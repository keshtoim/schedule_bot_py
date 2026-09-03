"""Проверка выбора свежих аномалий: python -m scripts.test_notify"""

from __future__ import annotations

import os
import sys

# config.py падает без этих переменных — задаём до импорта всего, что его тянет.
os.environ.setdefault("BOT_TOKEN", "test")
os.environ.setdefault("SCHEDULE_SOURCE", "scratch_samples/raspisanie.xlsx")
os.environ.setdefault("ZAMENY_SOURCE", "scratch_samples/zameny.xlsx")

from schedule_bot.parser.zameny_parser import ZamenyRow  # noqa: E402
from schedule_bot.services.group_reconcile import ZamenyAnomaly  # noqa: E402
from schedule_bot.services.zameny_notifier import select_fresh_anomalies  # noqa: E402

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


def mk(stated: str, likely: str, replacement: str) -> ZamenyAnomaly:
    return ZamenyAnomaly(
        kind="typo",
        stated_group=stated,
        likely_group=likely,
        date="05.09.2025",
        weekday="Пятница",
        rows=[ZamenyRow(stated, "2пара", "2", "тех.оборуд.", replacement, "")],
        evidence=[],
    )


a1 = mk("23-ИСП-2", "23-ИСП-1", "Физика")

r1 = select_fresh_anomalies([a1], None)
check("первый запуск только сеет", r1.seed_only and not r1.fresh and len(r1.next_notified) == 1)

r2 = select_fresh_anomalies([a1], r1.next_notified)
check("известная аномалия не повторяется", not r2.seed_only and not r2.fresh)

a1b = mk("23-ИСП-2", "23-ИСП-1", "Химия")
r3 = select_fresh_anomalies([a1b], r1.next_notified)
check("переформулированная аномалия снова свежая", len(r3.fresh) == 1)

a2 = mk("24-ИСП-3", "24-ИСП-2", "История")
r4 = select_fresh_anomalies([a1, a2], r1.next_notified)
check("свежая только новая аномалия", len(r4.fresh) == 1 and r4.fresh[0].stated_group == "24-ИСП-3")
check("next_notified держит обе после свежей", len(r4.next_notified) == 2)

r5 = select_fresh_anomalies([], r4.next_notified)
check("исчезнувшие аномалии выкинуты", not r5.fresh and len(r5.next_notified) == 0)

print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
