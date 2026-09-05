"""Проверка вывода недели: python -m scripts.test_week"""

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
os.environ["DATA_DIR"] = str(SAMPLES / "_data_week")

from schedule_bot.services.day_view import format_week  # noqa: E402


async def main() -> None:
    text = await format_week("24-МТОЭРПО", date(2026, 6, 16))  # неделя 16.06.2026
    print(text)
    print("\n--- length:", len(text), "chars ---")


if __name__ == "__main__":
    asyncio.run(main())
