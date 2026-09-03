from __future__ import annotations

import re
from pathlib import Path

import httpx

_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


async def resolve_local_file(source: str, cache_dir: Path, cache_file_name: str) -> Path:
    """Принимает значение из конфига — это либо http(s)-URL (скачивается и
    кешируется на диск), либо локальный путь (используется как есть) — и
    возвращает локальный путь, готовый для openpyxl."""
    if not _URL_RE.match(source):
        return Path(source).resolve()

    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        res = await client.get(source)
        res.raise_for_status()

    cache_dir.mkdir(parents=True, exist_ok=True)
    file_path = cache_dir / cache_file_name
    file_path.write_bytes(res.content)
    return file_path
