from __future__ import annotations

from aiogram.types import Message

from ..keyboards import NO_GROUP_HINT, build_main_menu
from ..store.user_store import get_user_group


async def resolve_group(message: Message) -> str | None:
    """Группа пользователя или None. Если группы нет — сам отвечает подсказкой
    (и заодно возвращает клавиатуру «Запустить»), хендлеру остаётся выйти."""
    group = await get_user_group(message.chat.id)
    if not group:
        await message.answer(NO_GROUP_HINT, reply_markup=build_main_menu(None))
    return group
