from __future__ import annotations

import contextlib
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from . import maintenance
from .config import config
from .utils.describe_error import describe_error

log = logging.getLogger(__name__)


def _user_id(event: TelegramObject) -> int | None:
    user = getattr(event, "from_user", None)
    return user.id if user else None


class TokenBucket:
    """Классическое «вёдро с токенами»: пополняется равномерно во времени,
    каждое действие тратит один токен. Пустое ведро → действие отклонено."""

    __slots__ = ("tokens", "last")

    def __init__(self, capacity: float, now: float) -> None:
        self.tokens = capacity
        self.last = now

    def take(self, now: float, capacity: float, refill_per_sec: float) -> bool:
        self.tokens = min(capacity, self.tokens + (now - self.last) * refill_per_sec)
        self.last = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


_THROTTLE_CAPACITY = 5  # запас на «пролистать меню» без задержки
_THROTTLE_REFILL_PER_SEC = 1 / 3  # дальше ~1 действие в 3 с (устойчиво ~20/мин)
_THROTTLE_WARN_COOLDOWN_S = 15
_THROTTLE_GC_AT = 512


class ThrottleMiddleware(BaseMiddleware):
    """Мягкий анти-флуд. До пяти действий подряд проходят сразу, дальше темп
    ограничивается; лишние апдейты тихо отбрасываются, а раз в 15 с чат
    получает короткое «помедленнее». Владелец не ограничивается."""

    def __init__(self) -> None:
        self._buckets: dict[int, TokenBucket] = {}
        self._warned_at: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        uid = _user_id(event)
        if uid is None or uid == config.owner_chat_id:
            return await handler(event, data)

        now = time.monotonic()
        bucket = self._buckets.get(uid)
        if bucket is None:
            bucket = self._buckets[uid] = TokenBucket(_THROTTLE_CAPACITY, now)

        if bucket.take(now, _THROTTLE_CAPACITY, _THROTTLE_REFILL_PER_SEC):
            return await handler(event, data)

        if now - self._warned_at.get(uid, 0.0) > _THROTTLE_WARN_COOLDOWN_S:
            self._warned_at[uid] = now
            log.warning("Анти-флуд: чат %s превысил лимит, придерживаю", uid)
            with contextlib.suppress(Exception):
                if isinstance(event, Message):
                    await event.answer("Слишком часто — подожди пару секунд 🙂")
                elif isinstance(event, CallbackQuery):
                    await event.answer("Помедленнее 🙂")
        elif isinstance(event, CallbackQuery):
            with contextlib.suppress(Exception):
                await event.answer()  # просто снять «часики»

        self._gc(now)
        return None

    def _gc(self, now: float) -> None:
        if len(self._buckets) < _THROTTLE_GC_AT:
            return
        for uid in [u for u, b in self._buckets.items() if now - b.last > 300]:
            self._buckets.pop(uid, None)
            self._warned_at.pop(uid, None)


class MaintenanceMiddleware(BaseMiddleware):
    """Пока включён режим техработ — всем, кроме владельца, отвечаем «вернусь
    позже» и не пускаем дальше. Владелец работает как обычно (в т.ч. чтобы
    выключить режим)."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if maintenance.is_on() and _user_id(event) != config.owner_chat_id:
            if isinstance(event, Message):
                await event.answer(maintenance.NOTICE)
            elif isinstance(event, CallbackQuery):
                await event.answer(maintenance.NOTICE, show_alert=True)
            return None
        return await handler(event, data)


def _describe(event: TelegramObject) -> tuple[str, str]:
    if isinstance(event, Message):
        who = f"chat={event.chat.id}"
        if event.from_user and event.from_user.username:
            who += f" @{event.from_user.username}"
        text = (event.text or event.caption or "").replace("\n", " ").strip()
        return who, (f"текст {text!r}" if text else "сообщение без текста")
    if isinstance(event, CallbackQuery):
        chat = event.message.chat.id if event.message else "?"
        return f"chat={chat} @{event.from_user.username or event.from_user.id}", f"кнопка {event.data!r}"
    return "?", type(event).__name__


class LoggingMiddleware(BaseMiddleware):
    """Пишет в консоль каждое действие пользователя, время обработки и любую
    ошибку внутри хендлера — по логу видно, что нажали и на чём упало."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        who, what = _describe(event)
        log.info("▶ %s — %s", who, what)
        started = time.monotonic()
        try:
            result = await handler(event, data)
        except Exception as err:
            ms = (time.monotonic() - started) * 1000
            log.exception("✖ %s — %s — упало за %.0f мс: %s", who, what, ms, describe_error(err))
            raise
        log.info("✔ %s — обработано за %.0f мс", who, (time.monotonic() - started) * 1000)
        return result
