"""Замена в rich-таблице: фамилия преподавателя должна попадать в колонку
«Преподаватель / Аудитория», а не оставаться приклеенной к предмету —
баг, найденный пользователями (скрин: «БЖ Токарев» / «303» вместо
«БЖ» / «Токарев, ауд. 303»). python -m scripts.test_zameny_rich_columns
"""

from __future__ import annotations

import sys

from schedule_bot.parser.schedule_parser import ScheduleDay, SchedulePair
from schedule_bot.parser.zameny_parser import ZamenyBlock, ZamenyRow
from schedule_bot.services.schedule_rich_view import (
    _day_table_html,
    _format_location,
    _split_zameny_replacement,
)

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


def row(group: str, pair_number: str, instead_of: str, replacement: str, room: str = "") -> ZamenyRow:
    return ZamenyRow(group, f"{pair_number}пара", pair_number, instead_of, replacement, room)


# --- _split_zameny_replacement: голая пара функций ---------------------
check(
    "«БЖ Токарев» + комната → предмет БЖ, препод Токарев с аудиторией",
    _split_zameny_replacement("БЖ Токарев", "303") == ("БЖ", "Токарев, ауд. 303"),
)
check(
    "«МДК.02.01 Сизый» + комната",
    _split_zameny_replacement("МДК.02.01 Сизый", "204") == ("МДК.02.01", "Сизый, ауд. 204"),
)
check(
    "нечисловая пометка вместо кабинета («лекции») — без «ауд.»",
    _split_zameny_replacement("ПОПД Захарова", "лекции") == ("ПОПД", "Захарова, лекции"),
)
check(
    "без комнаты — просто преподаватель",
    _split_zameny_replacement("экономика Новикова", "") == ("экономика", "Новикова"),
)
check(
    "не разобрать (фамилия в скобках) — текст как есть, комната всё равно на месте",
    _split_zameny_replacement("комп.сети (Симонян)", "210") == ("комп.сети (Симонян)", "ауд. 210"),
)
check("совсем без данных → прочерк", _split_zameny_replacement("", "") == ("", "—"))
check("_format_location: номер → с «ауд.»", _format_location("303") == "ауд. 303")
check("_format_location: слово → как есть", _format_location("лекции") == "лекции")
check("_format_location: пусто → пусто", _format_location("") == "")

# --- сквозной сценарий: ровно как на скрине пользователей ---------------
day = ScheduleDay(
    weekday="Суббота",
    pairs=[
        SchedulePair("2", "10.50", "12.25", {"23-ИСП-1": "обществознание Курашова 303"}),
        SchedulePair("3", "12.45", "14.20", {"23-ИСП-1": "МДК.02.01 Сизый 204"}),
    ],
)
block = ZamenyBlock(
    "Суббота",
    "12.09.2026",
    [
        row("23-ИСП-1", "2", "обществознание (Курашова)", "БЖ Токарев", "303"),
        row("23-ИСП-1", "3", "", "МДК.02.01 Сизый", "204"),
    ],
)

table = _day_table_html(day, "23-ИСП-1", False, block)
print("\n" + table)

check(
    "пара 2: предмет «🔁 БЖ» отдельно от преподавателя «Токарев, ауд. 303»",
    "<td>2</td><td>10.50–12.25</td><td>🔁 БЖ</td><td>Токарев, ауд. 303</td>" in table,
)
check(
    "пара 3: предмет «🔁 МДК.02.01» отдельно от «Сизый, ауд. 204»",
    "<td>3</td><td>12.45–14.20</td><td>🔁 МДК.02.01</td><td>Сизый, ауд. 204</td>" in table,
)
check("фамилия преподавателя не осталась в колонке предмета", "БЖ Токарев" not in table and "МДК.02.01 Сизый" not in table)

print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
