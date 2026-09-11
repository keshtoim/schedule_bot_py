from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from ..config import config
from ..parser.schedule_parser import Schedule, parse_schedule
from ..parser.workbook import load_active_sheet
from ..parser.zameny_parser import ZamenyBlock, parse_zameny
from .college_page_scraper import fetch_college_links
from ..utils.describe_error import describe_error
from .file_source import FetchResult, resolve_local_file
from .group_reconcile import ZamenyAnomaly, find_zameny_anomalies

log = logging.getLogger(__name__)


@dataclass
class CachedData:
    schedule: Schedule
    zameny: list[ZamenyBlock]
    schedule_file_path: Path
    zameny_file_path: Path
    anomalies: list[ZamenyAnomaly]
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


async def _load_schedule(fetch: FetchResult, prev: CachedData | None) -> Schedule:
    # Сервер подтвердил, что файл с прошлой загрузки не менялся (HTTP 304) —
    # раз мы уже разбирали его в этом процессе, разбирать заново нечего.
    if fetch.unchanged and prev is not None:
        return prev.schedule
    sheet = await asyncio.to_thread(load_active_sheet, fetch.path)
    return parse_schedule(sheet)


async def _load_zameny(fetch: FetchResult, prev: CachedData | None) -> list[ZamenyBlock]:
    if fetch.unchanged and prev is not None:
        return prev.zameny
    sheet = await asyncio.to_thread(load_active_sheet, fetch.path)
    return parse_zameny(sheet)


async def _fetch_data() -> CachedData:
    started = time.time()
    log.info("Проверяю данные: расписание + замены")
    cache_dir = config.data_path / "cache"
    schedule_src, zameny_src = await _resolve_source_urls()
    prev = _cache  # с прошлого успешного разбора в этом же процессе

    schedule_fetch, zameny_fetch = await asyncio.gather(
        resolve_local_file(schedule_src, cache_dir, "raspisanie.xlsx"),
        resolve_local_file(zameny_src, cache_dir, "zameny.xlsx"),
    )

    schedule, zameny = await asyncio.gather(
        _load_schedule(schedule_fetch, prev),
        _load_zameny(zameny_fetch, prev),
    )

    log.info(
        "Готово за %.1f с: расписание — %s (%d групп / %d дней); замены — %s (%d блок(ов), %d строк)",
        time.time() - started,
        "не менялось" if schedule_fetch.unchanged and prev is not None else "разобрано",
        len(schedule.groups),
        len(schedule.days),
        "не менялись" if zameny_fetch.unchanged and prev is not None else "разобраны",
        len(zameny),
        sum(len(b.rows) for b in zameny),
    )

    both_unchanged = schedule_fetch.unchanged and zameny_fetch.unchanged and prev is not None
    if both_unchanged:
        anomalies = prev.anomalies
    else:
        # Best-effort — баг в проверке несоответствий не должен ломать обычную
        # выдачу расписания и замен.
        try:
            anomalies = find_zameny_anomalies(schedule, zameny)
            if anomalies:
                log.warning(
                    "Замены: возможные опечатки в названиях групп — %d: %s",
                    len(anomalies),
                    ", ".join(f"{a.stated_group}→{a.likely_group}" for a in anomalies),
                )
        except Exception:
            log.exception("Не удалось проверить замены на несоответствия")
            anomalies = []

    return CachedData(
        schedule=schedule,
        zameny=zameny,
        schedule_file_path=schedule_fetch.path,
        zameny_file_path=zameny_fetch.path,
        anomalies=anomalies,
        fetched_at=time.time(),
    )


async def _run_fetch() -> CachedData:
    global _cache, _in_flight
    try:
        _cache = await _fetch_data()
        return _cache
    except Exception as err:
        log.error("Не удалось обновить данные: %s", describe_error(err), exc_info=True)
        raise
    finally:
        _in_flight = None


async def get_data() -> CachedData:
    """Параллельные вызовы (например два быстрых нажатия кнопок) должны ждать
    одну и ту же загрузку, а не запускать каждый свою — два писателя в один
    файл кеша и приводили к ошибкам «битый zip»."""
    global _in_flight
    if _cache and _is_fresh(_cache.fetched_at):
        log.debug("Данные из кеша (возраст %.0f с)", time.time() - _cache.fetched_at)
        return _cache
    if _in_flight is None:
        log.info("Кеш устарел или пуст — запускаю обновление")
        _in_flight = asyncio.ensure_future(_run_fetch())
    else:
        log.debug("Обновление уже идёт — жду его")
    return await _in_flight


async def get_schedule() -> Schedule:
    return (await get_data()).schedule


async def get_zameny() -> list[ZamenyBlock]:
    return (await get_data()).zameny


async def get_zameny_anomalies() -> list[ZamenyAnomaly]:
    return (await get_data()).anomalies


async def get_zameny_file_path() -> Path:
    """Локальный путь к текущей закешированной книге замен — чтобы отдавать её пользователям как есть."""
    return (await get_data()).zameny_file_path


async def get_schedule_file_path() -> Path:
    """Локальный путь к текущей закешированной книге расписания — чтобы отдавать её пользователям как есть."""
    return (await get_data()).schedule_file_path
