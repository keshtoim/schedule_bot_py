from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

_T = TypeVar("_T")


async def with_retry(
    fn: Callable[[], Awaitable[_T]], attempts: int = 3, delay_sec: float = 0.5
) -> _T:
    """Повторяет ненадёжную async-операцию (сеть иногда рвёт соединение)."""
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            return await fn()
        except Exception as err:  # noqa: BLE001
            last_error = err
            if attempt < attempts:
                await asyncio.sleep(delay_sec * attempt)

    assert last_error is not None
    raise last_error
