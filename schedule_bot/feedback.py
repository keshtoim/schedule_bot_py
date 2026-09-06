"""Багрепорты от пользователей: владельцу в личку + в лог + в файл.

Владелец пользуется этим же ботом, так что отдельный бот не нужен — просто
шлём сообщение на его chat_id (OWNER_CHAT_ID). Свой chat_id владелец узнаёт
командой /id.
"""

from __future__ import annotations

import json
import logging
import time

from aiogram import Bot
from aiogram.types import User

from .config import config
from .utils.atomic import write_text_atomic
from .utils.clock import today
from .utils.html import escape_html
from .utils.weekday import is_numerator_week

log = logging.getLogger(__name__)

_MAX_LEN = 2000


def _log_file():
    return config.data_path / "bug-reports.jsonl"


def _append_to_file(record: dict) -> None:
    path = _log_file()
    prev = path.read_text("utf-8") if path.is_file() else ""
    write_text_atomic(path, prev + json.dumps(record, ensure_ascii=False) + "\n")


async def report_bug(bot: Bot, user: User, group: str | None, text: str) -> None:
    """Доставить багрепорт: в файл data/bug-reports.jsonl, в лог и, если задан
    OWNER_CHAT_ID, — сообщением владельцу."""
    text = text.strip()[:_MAX_LEN]
    who = f"@{user.username}" if user.username else user.full_name

    d = today()
    parity = "числитель" if is_numerator_week(d) else "знаменатель"

    _append_to_file(
        {
            "ts": int(time.time()),
            "user_id": user.id,
            "username": user.username,
            "group": group,
            "text": text,
        }
    )

    msg = (
        "🐞 <b>Багрепорт</b>\n"
        f"От: {escape_html(who)} · id <code>{user.id}</code>\n"
        f"Группа: <b>{escape_html(group or '—')}</b>\n"
        f"Контекст: {d:%d.%m.%Y}, {parity}\n\n"
        f"{escape_html(text)}"
    )

    if config.owner_chat_id:
        try:
            await bot.send_message(config.owner_chat_id, msg)
            log.info("Багрепорт от %s отправлен владельцу", who)
            return
        except Exception:
            log.exception("Не смог отправить багрепорт владельцу (chat %s)", config.owner_chat_id)

    log.warning(
        "Багрепорт от %s (OWNER_CHAT_ID не задан или сообщение не дошло) — см. %s:\n%s",
        who, _log_file(), text,
    )
