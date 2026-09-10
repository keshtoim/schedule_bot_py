"""FSM-хранилище на диске: python -m scripts.test_fsm_storage"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("BOT_TOKEN", "test")
os.environ.setdefault("SCHEDULE_SOURCE", "x")
os.environ.setdefault("ZAMENY_SOURCE", "y")

from aiogram.fsm.state import State, StatesGroup  # noqa: E402
from aiogram.fsm.storage.base import StorageKey  # noqa: E402

from schedule_bot.store.fsm_storage import JSONFileStorage  # noqa: E402

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


class Demo(StatesGroup):
    waiting = State()


KEY = StorageKey(bot_id=1, chat_id=42, user_id=42)


async def main() -> None:
    path = Path(tempfile.mkdtemp(prefix="fsm-test-")) / "fsm.json"

    st = JSONFileStorage(path)
    check("новое хранилище: состояния нет", await st.get_state(KEY) is None)
    check("новое хранилище: данные пустые", await st.get_data(KEY) == {})

    await st.set_state(KEY, Demo.waiting)
    await st.update_data(KEY, {"draft": "не грузится расписание"})
    check("состояние сохранено строкой", await st.get_state(KEY) == "Demo:waiting")
    check("данные сохранены", (await st.get_data(KEY))["draft"] == "не грузится расписание")
    check("файл на диске появился", path.exists())

    # новый инстанс поверх того же файла — как будто бот перезапустился
    st2 = JSONFileStorage(path)
    check("после «перезапуска» состояние на месте", await st2.get_state(KEY) == "Demo:waiting")
    check("после «перезапуска» данные на месте", (await st2.get_data(KEY))["draft"] == "не грузится расписание")

    # очистка (как state.clear())
    await st2.set_state(KEY, None)
    await st2.set_data(KEY, {})
    check("после clear состояния нет", await st2.get_state(KEY) is None)
    check("после clear данных нет", await st2.get_data(KEY) == {})

    st3 = JSONFileStorage(path)
    check("пустая запись не воскресает после перезапуска", await st3.get_state(KEY) is None)
    import json

    check("файл не копит мусорные ключи", json.loads(path.read_text("utf-8")) == {})

    # битый файл не роняет старт
    path.write_text("{ это не json", encoding="utf-8")
    st4 = JSONFileStorage(path)
    check("битый файл → пустое хранилище, без исключения", await st4.get_state(KEY) is None)

    print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
    sys.exit(0 if failed == 0 else 1)


asyncio.run(main())
