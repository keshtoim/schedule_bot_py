"""Во сколько присылать пользователю расписание — утром (на сегодня) и/или
вечером (на завтра).

data/reminders.json: {chat_id: {"morning": "HH:MM"|"off", "evening": ...}}.
Старый формат {chat_id: "HH:MM"|"off"} читается как одно вечернее значение.
Отсутствие записи целиком = пользователя ещё не спрашивали (действуют дефолты).
"""

from __future__ import annotations

import json

from ..config import config
from ..utils.atomic import write_text_atomic

KINDS = ("morning", "evening")

_file_path = config.data_path / "reminders.json"
_cache: dict[str, dict[str, str]] | None = None


def _coerce(value: object) -> dict[str, str]:
    """Старое значение-строка → {"evening": <оно>}; новый dict — как есть."""
    if isinstance(value, str):
        return {"evening": value}
    if isinstance(value, dict):
        return {k: v for k, v in value.items() if k in KINDS and isinstance(v, str)}
    return {}


def _load() -> dict[str, dict[str, str]]:
    global _cache
    if _cache is None:
        try:
            raw = json.loads(_file_path.read_text("utf-8"))
        except (OSError, ValueError):
            raw = {}
        _cache = {str(k): _coerce(v) for k, v in raw.items()} if isinstance(raw, dict) else {}
    return _cache


def _default(kind: str) -> str:
    return config.reminder_default if kind == "evening" else config.morning_reminder_default


def get_reminders(chat_id: int) -> dict[str, str] | None:
    """Сырая запись пользователя или None (не спрашивали)."""
    return _load().get(str(chat_id))


def was_asked(chat_id: int) -> bool:
    """Проходил ли пользователь онбординг-вопрос про напоминания."""
    return str(chat_id) in _load()


def effective_reminder(chat_id: int, kind: str) -> str:
    """Что реально применяется для утра/вечера: своё значение либо дефолт."""
    rec = _load().get(str(chat_id))
    if rec is None:
        return _default(kind)
    return rec.get(kind, _default(kind))


def _persist() -> None:
    write_text_atomic(_file_path, json.dumps(_load(), ensure_ascii=False, indent=2))


async def set_reminder(chat_id: int, kind: str, value: str) -> None:
    if kind not in KINDS:
        raise ValueError(f"kind должен быть из {KINDS}, а не {kind!r}")
    _load().setdefault(str(chat_id), {})[kind] = value
    _persist()


async def forget_reminder(chat_id: int) -> None:
    if _load().pop(str(chat_id), None) is not None:
        _persist()
