from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from .describe_error import describe_error

_T = TypeVar("_T")

log = logging.getLogger(__name__)


async def with_retry(
    fn: Callable[[], Awaitable[_T]],
    attempts: int = 3,
    delay_sec: float = 0.5,
    name: str = "операция",
) -> _T:
    """Повторяет ненадёжную async-операцию (сеть иногда рвёт соединение).
    `name` попадает в лог, чтобы по консоли было видно, что именно повторяется."""
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            return await fn()
        except Exception as err:  # noqa: BLE001
            last_error = err
            if attempt < attempts:
                log.warning(
                    "%s: попытка %d/%d не удалась: %s — повтор", name, attempt, attempts, describe_error(err)
                )
                await asyncio.sleep(delay_sec * attempt)

    assert last_error is not None
    log.error("%s: не удалось за %d попыток: %s", name, attempts, describe_error(last_error))
    raise last_error
