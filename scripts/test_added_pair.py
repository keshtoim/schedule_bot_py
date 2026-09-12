"""Замена может добавить пару туда, где у группы по расписанию пусто —
в выводе дня она должна появиться: python -m scripts.test_added_pair"""

from __future__ import annotations

import sys

from schedule_bot.parser.schedule_parser import Schedule, ScheduleDay, SchedulePair
from schedule_bot.parser.zameny_parser import ZamenyBlock, ZamenyRow
from schedule_bot.services.day_view import day_lesson_lines
from schedule_bot.services.schedule_rich_view import _day_table_html

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


def row(group: str, pair_number: str, instead_of: str, replacement: str, room: str = "") -> ZamenyRow:
    return ZamenyRow(group, f"{pair_number}пара", pair_number, instead_of, replacement, room)


# Реальный кейс: 23-ИСП-1, пятница. Пары 1-2 отменены, пара 3 идёт по
# расписанию, пара 4 (в сетке есть, но у группы пусто) добавлена заменой.
day = ScheduleDay(
    weekday="Пятница",
    pairs=[
        SchedulePair("1", "9.00", "10.35", {"23-ИСП-1": "МДК.02.01 Сизый 204"}),
        SchedulePair("2", "10.50", "12.25", {"23-ИСП-1": "МДК.02.01 Сизый 204"}),
        SchedulePair("3", "12.45", "14.20", {"23-ИСП-1": "компьютерные сети Симонян 210"}),
        SchedulePair("4", "14.30", "16.05", {"23-ИСП-1": ""}),
    ],
)
block = ZamenyBlock(
    "Пятница",
    "04.09.2026",
    [
        row("23-ИСП-1", "1", "МДК.02.01 Сизый", "нет"),
        row("23-ИСП-1", "2", "МДК.02.01 Сизый", "нет"),
        row("23-ИСП-1", "4", "", "комп.сети (Симонян)", "210"),
    ],
)

lines = day_lesson_lines(day, "23-ИСП-1", True, block)
print("\n".join(lines))
check("plain: 4 строки (пары 1-4)", len(lines) == 4)
check("plain: пары 1-2 отменены", lines[0].count("Отменено") and lines[1].count("Отменено"))
check("plain: пара 3 по расписанию", "компьютерные сети" in lines[2] and "➕" not in lines[2])
check("plain: пара 4 добавлена", lines[3].startswith("<b>Пара 4 (14.30–16.05):</b> ➕") and "комп.сети" in lines[3] and "210" in lines[3])

table = _day_table_html(day, "23-ИСП-1", True, block)
print("\n" + table)
check("rich: пара 4 в таблице, аудитория с префиксом «ауд.»", "<td>4</td><td>14.30–16.05</td><td>➕ комп.сети (Симонян)</td><td>ауд. 210</td>" in table)
check("rich: строк ровно 4", table.count("<tr>") == 5)  # 1 заголовок + 4 пары

# Пара, которой нет в сетке вообще (grid_pair отсутствует) — тоже показываем,
# только без времени.
block_no_grid = ZamenyBlock("Пятница", "04.09.2026", [row("23-ИСП-1", "7", "", "классный час", "301")])
extra = day_lesson_lines(day, "23-ИСП-1", True, block_no_grid)
check("plain: пара вне сетки показана без времени", extra[-1] == "<b>Пара 7:</b> ➕ <i>классный час 301</i>")

# Отмена несуществующей пары — показывать нечего.
block_cancel = ZamenyBlock("Пятница", "04.09.2026", [row("23-ИСП-1", "4", "", "нет")])
only_sched = day_lesson_lines(day, "23-ИСП-1", True, block_cancel)
check("plain: отмену пустой пары не показываем", all("Пара 4" not in line for line in only_sched))

print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
