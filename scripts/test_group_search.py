"""Текстовый поиск группы: python -m scripts.test_group_search"""

from __future__ import annotations

import sys

from schedule_bot.handlers.group_search import match_groups

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


GROUPS = [
    "23-ИСП-1",
    "23-ИСП-2",
    "24-ИСП-1",
    "25-ИСП-1",
    "23-МТОРПО-1",
    "22-ПКС-1",
]

check("«исп1» → все ИСП-1 по курсам, отсортировано",
      match_groups("исп1", GROUPS) == ["23-ИСП-1", "24-ИСП-1", "25-ИСП-1"])
check("регистр не важен",
      match_groups("ИсП1", GROUPS) == ["23-ИСП-1", "24-ИСП-1", "25-ИСП-1"])
check("«23» → весь курс",
      match_groups("23", GROUPS) == ["23-ИСП-1", "23-ИСП-2", "23-МТОРПО-1"])
check("точное имя с дефисами",
      match_groups("23-исп-1", GROUPS) == ["23-ИСП-1"])
check("имя с пробелами вместо дефисов",
      match_groups("23 исп 1", GROUPS) == ["23-ИСП-1"])
check("часть слова посередине",
      match_groups("мторпо", GROUPS) == ["23-МТОРПО-1"])
check("латинская раскладка: bcg = исп",
      match_groups("bcg", GROUPS) == ["23-ИСП-1", "23-ИСП-2", "24-ИСП-1", "25-ИСП-1"])
check("латинский двойник буквы: 23-иcп-1 (лат. c)",
      match_groups("23-иcп-1", GROUPS) == ["23-ИСП-1"])
check("нет совпадений → пусто",
      match_groups("экономика", GROUPS) == [])
check("слишком короткий запрос → пусто",
      match_groups("и", GROUPS) == [])
check("один символ-цифра → пусто",
      match_groups("2", GROUPS) == [])
check("лимит результатов соблюдается",
      len(match_groups("исп1", [f"2{n:02d}-ИСП-1" for n in range(40)], limit=5)) == 5)

print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
