"""Во сколько присылать пользователю расписание на завтра.

Отдельный файл data/reminders.json ({chat_id: "HH:MM" | "off"}), чтобы не
трогать критичный users.json. Отсутствие записи = пользователя ещё не
спрашивали, действует REMINDER_DEFAULT.
"""

from __future__ import annotations

import json

from ..config import config
from ..utils.atomic import write_text_atomic

_file_path = config.data_path / "reminders.json"
_cache: dict[str, str] | None = None


def _load() -> dict[str, str]:
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(_file_path.read_text("utf-8"))
        except (OSError, ValueError):
            _cache = {}
    return _cache


def get_reminder(chat_id: int) -> str | None:
    """«HH:MM», «off» или None (не спрашивали — берётся дефолт)."""
    return _load().get(str(chat_id))


def effective_reminder(chat_id: int) -> str:
    """Что реально применяется: своё значение либо REMINDER_DEFAULT."""
    return get_reminder(chat_id) or config.reminder_default


async def set_reminder(chat_id: int, value: str) -> None:
    data = _load()
    data[str(chat_id)] = value
    write_text_atomic(_file_path, json.dumps(data, ensure_ascii=False, indent=2))


async def forget_reminder(chat_id: int) -> None:
    data = _load()
    if data.pop(str(chat_id), None) is not None:
        write_text_atomic(_file_path, json.dumps(data, ensure_ascii=False, indent=2))
