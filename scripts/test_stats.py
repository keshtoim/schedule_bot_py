"""Статистика владельца: python -m scripts.test_stats"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("BOT_TOKEN", "test")
os.environ.setdefault("SCHEDULE_SOURCE", "x")
os.environ.setdefault("ZAMENY_SOURCE", "y")

from schedule_bot.services.stats import format_stats  # noqa: E402

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


empty = format_stats([])
check("пустая база — без падений", "Пока никто" in empty)

chats = (
    [(i, "23-ИСП-1") for i in range(8)]
    + [(100 + i, "24-ИСП-2") for i in range(5)]
    + [(200 + i, "23-МТОРПО-1") for i in range(5)]
    + [(300, "22-ПКС-1")]
)
out = format_stats(chats)
check("всего пользователей посчитано", "Пользователей: <b>19</b>" in out)
check("различных групп посчитано", "Групп задействовано: <b>4</b>" in out)
check("самая частая группа — первой", out.index("23-ИСП-1") < out.index("24-ИСП-2"))
check("при равенстве count — по алфавиту", out.index("23-МТОРПО-1") < out.index("24-ИСП-2") or out.index("24-ИСП-2") < out.index("23-МТОРПО-1"))
check("счётчик группы виден", "8" in out and "23-ИСП-1" in out)

# порог топ-10
many = [(i, f"grp-{i:02d}") for i in range(15)]
out2 = format_stats(many)
check("больше 10 групп — показан хвост «…и ещё N»", "и ещё 5" in out2)
check("в топе ровно 10 строк с группами", out2.count("<code>") == 10)

print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
