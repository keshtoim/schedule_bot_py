"""Условная загрузка файлов (ETag/Last-Modified): python -m scripts.test_file_source"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("BOT_TOKEN", "test")
os.environ.setdefault("SCHEDULE_SOURCE", "x")
os.environ.setdefault("ZAMENY_SOURCE", "y")

from schedule_bot.services.file_source import (  # noqa: E402
    FetchResult,
    _conditional_headers,
    _is_valid_zip,
    _load_meta,
    _save_meta,
    resolve_local_file,
)

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


URL = "https://college.tu-bryansk.ru/wp-content/uploads/2026/09/raspisanie.xlsx"

# --- _conditional_headers: чистая логика ------------------------------
check("файла нет на диске → пустые заголовки", _conditional_headers({"url": URL, "etag": "e1"}, URL, False) == {})
check("метаданных нет → пустые заголовки", _conditional_headers({}, URL, True) == {})
check(
    "URL сменился (колледж перезалил под новым именем) → пустые заголовки",
    _conditional_headers({"url": URL, "etag": "e1"}, URL + ".new", True) == {},
)
check(
    "тот же URL, есть и etag, и дата → оба условных заголовка",
    _conditional_headers({"url": URL, "etag": '"e1"', "last_modified": "Wed, 04 Sep 2026 10:00:00 GMT"}, URL, True)
    == {"If-None-Match": '"e1"', "If-Modified-Since": "Wed, 04 Sep 2026 10:00:00 GMT"},
)
check(
    "тот же URL, только дата (сервер не отдаёт ETag)",
    _conditional_headers({"url": URL, "last_modified": "Wed, 04 Sep 2026 10:00:00 GMT"}, URL, True)
    == {"If-Modified-Since": "Wed, 04 Sep 2026 10:00:00 GMT"},
)

# --- _is_valid_zip ------------------------------------------------------
check("zip-сигнатура (PK) — валидно", _is_valid_zip(b"PK\x03\x04rest-does-not-matter"))
check("html-заглушка вместо файла — невалидно", not _is_valid_zip(b"<html>anti-ddos challenge</html>"))
check("пустой/оборванный ответ — невалидно", not _is_valid_zip(b"P"))

# --- _load_meta / _save_meta: атомарный roundtrip рядом с файлом --------
_TMP = Path(tempfile.mkdtemp(prefix="file-source-test-"))
try:
    target = _TMP / "raspisanie.xlsx"
    check("метаданных ещё нет — пустой dict", _load_meta(target) == {})

    meta = {"url": URL, "etag": '"abc"', "last_modified": "Wed, 04 Sep 2026 10:00:00 GMT"}
    _save_meta(target, meta)
    check("метаданные сохранились рядом с файлом", (_TMP / "raspisanie.xlsx.meta.json").exists())
    check("прочитались как записали", _load_meta(target) == meta)

    # --- resolve_local_file: локальный путь (режим разработки) ----------
    sample = _TMP / "sample.xlsx"
    sample.write_bytes(b"PK\x03\x04not a real workbook but that's fine here")

    async def _run() -> FetchResult:
        return await resolve_local_file(str(sample), _TMP / "cache", "raspisanie.xlsx")

    result = asyncio.run(_run())
    check("локальный источник: путь резолвится как есть", result.path == sample.resolve())
    check("локальный источник: unchanged всегда False", result.unchanged is False)
    check("локальный источник: last_modified неизвестен", result.last_modified is None)
finally:
    shutil.rmtree(_TMP, ignore_errors=True)

print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
