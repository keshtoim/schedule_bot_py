"""Режим техработ: python -m scripts.test_maintenance"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path

_DATA = Path(tempfile.mkdtemp(prefix="maint-test-"))
os.environ["DATA_DIR"] = str(_DATA)
os.environ.setdefault("BOT_TOKEN", "test")
os.environ.setdefault("SCHEDULE_SOURCE", "x")
os.environ.setdefault("ZAMENY_SOURCE", "y")
os.environ["OWNER_CHAT_ID"] = "111"

from schedule_bot import maintenance  # noqa: E402
from schedule_bot.middlewares import MaintenanceMiddleware  # noqa: E402

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


class FakeUser:
    def __init__(self, uid: int) -> None:
        self.id = uid


class FakeMessage:
    def __init__(self, uid: int) -> None:
        self.from_user = FakeUser(uid)
        self.replies: list[str] = []

    async def answer(self, text: str, **kw) -> None:
        self.replies.append(text)


# middleware проверяет isinstance(event, Message) — подменяем на время теста
maintenance_mod = sys.modules["schedule_bot.middlewares"]
maintenance_mod.Message = FakeMessage  # type: ignore[assignment]


async def main() -> None:
    mw = MaintenanceMiddleware()
    handled: list[int] = []

    async def handler(event, data):
        handled.append(event.from_user.id)
        return "handled"

    # --- выключено: все проходят ----------------------------------
    check("по умолчанию выключено", not maintenance.is_on())
    m = FakeMessage(999)
    await mw(handler, m, {})
    check("выкл: обычный юзер обработан", handled == [999] and m.replies == [])

    # --- toggle -------------------------------------------------
    check("toggle -> включено", maintenance.toggle() is True)
    check("флаг-файл создан", (_DATA / "maintenance").is_file())

    handled.clear()
    m2 = FakeMessage(999)
    await mw(handler, m2, {})
    check("вкл: обычному юзеру — уведомление, хендлер не вызван", handled == [] and m2.replies == [maintenance.NOTICE])

    handled.clear()
    owner = FakeMessage(111)
    await mw(handler, owner, {})
    check("вкл: владелец работает как обычно", handled == [111] and owner.replies == [])

    check("toggle -> выключено", maintenance.toggle() is False)
    check("флаг-файл удалён", not (_DATA / "maintenance").exists())


try:
    asyncio.run(main())
finally:
    shutil.rmtree(_DATA, ignore_errors=True)

print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
