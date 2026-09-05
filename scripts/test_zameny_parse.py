"""Проверка парсера замен на новом формате файла: python -m scripts.test_zameny_parse"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from schedule_bot.parser.schedule_parser import parse_schedule
from schedule_bot.parser.workbook import load_active_sheet
from schedule_bot.parser.zameny_parser import parse_zameny
from schedule_bot.services.group_reconcile import find_zameny_anomalies

SAMPLES = Path(__file__).resolve().parent.parent / "scratch_samples"

if not list(SAMPLES.glob("*.xlsx")):
    print("SKIP: нет scratch_samples/*.xlsx (реальные файлы не в git)")
    raise SystemExit(0)

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


def main() -> None:
    # --- формат 2026-09: суффикс чётности в заголовке, имя группы только в
    #     первой строке многострочного блока -------------------------------
    sched = parse_schedule(load_active_sheet(SAMPLES / "raspisanie_2026-09.xlsx"))
    zam = parse_zameny(load_active_sheet(SAMPLES / "zameny_2026-09.xlsx"))

    check("заголовок с суффиксом '(числитель)' парсится", len(zam) >= 1)
    fri = zam[0]
    check("день недели нормализован", fri.weekday == "Пятница")
    check("дата блока извлечена", fri.date == "04.09.2026")

    isp = [r for r in fri.rows if r.group == "23-ИСП-1"]
    check("строки-продолжения наследуют имя группы (3 строки у 23-ИСП-1)", len(isp) == 3)
    check("пары 1, 2 и 4 захвачены", ",".join(sorted(r.pair_number for r in isp)) == "1,2,4")
    check("подвал 'Учебная часть' не считается заменой", not any("учебная часть" in r.group.lower() for r in fri.rows))

    check("нет ложной аномалии на корректном файле", len(find_zameny_anomalies(sched, zam)) == 0)

    # подставляем реальную опечатку (блок записан под 23-ИСП-2)
    zam2 = parse_zameny(load_active_sheet(SAMPLES / "zameny_2026-09.xlsx"))
    for b in zam2:
        for row in b.rows:
            if row.group == "23-ИСП-1":
                row.group = "23-ИСП-2"
    anomalies = find_zameny_anomalies(sched, zam2)
    check("опечатка поймана: 23-ИСП-2 -> 23-ИСП-1", len(anomalies) == 1 and anomalies[0].likely_group == "23-ИСП-1")
    check("аномалия несёт все 3 строки", len(anomalies[0].rows) == 3)

    # --- старый формат 2026-06 всё ещё парсится --------------------------
    zam_old = parse_zameny(load_active_sheet(SAMPLES / "zameny.xlsx"))
    check("старый июньский формат парсит блок с датой", any(re.search(r"\d{2}\.\d{2}\.\d{4}", b.date) for b in zam_old))

    print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
