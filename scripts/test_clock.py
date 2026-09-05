"""Часовой пояс — всё по Москве: python -m scripts.test_clock"""

from __future__ import annotations

import os
import sys
from datetime import datetime, time
from zoneinfo import ZoneInfo

os.environ.setdefault("BOT_TOKEN", "test")
os.environ.setdefault("SCHEDULE_SOURCE", "x")
os.environ.setdefault("ZAMENY_SOURCE", "y")

from schedule_bot.services.zameny_notifier import next_run  # noqa: E402
from schedule_bot.utils.clock import MSK, now, today  # noqa: E402

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


# --- clock: всегда Москва ------------------------------------------------
check("clock.now() timezone-aware", now().tzinfo is not None)
check("clock.now() именно Europe/Moscow", now().utcoffset() == datetime.now(MSK).utcoffset())
check("clock.today() == дата по Москве", today() == datetime.now(MSK).date())
check("MSK — это Europe/Moscow", MSK == ZoneInfo("Europe/Moscow"))

# --- next_run с tz-aware временем не падает на вычитании -----------------
msk_now = datetime(2026, 9, 7, 13, 0, tzinfo=MSK)
nxt = next_run(msk_now, time(12, 25), 3)
check("next_run вернул tz-aware", nxt.tzinfo is not None)
check("next_run: в 13:00 -> сегодня 15:25", nxt == datetime(2026, 9, 7, 15, 25, tzinfo=MSK))
check("next_run: разница считается без ошибки", (nxt - msk_now).total_seconds() == 2 * 3600 + 25 * 60)
# naive время (как в тестах) тоже работает
naive = next_run(datetime(2026, 9, 7, 8, 0), time(12, 25), 3)
check("next_run: naive -> сегодня 12:25", naive == datetime(2026, 9, 7, 12, 25))

print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
