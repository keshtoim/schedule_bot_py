from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from ..keyboards import Button
from ..services.day_view import format_week
from ..store.user_store import get_user_group

router = Router(name="week")


@router.message(Command("week"))
@router.message(F.text == Button.WEEK)
async def send_week(message: Message) -> None:
    group = await get_user_group(message.chat.id)
    if not group:
        await message.answer("Сначала выберите группу: 👥 Моя группа")
        return
    await message.answer(await format_week(group))
