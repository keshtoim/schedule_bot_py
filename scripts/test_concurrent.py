"""Гонка при параллельной загрузке: python -m scripts.test_concurrent"""

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
os.environ["DATA_DIR"] = str(SAMPLES / "_data_concurrent")

from schedule_bot.services.day_view import format_day, format_week  # noqa: E402


async def main() -> None:
    # Несколько параллельных вызовов — как два нажатия кнопки почти одновременно.
    results = await asyncio.gather(
        format_day("24-МТОЭРПО", date(2026, 6, 16)),
        format_week("24-МТОЭРПО", date(2026, 6, 16)),
        format_day("25-ТМ", date(2026, 6, 17)),
        format_week("25-ТМ", date(2026, 6, 16)),
    )

    print("All", len(results), "concurrent calls resolved OK.")
    print(results[0][:60])


if __name__ == "__main__":
    asyncio.run(main())
