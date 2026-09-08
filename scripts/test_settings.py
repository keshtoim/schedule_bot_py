"""Багрепорты и сброс профиля: python -m scripts.test_settings"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

_DATA = Path(tempfile.mkdtemp(prefix="settings-test-"))
os.environ["DATA_DIR"] = str(_DATA)
os.environ.setdefault("BOT_TOKEN", "test")
os.environ.setdefault("SCHEDULE_SOURCE", "x")
os.environ.setdefault("ZAMENY_SOURCE", "y")
os.environ["OWNER_CHAT_ID"] = ""  # пусто и явно, чтобы .env не подставил своё

from schedule_bot.config import config  # noqa: E402
from schedule_bot.feedback import _log_file, report_bug  # noqa: E402
from schedule_bot.store.user_store import forget_user, get_user_group, set_user_group  # noqa: E402

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


class FakeBot:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str, **kw) -> None:
        self.sent.append((chat_id, text))


class FakeUser:
    id = 777
    username = "tester"
    full_name = "Test Er"


async def main() -> None:
    # --- багрепорт без OWNER_CHAT_ID: в файл и в лог, владельцу не шлём ---
    bot = FakeBot()
    await report_bug(bot, FakeUser(), "23-ИСП-1", "  на пятницу не та чётность  ")
    check("багрепорт записан в файл", _log_file().is_file())
    rec = json.loads(_log_file().read_text(encoding="utf-8").splitlines()[-1])
    check("в записи — обрезанный текст", rec["text"] == "на пятницу не та чётность")
    check("в записи — группа и id", rec["group"] == "23-ИСП-1" and rec["user_id"] == 777)
    check("без OWNER_CHAT_ID владельцу не слали", bot.sent == [])

    # --- багрепорт с OWNER_CHAT_ID -> сообщение владельцу ------------
    object.__setattr__(config, "owner_chat_id", 999)
    bot2 = FakeBot()
    await report_bug(bot2, FakeUser(), None, "вторая проблема")
    check("с OWNER_CHAT_ID -> сообщение владельцу", len(bot2.sent) == 1 and bot2.sent[0][0] == 999)
    check("в сообщении владельцу есть текст и «Багрепорт»", "вторая проблема" in bot2.sent[0][1] and "Багрепорт" in bot2.sent[0][1])
    check("обе записи в файле", len(_log_file().read_text(encoding="utf-8").strip().splitlines()) == 2)
    object.__setattr__(config, "owner_chat_id", None)

    # --- forget_user ----------------------------------------------
    await set_user_group(777, "24-ТМ")
    check("группа записана", await get_user_group(777) == "24-ТМ")
    await forget_user(777)
    check("forget_user убрал запись", await get_user_group(777) is None)
    await forget_user(777)
    check("повторный forget_user не падает", True)


try:
    asyncio.run(main())
finally:
    shutil.rmtree(_DATA, ignore_errors=True)

print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
