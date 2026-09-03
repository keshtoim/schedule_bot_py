"""Живая проверка: скачать данные с сайта колледжа. python -m scripts.test_live"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

SAMPLES = Path(__file__).resolve().parent.parent / "scratch_samples"
os.environ.setdefault("BOT_TOKEN", "test")
os.environ.setdefault("COLLEGE_PAGE_URL", "")
os.environ["DATA_DIR"] = str(SAMPLES / "_data_live")

from schedule_bot.services.college_page_scraper import fetch_college_links  # noqa: E402
from schedule_bot.services.schedule_service import get_schedule, get_zameny  # noqa: E402


async def main() -> None:
    links = await fetch_college_links(os.environ["COLLEGE_PAGE_URL"])
    print("schedule_url:", links.schedule_url)
    print("zameny_url:", links.zameny_url)

    schedule = await get_schedule()
    print("groups:", len(schedule.groups))
    print("days:", [d.weekday for d in schedule.days])

    zameny = await get_zameny()
    print("zameny blocks:", [f"{z.weekday} {z.date} ({len(z.rows)} rows)" for z in zameny])


if __name__ == "__main__":
    asyncio.run(main())
