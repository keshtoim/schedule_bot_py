"""Проверка обнаружения опечаток в названиях групп: python -m scripts.test_reconcile"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict

from schedule_bot.parser.schedule_parser import Schedule, ScheduleDay, SchedulePair
from schedule_bot.parser.zameny_parser import ZamenyBlock, ZamenyRow
from schedule_bot.services.group_reconcile import (
    edit_distance,
    find_zameny_anomalies,
    lessons_look_same,
    normalize_group,
)

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


def row(group: str, pair_number: str, instead_of: str, replacement: str, room: str = "") -> ZamenyRow:
    return ZamenyRow(group, f"{pair_number}пара", pair_number, instead_of, replacement, room)


# --- юнит-проверки -----------------------------------------------------
check("normalize_group: латинская C", normalize_group("23-ИCП-1") == normalize_group("23-ИСП-1"))
check("normalize_group: en-dash + пробелы", normalize_group("23 – ИСП - 1") == normalize_group("23-ИСП-1"))
check("edit_distance последняя цифра", edit_distance(normalize_group("23-исп-2"), normalize_group("23-исп-1")) == 1)
check(
    "lessons_look_same: сокращение",
    lessons_look_same("тех.оборуд. (Кипенская)", "Технологическое оборудование Кипенская ауд.5"),
)
check("lessons_look_same: не связаны", not lessons_look_same("Математика Иванов", "Физкультура Петров"))

# --- фикстура: реальный кейс -----------------------------------------
schedule = Schedule(
    groups=["23-ИСП-1", "23-ИСП-2", "24-ИСП-1"],
    days=[
        ScheduleDay(
            weekday="Пятница",
            pairs=[
                SchedulePair(
                    "1", "8.00", "9.35",
                    {"23-ИСП-1": "Иностранный язык Смирнова", "23-ИСП-2": "Иностранный язык Смирнова", "24-ИСП-1": ""},
                ),
                SchedulePair(
                    "2", "9.45", "11.20",
                    {
                        "23-ИСП-1": "Технологическое оборудование Кипенская ауд.5",
                        "23-ИСП-2": "Базы данных Орлов ауд.12",
                        "24-ИСП-1": "",
                    },
                ),
            ],
        )
    ],
)

zameny = [ZamenyBlock("Пятница", "05.09.2025", [row("23-ИСП-2", "2", "тех.оборуд. (Кипенская)", "Физика Ландау", "ауд.3")])]

anomalies = find_zameny_anomalies(schedule, zameny)
print("\nanomalies:", json.dumps([asdict(a) for a in anomalies], ensure_ascii=False, indent=2))
check("одна аномалия", len(anomalies) == 1)
check("kind == typo", anomalies and anomalies[0].kind == "typo")
check("stated 23-ИСП-2", anomalies and anomalies[0].stated_group == "23-ИСП-2")
check("likely 23-ИСП-1", anomalies and anomalies[0].likely_group == "23-ИСП-1")

# --- нет ложного срабатывания, когда расписание указанной группы совпадает
zameny_ok = [ZamenyBlock("Пятница", "05.09.2025", [row("23-ИСП-2", "2", "Базы данных (Орлов)", "Физика")])]
check("нет аномалии, если группа совпадает", len(find_zameny_anomalies(schedule, zameny_ok)) == 0)

# --- гомоглиф принимается без сверки с расписанием --------------------
zameny_homo = [ZamenyBlock("Пятница", "05.09.2025", [row("23-ИCП-1", "1", "что-то", "иначе")])]
ha = find_zameny_anomalies(schedule, zameny_homo)
check("гомоглиф найден", len(ha) == 1 and ha[0].kind == "homoglyph" and ha[0].likely_group == "23-ИСП-1")

print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
