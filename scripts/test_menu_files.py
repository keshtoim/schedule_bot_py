"""Кнопки «Ещё» — отправка исходных файлов: python -m scripts.test_menu_files"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from schedule_bot.handlers.menu import _send_source_file

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


class _Bot:
    async def send_chat_action(self, chat_id: int, action: str) -> None:
        pass


class _Chat:
    id = 1


class _Message:
    def __init__(self) -> None:
        self.bot = _Bot()
        self.chat = _Chat()
        self.texts: list[str] = []
        self.documents: list[tuple[bytes, str]] = []

    async def answer(self, text: str, **kw) -> "_Message":
        self.texts.append(text)
        return _Message()

    async def answer_document(self, document, **kw) -> None:
        self.documents.append((document.data, document.filename))


async def _ok_path() -> Path:
    return Path(__file__)  # любой существующий файл, содержимое не важно


async def _boom_path() -> Path:
    raise RuntimeError("сеть недоступна")


async def main() -> None:
    ok = _Message()
    await _send_source_file(ok, "расписание", "raspisanie.xlsx", _ok_path)
    check("файл отправлен документом", len(ok.documents) == 1)
    check("имя файла верное", ok.documents and ok.documents[0][1] == "raspisanie.xlsx")
    check("текстом ничего лишнего не ответили", ok.texts == [])

    boom = _Message()
    await _send_source_file(boom, "замены", "zameny.xlsx", _boom_path)
    check("документ не ушёл", boom.documents == [])
    check("пользователю сообщили об ошибке", boom.texts and "замены" in boom.texts[0])


asyncio.run(main())
print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
