from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from ..config import config
from ..parser.schedule_parser import Schedule, parse_schedule
from ..parser.workbook import load_active_sheet
from ..parser.zameny_parser import ZamenyBlock, parse_zameny
from .college_page_scraper import fetch_college_links
from .file_source import resolve_local_file


@dataclass
class CachedData:
    schedule: Schedule
    zameny: list[ZamenyBlock]
    fetched_at: float


_cache: CachedData | None = None
_in_flight: asyncio.Task[CachedData] | None = None


def _is_fresh(fetched_at: float) -> bool:
    return time.time() - fetched_at < config.cache_ttl_minutes * 60


async def _resolve_source_urls() -> tuple[str, str]:
    if config.schedule_source and config.zameny_source:
        return config.schedule_source, config.zameny_source
    links = await fetch_college_links(config.college_page_url or "")
    return links.schedule_url, links.zameny_url


async def _fetch_data() -> CachedData:
    cache_dir = config.data_path / "cache"
    schedule_src, zameny_src = await _resolve_source_urls()

    schedule_file, zameny_file = await asyncio.gather(
        resolve_local_file(schedule_src, cache_dir, "raspisanie.xlsx"),
        resolve_local_file(zameny_src, cache_dir, "zameny.xlsx"),
    )

    schedule_sheet, zameny_sheet = await asyncio.gather(
        asyncio.to_thread(load_active_sheet, schedule_file),
        asyncio.to_thread(load_active_sheet, zameny_file),
    )

    return CachedData(
        schedule=parse_schedule(schedule_sheet),
        zameny=parse_zameny(zameny_sheet),
        fetched_at=time.time(),
    )


async def _run_fetch() -> CachedData:
    global _cache, _in_flight
    try:
        _cache = await _fetch_data()
        return _cache
    finally:
        _in_flight = None


async def get_data() -> CachedData:
    """Параллельные вызовы (например два быстрых нажатия кнопок) должны ждать
    одну и ту же загрузку, а не запускать каждый свою — два писателя в один
    файл кеша и приводили к ошибкам «битый zip»."""
    global _in_flight
    if _cache and _is_fresh(_cache.fetched_at):
        return _cache
    if _in_flight is None:
        _in_flight = asyncio.ensure_future(_run_fetch())
    return await _in_flight


async def get_schedule() -> Schedule:
    return (await get_data()).schedule


async def get_zameny() -> list[ZamenyBlock]:
    return (await get_data()).zameny
