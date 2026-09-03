from __future__ import annotations

import asyncio
import contextlib
import logging
import random
from collections.abc import AsyncIterator

from aiogram.types import Message

from ..keyboards import NO_GROUP_HINT, build_main_menu
from ..store.user_store import get_user_group

log = logging.getLogger(__name__)


async def resolve_group(message: Message) -> str | None:
    """Группа пользователя или None. Если группы нет — сам отвечает подсказкой
    (и заодно возвращает клавиатуру «Запустить»), хендлеру остаётся выйти."""
    group = await get_user_group(message.chat.id)
    if not group:
        await message.answer(NO_GROUP_HINT, reply_markup=build_main_menu(None))
    return group


# Фразы-заглушки на время долгой операции (скачивание файлов, разбор замен).
# Берутся по кругу в случайном порядке, чтобы не примелькались.
THINKING_PHRASES = (
    "🔎 Изучаю файлы…",
    "📚 Листаю расписание…",
    "🗂 Разбираю замены…",
    "⏳ Собираю данные…",
    "📡 Тяну свежие файлы колледжа…",
    "✍️ Сверяю замены с расписанием…",
    "🧮 Раскладываю числитель и знаменатель…",
    "🤏 Секунду, готовлю ответ…",
)

_THINKING_DELAY_SEC = 0.4


@contextlib.asynccontextmanager
async def thinking(message: Message, delay: float = _THINKING_DELAY_SEC) -> AsyncIterator[None]:
    """Показывает исчезающее сообщение-заглушку, если операция затянулась
    дольше `delay`, и убирает его, как только готов настоящий ответ. Если
    ответ пришёл быстро (данные из кеша) — пользователь заглушку не увидит."""
    placeholder: Message | None = None

    async def _show() -> None:
        nonlocal placeholder
        try:
            await asyncio.sleep(delay)
            await message.bot.send_chat_action(message.chat.id, "typing")
            placeholder = await message.answer(random.choice(THINKING_PHRASES))
        except asyncio.CancelledError:
            raise
        except Exception:
            log.debug("thinking: не удалось показать заглушку", exc_info=True)

    task = asyncio.create_task(_show())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        if placeholder is not None:
            with contextlib.suppress(Exception):
                await placeholder.delete()
