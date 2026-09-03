"""Проверка парсеров на образцах книг: python -m scripts.test_parse"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from schedule_bot.parser.schedule_parser import parse_schedule
from schedule_bot.parser.workbook import load_active_sheet
from schedule_bot.parser.zameny_parser import parse_zameny

SAMPLES = Path(__file__).resolve().parent.parent / "scratch_samples"


def main() -> None:
    schedule = parse_schedule(load_active_sheet(SAMPLES / "raspisanie.xlsx"))
    print("=== SCHEDULE ===")
    print("groups:", len(schedule.groups), schedule.groups)
    print("days:", [f"{d.weekday} ({len(d.pairs)} pairs)" for d in schedule.days])
    mon = next((d for d in schedule.days if d.weekday == "Понедельник"), None)
    print(json.dumps([asdict(p) for p in (mon.pairs[:2] if mon else [])], ensure_ascii=False, indent=2))

    zameny = parse_zameny(load_active_sheet(SAMPLES / "zameny.xlsx"))
    print("\n=== ZAMENY ===")
    print(json.dumps([asdict(b) for b in zameny], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
