"""Переиспользование разбора при HTTP 304 (файл не менялся): python -m scripts.test_schedule_cache"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

os.environ.setdefault("BOT_TOKEN", "test")
os.environ.setdefault("SCHEDULE_SOURCE", "x")
os.environ.setdefault("ZAMENY_SOURCE", "y")

from schedule_bot.services.file_source import FetchResult  # noqa: E402
from schedule_bot.services.schedule_service import CachedData, _load_schedule, _load_zameny  # noqa: E402

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


# Не настоящие Schedule/ZamenyBlock — для проверки достаточно сравнить identity:
# если функция вернула ровно этот объект, значит парсер не запускался.
_PREV_SCHEDULE = object()
_PREV_ZAMENY = object()
_PREV = CachedData(
    schedule=_PREV_SCHEDULE,  # type: ignore[arg-type]
    zameny=_PREV_ZAMENY,  # type: ignore[arg-type]
    schedule_file_path=Path("prev-raspisanie.xlsx"),
    zameny_file_path=Path("prev-zameny.xlsx"),
    anomalies=[],
    fetched_at=0.0,
)

# Путь заведомо не существует — если функция вдруг попытается его распарсить
# вместо переиспользования кеша, она упадёт, а не тихо соврёт.
_MISSING = Path("/does/not/exist/raspisanie.xlsx")


async def main() -> None:
    unchanged = FetchResult(path=_MISSING, unchanged=True, last_modified="Wed, 04 Sep 2026 10:00:00 GMT")

    schedule = await _load_schedule(unchanged, _PREV)
    check("304 + есть предыдущий разбор → отдаём его без парсинга", schedule is _PREV_SCHEDULE)

    zameny = await _load_zameny(unchanged, _PREV)
    check("то же самое для замен", zameny is _PREV_ZAMENY)

    # Файл «не менялся», но это первый запуск процесса — переиспользовать
    # нечего, поэтому обязаны попытаться распарсить (и упасть на несуществующем
    # пути), а не тихо остаться без данных.
    try:
        await _load_schedule(unchanged, None)
        check("без prev пытается распарсить, а не выдумывает данные", False)
    except (OSError, ValueError, Exception):  # noqa: BLE001 — важен сам факт попытки
        check("без prev пытается распарсить, а не выдумывает данные", True)


asyncio.run(main())

print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
