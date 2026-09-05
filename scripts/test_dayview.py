"""Проверка вывода дня: python -m scripts.test_dayview"""

from __future__ import annotations

import asyncio
import os
from datetime import date
from pathlib import Path

SAMPLES = Path(__file__).resolve().parent.parent / "scratch_samples"

if not list(SAMPLES.glob("*.xlsx")):
    print("SKIP: нет scratch_samples/*.xlsx (реальные файлы не в git)")
    raise SystemExit(0)
os.environ.setdefault("BOT_TOKEN", "test")
os.environ["SCHEDULE_SOURCE"] = str(SAMPLES / "raspisanie.xlsx")
os.environ["ZAMENY_SOURCE"] = str(SAMPLES / "zameny.xlsx")
os.environ["DATA_DIR"] = str(SAMPLES / "_data")

from schedule_bot.services.day_view import format_day  # noqa: E402


async def main() -> None:
    # Группа + дата подобраны под реальную замену в образце: 24-МТОЭРПО,
    # пара 2, вторник 16.06.2026 -> "тех.оборуд." отменена ("нет").
    print(await format_day("24-МТОЭРПО", date(2026, 6, 16)))
    print("\n---\n")
    print(await format_day("25-ТМ", date(2026, 6, 16)))
    print("\n---\n")
    print(await format_day("24-МТОЭРПО", date(2026, 6, 21)))  # воскресенье


if __name__ == "__main__":
    asyncio.run(main())
