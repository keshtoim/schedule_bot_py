"""Вечернее напоминание: python -m scripts.test_reminders"""

from __future__ import annotations

import asyncio
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

from schedule_bot.config import config  # noqa: E402
from schedule_bot.services.reminder_sender import _due  # noqa: E402
from schedule_bot.store.reminders import (  # noqa: E402
    effective_reminder,
    forget_reminder,
    get_reminder,
    set_reminder,
)

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


async def main() -> None:
    # --- store ------------------------------------------------------
    check("не спрашивали -> get_reminder None", get_reminder(5) is None)
    check("не спрашивали -> effective = дефолт", effective_reminder(5) == "20:00")

    await set_reminder(5, "18:00")
    check("своё время сохранено", get_reminder(5) == "18:00" and effective_reminder(5) == "18:00")

    await set_reminder(5, "off")
    check("можно выключить", effective_reminder(5) == "off")

    await forget_reminder(5)
    check("после forget снова дефолт", get_reminder(5) is None)
    check("REMINDER_DEFAULT из окружения подхватился", config.reminder_default == "20:00")

    # --- _due: кому пора слать ------------------------------------
    T = "2026-09-08"
    check("время пришло, сегодня не слали -> пора", _due("20:00", None, "20:00", T))
    check("время ещё не пришло -> не пора", not _due("20:00", None, "19:59", T))
    check("сегодня уже слали -> не пора", not _due("20:00", T, "21:00", T))
    check("вчера слали, новый день -> пора снова", _due("20:00", "2026-09-07", "20:01", T))
    check("напоминание выключено -> никогда", not _due("off", None, "23:00", T))
    check("догоняем, если бот проспал время", _due("20:00", None, "21:30", T))


try:
    asyncio.run(main())
finally:
    shutil.rmtree(_DATA, ignore_errors=True)

print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
