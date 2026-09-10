"""Утренние и вечерние напоминания: python -m scripts.test_reminders"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

_DATA = Path(tempfile.mkdtemp(prefix="rem-test-"))
os.environ["DATA_DIR"] = str(_DATA)
os.environ.setdefault("BOT_TOKEN", "test")
os.environ.setdefault("SCHEDULE_SOURCE", "x")
os.environ.setdefault("ZAMENY_SOURCE", "y")
os.environ["REMINDER_DEFAULT"] = "20:00"
os.environ["MORNING_REMINDER_DEFAULT"] = "off"

# файл в старом формате {chat_id: "HH:MM"} — должен прочитаться как вечернее
(_DATA / "reminders.json").write_text(json.dumps({"99": "21:00"}), encoding="utf-8")

from schedule_bot.config import config  # noqa: E402
from schedule_bot.services.reminder_sender import _due, _load_sent  # noqa: E402
from schedule_bot.store.reminders import (  # noqa: E402
    _coerce,
    effective_reminder,
    forget_reminder,
    get_reminders,
    set_reminder,
    was_asked,
)

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


async def _raises_value_error(coro) -> bool:
    try:
        await coro
        return False
    except ValueError:
        return True


async def main() -> None:
    # --- дефолты ---------------------------------------------------
    check("дефолт вечернего из env", config.reminder_default == "20:00")
    check("дефолт утреннего — off", config.morning_reminder_default == "off")

    # --- хранилище ----------------------------------------------
    check("не спрашивали → get_reminders None", get_reminders(5) is None)
    check("не спрашивали → was_asked False", not was_asked(5))
    check("не спрашивали → вечернее = дефолт", effective_reminder(5, "evening") == "20:00")
    check("не спрашивали → утреннее = off", effective_reminder(5, "morning") == "off")

    await set_reminder(5, "morning", "07:30")
    check("утреннее сохранено, вечернее ещё дефолт",
          effective_reminder(5, "morning") == "07:30" and effective_reminder(5, "evening") == "20:00")
    check("was_asked True после первой записи", was_asked(5))

    await set_reminder(5, "evening", "off")
    check("вечернее выключили — утреннее не затронуто",
          effective_reminder(5, "evening") == "off" and effective_reminder(5, "morning") == "07:30")

    await forget_reminder(5)
    check("после forget обе снова дефолтные",
          get_reminders(5) is None and effective_reminder(5, "morning") == "off")
    check("неизвестный kind → ValueError", await _raises_value_error(set_reminder(5, "noon", "12:00")))

    # --- миграция старого формата -------------------------------
    check("старый {chat: 'HH:MM'} читается как вечернее", effective_reminder(99, "evening") == "21:00")
    check("у мигрированного утреннее = дефолт", effective_reminder(99, "morning") == "off")
    check("_coerce: строка → evening", _coerce("19:00") == {"evening": "19:00"})
    check("_coerce: чужие ключи отсекаются", _coerce({"morning": "07:00", "x": 1}) == {"morning": "07:00"})

    # --- _due: кому пора слать ----------------------------------
    T = "2026-09-08"
    check("время пришло, сегодня не слали → пора", _due("20:00", None, "20:00", T))
    check("время ещё не пришло → не пора", not _due("20:00", None, "19:59", T))
    check("сегодня уже слали → не пора", not _due("20:00", T, "21:00", T))
    check("вчера слали, новый день → пора снова", _due("20:00", "2026-09-07", "20:01", T))
    check("выключено → никогда", not _due("off", None, "23:00", T))
    check("догоняем, если бот проспал время", _due("07:30", None, "09:15", T))

    # --- _load_sent: миграция ключей ---------------------------
    (_DATA / "reminder-sent.json").write_text(
        json.dumps({"42": T, "43:morning": T}), encoding="utf-8"
    )
    loaded = _load_sent()
    check("_load_sent: ключ без вида → :evening", loaded.get("42:evening") == T)
    check("_load_sent: ключ с видом сохраняется", loaded.get("43:morning") == T)


try:
    asyncio.run(main())
finally:
    shutil.rmtree(_DATA, ignore_errors=True)

print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
