"""Middleware логирования действий: python -m scripts.test_logging"""

from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass

from schedule_bot.middlewares import LoggingMiddleware

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


# --- минимальные заглушки под то, что читает middleware ---------------
@dataclass
class _User:
    id: int
    username: str | None


@dataclass
class _Chat:
    id: int


@dataclass
class _Message:
    chat: _Chat
    from_user: _User
    text: str | None = None
    caption: str | None = None


# aiogram проверяет тип через isinstance(event, Message) — подменяем на время теста.
import schedule_bot.middlewares as mw  # noqa: E402

mw.Message = _Message  # type: ignore[assignment]

logs: list[logging.LogRecord] = []


class _Capture(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        logs.append(record)


logging.getLogger("schedule_bot.middlewares").addHandler(_Capture())
logging.getLogger("schedule_bot.middlewares").setLevel(logging.DEBUG)


async def main() -> None:
    middleware = LoggingMiddleware()
    event = _Message(_Chat(42), _User(1, "vasya"), text="📅 Сегодня")

    async def ok_handler(ev, data):
        return "done"

    result = await middleware(ok_handler, event, {})
    check("хендлер отработал, результат проброшен", result == "done")
    msgs = [r.getMessage() for r in logs]
    check("залогировано начало действия", any(m.startswith("▶") and "chat=42" in m and "Сегодня" in m for m in msgs))
    check("залогировано завершение", any(m.startswith("✔") and "chat=42" in m for m in msgs))

    logs.clear()

    async def boom_handler(ev, data):
        raise RuntimeError("бум")

    raised = False
    try:
        await middleware(boom_handler, event, {})
    except RuntimeError:
        raised = True
    check("ошибка проброшена дальше (сработает errors-хендлер)", raised)
    check("ошибка залогирована с ✖", any(r.getMessage().startswith("✖") and r.exc_info for r in logs))


asyncio.run(main())
print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
