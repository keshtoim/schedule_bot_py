from __future__ import annotations

import asyncio
import os
import re
import time
from pathlib import Path

import httpx

_URL_RE = re.compile(r"^https?://", re.IGNORECASE)

_MAX_ATTEMPTS = 3
_RETRY_DELAY_SEC = 1.0


def _is_valid_zip(data: bytes) -> bool:
    """.xlsx — это zip-архив; оборванная загрузка (сеть иногда рвётся на
    середине) даёт файл, который openpyxl отвергает как «битый zip». Проверка
    сигнатуры локального заголовка zip ловит это до записи на диск."""
    return len(data) > 4 and data[0] == 0x50 and data[1] == 0x4B


async def _download_with_retry(source: str) -> bytes:
    last_error: Exception | None = None

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                res = await client.get(source)
                res.raise_for_status()
            data = res.content
            if not _is_valid_zip(data):
                raise ValueError(
                    f"Downloaded file from {source} is not a valid .xlsx (truncated or bad response)"
                )
            return data
        except Exception as err:  # noqa: BLE001 — повторяем любую сетевую ошибку
            last_error = err
            if attempt < _MAX_ATTEMPTS:
                await asyncio.sleep(_RETRY_DELAY_SEC * attempt)

    assert last_error is not None
    raise last_error


async def resolve_local_file(source: str, cache_dir: Path, cache_file_name: str) -> Path:
    """Принимает значение из конфига — это либо http(s)-URL (скачивается и
    кешируется на диск), либо локальный путь (используется как есть) — и
    возвращает локальный путь, готовый для openpyxl."""
    if not _URL_RE.match(source):
        return Path(source).resolve()

    data = await _download_with_retry(source)

    cache_dir.mkdir(parents=True, exist_ok=True)
    file_path = cache_dir / cache_file_name

    # Пишем в уникальный временный файл и переименовываем на место (атомарно
    # в пределах тома), чтобы читатель никогда не увидел недописанный файл,
    # даже если две загрузки одного cache_file_name наложились друг на друга.
    tmp_path = cache_dir / f"{cache_file_name}.{os.getpid()}-{time.time_ns()}.tmp"
    tmp_path.write_bytes(data)
    os.replace(tmp_path, file_path)
    return file_path
