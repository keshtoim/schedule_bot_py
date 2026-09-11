from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from ..utils.atomic import write_text_atomic
from ..utils.describe_error import describe_error

log = logging.getLogger(__name__)

_URL_RE = re.compile(r"^https?://", re.IGNORECASE)

_MAX_ATTEMPTS = 3
_RETRY_DELAY_SEC = 1.0


@dataclass
class FetchResult:
    path: Path
    # True — сервер подтвердил «файл с прошлого раза не менялся» (HTTP 304),
    # локальная копия переиспользована без перекачки. Для локальных путей
    # (режим разработки) всегда False — там нечего сверять.
    unchanged: bool
    last_modified: str | None


def _is_valid_zip(data: bytes) -> bool:
    """.xlsx — это zip-архив; оборванная загрузка (сеть иногда рвётся на
    середине) даёт файл, который openpyxl отвергает как «битый zip». Проверка
    сигнатуры локального заголовка zip ловит это до записи на диск."""
    return len(data) > 4 and data[0] == 0x50 and data[1] == 0x4B


def _meta_path(file_path: Path) -> Path:
    return file_path.with_name(file_path.name + ".meta.json")


def _load_meta(file_path: Path) -> dict:
    try:
        return json.loads(_meta_path(file_path).read_text("utf-8"))
    except (OSError, ValueError):
        return {}


def _save_meta(file_path: Path, meta: dict) -> None:
    try:
        write_text_atomic(_meta_path(file_path), json.dumps(meta, ensure_ascii=False))
    except OSError:
        log.warning("Не удалось сохранить метаданные %s", _meta_path(file_path), exc_info=True)


def _conditional_headers(meta: dict, source: str, file_exists: bool) -> dict[str, str]:
    """Заголовки условного запроса (If-None-Match / If-Modified-Since) — пусто,
    если сверять не с чем: копии нет на диске, или колледж отдал файл под
    другим URL (у расписания и замен дата обновления часто прямо в имени
    файла — новое имя само по себе значит «это другой файл», ETag/дата
    заголовков прошлого файла тут ни при чём)."""
    if not file_exists or meta.get("url") != source:
        return {}
    headers = {}
    if meta.get("etag"):
        headers["If-None-Match"] = meta["etag"]
    if meta.get("last_modified"):
        headers["If-Modified-Since"] = meta["last_modified"]
    return headers


@dataclass
class _FetchResponse:
    data: bytes | None  # None — сервер ответил 304, тело не присылал
    etag: str | None
    last_modified: str | None


async def _download_with_retry(source: str, headers: dict[str, str]) -> _FetchResponse:
    last_error: Exception | None = None

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                res = await client.get(source, headers=headers)
                if res.status_code == 304:
                    return _FetchResponse(data=None, etag=res.headers.get("ETag"), last_modified=res.headers.get("Last-Modified"))
                res.raise_for_status()
            data = res.content
            if not _is_valid_zip(data):
                raise ValueError(
                    f"Downloaded file from {source} is not a valid .xlsx (truncated or bad response)"
                )
            return _FetchResponse(data=data, etag=res.headers.get("ETag"), last_modified=res.headers.get("Last-Modified"))
        except Exception as err:  # noqa: BLE001 — повторяем любую сетевую ошибку
            last_error = err
            if attempt < _MAX_ATTEMPTS:
                pause = _RETRY_DELAY_SEC * attempt
                log.warning(
                    "Загрузка %s не удалась (попытка %d/%d): %s — повтор через %.0f с",
                    source, attempt, _MAX_ATTEMPTS, describe_error(err), pause,
                )
                await asyncio.sleep(pause)

    assert last_error is not None
    log.error("Загрузка %s не удалась за %d попыток: %s", source, _MAX_ATTEMPTS, describe_error(last_error))
    raise last_error


async def resolve_local_file(source: str, cache_dir: Path, cache_file_name: str) -> FetchResult:
    """Принимает значение из конфига — это либо http(s)-URL, либо локальный
    путь (режим разработки, используется как есть) — и возвращает локальный
    путь, готовый для openpyxl.

    Для URL сначала спрашиваем сервер условным запросом (ETag/Last-Modified
    прошлой загрузки, сохранённые рядом в `<файл>.meta.json`): если он
    подтверждает «без изменений» (HTTP 304) — качать нечего, отдаём то, что
    уже лежит на диске."""
    if not _URL_RE.match(source):
        log.info("%s: локальный файл %s", cache_file_name, source)
        return FetchResult(path=Path(source).resolve(), unchanged=False, last_modified=None)

    cache_dir.mkdir(parents=True, exist_ok=True)
    file_path = cache_dir / cache_file_name
    meta = _load_meta(file_path)
    headers = _conditional_headers(meta, source, file_path.exists())

    log.info("%s: проверяю %s", cache_file_name, source)
    started = time.monotonic()
    resp = await _download_with_retry(source, headers)

    if resp.data is None:
        log.info(
            "%s: сервер подтвердил «без изменений» за %.1f с — файл от %s",
            cache_file_name, time.monotonic() - started, meta.get("last_modified") or "?",
        )
        _save_meta(file_path, {
            "url": source,
            "etag": resp.etag or meta.get("etag"),
            "last_modified": resp.last_modified or meta.get("last_modified"),
        })
        return FetchResult(path=file_path, unchanged=True, last_modified=meta.get("last_modified"))

    log.info(
        "%s: скачано %.0f КБ за %.1f с (обновлён: %s)",
        cache_file_name, len(resp.data) / 1024, time.monotonic() - started, resp.last_modified or "сервер не сказал",
    )

    # Пишем в уникальный временный файл и переименовываем на место (атомарно
    # в пределах тома), чтобы читатель никогда не увидел недописанный файл,
    # даже если две загрузки одного cache_file_name наложились друг на друга.
    tmp_path = cache_dir / f"{cache_file_name}.{os.getpid()}-{time.time_ns()}.tmp"
    tmp_path.write_bytes(resp.data)
    os.replace(tmp_path, file_path)
    _save_meta(file_path, {"url": source, "etag": resp.etag, "last_modified": resp.last_modified})
    return FetchResult(path=file_path, unchanged=False, last_modified=resp.last_modified)
