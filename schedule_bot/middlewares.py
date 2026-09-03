from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from .utils.describe_error import describe_error

log = logging.getLogger(__name__)


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
