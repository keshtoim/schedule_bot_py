"""Напоминания о парах: утром — расписание на сегодня, вечером — на завтра.

Время у каждого своё (онбординг / Настройки → 🔔 Уведомления). Вечернее по
умолчанию REMINDER_DEFAULT, утреннее — MORNING_REMINDER_DEFAULT (по умолчанию
выключено). Проверяем раз в ~40 с; правило простое: напоминание включено,
текущее время по Москве уже >= заданного и сегодня по этому виду ещё не
слали — шлём и помечаем. За полночь метка перестаёт совпадать с датой и
правило само сбрасывается.
"""

from __future__ import annotations

import asyncio
import json
import logging

from aiogram import Bot

from ..config import config
from ..store.reminders import KINDS, effective_reminder
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
    """{"<chat_id>:<kind>": "YYYY-MM-DD"}. Старый формат без вида — вечернее."""
    try:
        raw = json.loads(_sent_path().read_text("utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        (k if ":" in k else f"{k}:evening"): v
        for k, v in raw.items()
        if isinstance(v, str)
    }


def _save_sent(data: dict[str, str]) -> None:
    write_text_atomic(_sent_path(), json.dumps(data, ensure_ascii=False))


async def _send_reminder(bot: Bot, chat_id: int, group: str, kind: str) -> None:
    if kind == "morning":
        d, title = today(), "🔔 <b>Пары на сегодня</b>"
    else:
        d, title = add_days(today(), 1), "🔔 <b>Пары на завтра</b>"

    if not await day_has_lessons(group, d):
        log.info("Напоминание chat=%s (%s): пар нет, пропускаю", chat_id, kind)
        return
    try:
        await send_rich_message_html(chat_id, title + "\n" + await build_day_html(group, d))
    except Exception:
        await bot.send_message(chat_id, title + "\n\n" + await format_day(group, d))
    log.info("Напоминание отправлено chat=%s (%s)", chat_id, kind)


def _due(target: str, last_sent: str | None, now_hhmm: str, today_iso: str) -> bool:
    """Пора ли слать: напоминание включено, сегодня ещё не слали, время
    напоминания уже наступило. За полночь last_sent перестаёт совпадать с
    today_iso — правило само сбрасывается."""
    return target != "off" and last_sent != today_iso and now_hhmm >= target


async def _tick(bot: Bot, sent: dict[str, str]) -> bool:
    """Один проход по пользователям и видам напоминаний. True — если что-то поменяли."""
    hhmm = now().strftime("%H:%M")
    day = today().isoformat()
    changed = False

    for chat_id, group in await get_all_chats():
        for kind in KINDS:
            key = f"{chat_id}:{kind}"
            if not _due(effective_reminder(chat_id, kind), sent.get(key), hhmm, day):
                continue
            try:
                await _send_reminder(bot, chat_id, group, kind)
            except Exception:
                # чаще всего это временный сбой сайта колледжа — не помечаем
                # «отправлено», попробуем на следующем проходе (через ~40 с)
                log.exception("Напоминание chat=%s (%s): не отправилось, повторю позже", chat_id, kind)
                continue
            sent[key] = day
            changed = True
            await asyncio.sleep(0.05)  # бережём лимиты Telegram

    return changed


def start_reminder_sender(bot: Bot) -> None:
    global _task

    async def _loop() -> None:
        log.info(
            "Напоминалка запущена (утро %s, вечер %s; проверка раз в %d с)",
            config.morning_reminder_default, config.reminder_default, _CHECK_EVERY_S,
        )
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
