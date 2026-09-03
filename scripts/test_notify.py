"""Проверка выбора свежих аномалий: python -m scripts.test_notify"""

from __future__ import annotations

import dataclasses
import os
import sys

# config.py падает без этих переменных — задаём до импорта всего, что его тянет.
os.environ.setdefault("BOT_TOKEN", "test")
os.environ.setdefault("SCHEDULE_SOURCE", "scratch_samples/raspisanie.xlsx")
os.environ.setdefault("ZAMENY_SOURCE", "scratch_samples/zameny.xlsx")

from schedule_bot.parser.zameny_parser import ZamenyBlock, ZamenyRow  # noqa: E402
from schedule_bot.services.group_reconcile import ZamenyAnomaly  # noqa: E402
from schedule_bot.services.zameny_notifier import (  # noqa: E402
    diff_group_digest,
    next_run,
    select_fresh_anomalies,
)
from schedule_bot.services.zameny_view import (  # noqa: E402
    build_zameny_digest_rich_html,
    format_zameny_digest_plain,
)

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

# --- дайджест по группам --------------------------------------------
def block(date: str, rows: list[tuple[str, str, str, str]]) -> ZamenyBlock:
    return ZamenyBlock(
        "Пятница", date, [ZamenyRow(g, f"{p}пара", p, was, repl, "") for g, p, was, repl in rows]
    )


G = "23-ИСП-1"
dates1 = {"04.09.2026"}
cur1 = [block("04.09.2026", [(G, "1", "МДК.02.01", "нет")])]

d1 = diff_group_digest(None, cur1, dates1)
check("новая группа с заменами -> new", d1.digest is not None and d1.digest.kind == "new")

d2 = diff_group_digest(d1.next, cur1, dates1)
check("сигнатура не изменилась -> нет дайджеста", d2.digest is None)

cur2 = [block("04.09.2026", [(G, "1", "МДК.02.01", "нет"), (G, "2", "МДК.02.01", "нет")])]
d3 = diff_group_digest(d1.next, cur2, dates1)
check("добавлена пара -> updated", d3.digest is not None and d3.digest.kind == "updated" and len(d3.digest.blocks[0].rows) == 2)

d4 = diff_group_digest(d3.next, [], dates1)
check("сняли, пока дата публикуется -> cleared", d4.digest is not None and d4.digest.kind == "cleared")
check("cleared перечисляет снятую дату", d4.digest is not None and d4.digest.cancelled_dates == ["04.09.2026"])

d5 = diff_group_digest(d3.next, [], set())
check("дата ушла из окна -> нет дайджеста", d5.digest is None and d5.next.sig == "")

rich = build_zameny_digest_rich_html(dataclasses.replace(d3.digest, group=G))
plain = format_zameny_digest_plain(dataclasses.replace(d3.digest, group=G))
check("rich-дайджест рисует таблицу", "<table" in rich and G in rich)
check("plain-дайджест рисуется", "Пятница, 04.09.2026" in plain and "Пара 1" in plain)

# --- расписание проверок замен: 12:25, затем каждые 3 ч до полуночи ---
from datetime import datetime, time as _t  # noqa: E402

START = _t(12, 25)
check("утром -> сегодня 12:25", next_run(datetime(2026, 9, 3, 8, 0), START, 3) == datetime(2026, 9, 3, 12, 25))
check("в 13:00 -> сегодня 15:25", next_run(datetime(2026, 9, 3, 13, 0), START, 3) == datetime(2026, 9, 3, 15, 25))
check("в 21:30 -> завтра 12:25", next_run(datetime(2026, 9, 3, 21, 30), START, 3) == datetime(2026, 9, 4, 12, 25))
check("ночью (02:00) -> сегодня 12:25", next_run(datetime(2026, 9, 3, 2, 0), START, 3) == datetime(2026, 9, 3, 12, 25))
check("ровно в 12:25 -> следующий слот 15:25", next_run(datetime(2026, 9, 3, 12, 25), START, 3) == datetime(2026, 9, 3, 15, 25))
check("последний слот дня — 21:25, не позже", next_run(datetime(2026, 9, 3, 20, 0), START, 3) == datetime(2026, 9, 3, 21, 25))

print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
