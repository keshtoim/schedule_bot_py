"""Исчезающее сообщение-заглушка: python -m scripts.test_thinking"""

from __future__ import annotations

import asyncio
import sys

from schedule_bot.handlers.common import THINKING_PHRASES, thinking

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


class _Placeholder:
    def __init__(self) -> None:
        self.deleted = False

    async def delete(self) -> None:
        self.deleted = True


class _Bot:
    def __init__(self) -> None:
        self.actions: list[str] = []

    async def send_chat_action(self, chat_id: int, action: str) -> None:
        self.actions.append(action)


class _Chat:
    id = 1


class _Message:
    def __init__(self) -> None:
        self.bot = _Bot()
        self.chat = _Chat()
        self.sent: list[str] = []
        self.placeholders: list[_Placeholder] = []

    async def answer(self, text: str) -> _Placeholder:
        self.sent.append(text)
        p = _Placeholder()
        self.placeholders.append(p)
        return p


async def main() -> None:
    # --- быстрая работа: заглушку не показываем -----------------------
    fast = _Message()
    async with thinking(fast, delay=0.2):
        await asyncio.sleep(0.01)
    check("быстрый ответ — заглушки не было", fast.sent == [])
    check("быстрый ответ — chat_action не слали", fast.bot.actions == [])

    # --- долгая работа: заглушка показана и убрана --------------------
    slow = _Message()
    async with thinking(slow, delay=0.05):
        await asyncio.sleep(0.2)
    check("долгий ответ — заглушка показана", len(slow.sent) == 1)
    check("долгий ответ — текст из списка фраз", slow.sent[0] in THINKING_PHRASES)
    check("долгий ответ — 'печатает…' отправлено", slow.bot.actions == ["typing"])
    check("долгий ответ — заглушка удалена", slow.placeholders[0].deleted)

    # --- ошибка внутри: заглушку всё равно убираем, ошибка летит выше -
    boom = _Message()
    raised = False
    try:
        async with thinking(boom, delay=0.05):
            await asyncio.sleep(0.1)
            raise RuntimeError("сбой")
    except RuntimeError:
        raised = True
    check("ошибка проброшена", raised)
    check("после ошибки заглушка удалена", boom.placeholders and boom.placeholders[0].deleted)


asyncio.run(main())
print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
