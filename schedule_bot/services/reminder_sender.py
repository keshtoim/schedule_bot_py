"""Вечернее напоминание: раз в день присылает пользователю пары на завтра.

Время у каждого своё (онбординг / Настройки → Напоминание), по умолчанию
REMINDER_DEFAULT. Проверяем раз в ~40 с; правило простое: если текущее
время по Москве уже >= времени напоминания и сегодня ещё не слали —
шлём и помечаем дату. На следующий день метка сбрасывается сама.
"""

from __future__ import annotations

import asyncio
import json
import logging

from aiogram import Bot

from ..config import config
from ..store.reminders import effective_reminder
from ..store.user_store import get_all_chats
from ..utils.atomic import write_text_atomic
from ..utils.clock import now, today
from ..utils.weekday import add_days
from .day_view import day_has_lessons, format_day
from .rich_message import send_rich_message_html
from .schedule_rich_view import build_day_html

log = logging.getLogger(__name__)

_CHECK_EVERY_S = 40
_task: asyncio.Task | None = None


def _sent_path():
    return config.data_path / "reminder-sent.json"


def _load_sent() -> dict[str, str]:
    try:
        return json.loads(_sent_path().read_text("utf-8"))
    except (OSError, ValueError):
        return {}


def _save_sent(data: dict[str, str]) -> None:
    write_text_atomic(_sent_path(), json.dumps(data, ensure_ascii=False))


async def _send_tomorrow(bot: Bot, chat_id: int, group: str) -> None:
    d = add_days(today(), 1)
    if not await day_has_lessons(group, d):
        log.info("Напоминание chat=%s: на завтра пар нет, пропускаю", chat_id)
        return
    try:
        await send_rich_message_html(chat_id, "🔔 <b>Пары на завтра</b>\n" + await build_day_html(group, d))
    except Exception:
        await bot.send_message(chat_id, "🔔 <b>Пары на завтра</b>\n\n" + await format_day(group, d))
    log.info("Напоминание отправлено chat=%s", chat_id)


def _due(target: str, last_sent: str | None, now_hhmm: str, today_iso: str) -> bool:
    """Пора ли слать: напоминание включено, сегодня ещё не слали, время
    напоминания уже наступило. За полночь last_sent перестаёт совпадать с
    today_iso — правило само сбрасывается."""
    return target != "off" and last_sent != today_iso and now_hhmm >= target


async def _tick(bot: Bot, sent: dict[str, str]) -> bool:
    """Один проход по пользователям. Возвращает True, если что-то поменяли."""
    hhmm = now().strftime("%H:%M")
    day = today().isoformat()
    changed = False

    for chat_id, group in await get_all_chats():
        key = str(chat_id)
        if not _due(effective_reminder(chat_id), sent.get(key), hhmm, day):
            continue
        try:
            await _send_tomorrow(bot, chat_id, group)
        except Exception:
            # чаще всего это временный сбой сайта колледжа — не помечаем
            # «отправлено», попробуем на следующем проходе (через ~40 с)
            log.exception("Напоминание chat=%s: не отправилось, повторю позже", chat_id)
            continue
        sent[key] = day
        changed = True
        await asyncio.sleep(0.05)  # бережём лимиты Telegram

    return changed


def start_reminder_sender(bot: Bot) -> None:
    global _task

    async def _loop() -> None:
        log.info("Напоминалка запущена (дефолт %s, проверка раз в %d с)", config.reminder_default, _CHECK_EVERY_S)
        sent = _load_sent()
        while True:
            try:
                if await _tick(bot, sent):
                    # чистим прошлые дни, чтобы файл не пух
                    day = today().isoformat()
                    sent = {k: v for k, v in sent.items() if v == day}
                    _save_sent(sent)
            except Exception:
                log.exception("Напоминалка: сбой прохода")
            await asyncio.sleep(_CHECK_EVERY_S)

    _task = asyncio.create_task(_loop())


def stop_reminder_sender() -> None:
    if _task is not None and not _task.done():
        _task.cancel()
