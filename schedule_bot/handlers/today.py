from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from ..keyboards import Button
from ..services.day_view import format_day
from ..store.user_store import get_user_group
from ..utils.weekday import today, tomorrow

router = Router(name="today")

_NO_GROUP_MSG = "Сначала выберите группу: 👥 Моя группа"


@router.message(Command("today"))
@router.message(F.text == Button.TODAY)
async def send_today(message: Message) -> None:
    group = await get_user_group(message.chat.id)
    if not group:
        await message.answer(_NO_GROUP_MSG)
        return
    await message.answer(await format_day(group, today()))


@router.message(Command("tomorrow"))
@router.message(F.text == Button.TOMORROW)
async def send_tomorrow(message: Message) -> None:
    group = await get_user_group(message.chat.id)
    if not group:
        await message.answer(_NO_GROUP_MSG)
        return
    await message.answer(await format_day(group, tomorrow()))
