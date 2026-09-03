import logging
from datetime import date

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from ..keyboards import Button
from ..services.day_view import format_day
from ..services.rich_message import send_rich_message_html
from ..services.schedule_rich_view import build_day_html
from ..store.user_store import get_user_group
from ..utils.weekday import today, tomorrow

router = Router(name="today")

_NO_GROUP_MSG = "Сначала выберите группу: 👥 Моя группа"


async def _send_day(message: Message, group: str, day_date: date) -> None:
    try:
        await send_rich_message_html(message.chat.id, await build_day_html(group, day_date))
    except Exception:
        logging.exception("sendRichMessage failed, falling back to plain HTML message")
        await message.answer(await format_day(group, day_date))


@router.message(Command("today"))
@router.message(F.text == Button.TODAY)
async def send_today(message: Message) -> None:
    group = await get_user_group(message.chat.id)
    if not group:
        await message.answer(_NO_GROUP_MSG)
        return
    await _send_day(message, group, today())


@router.message(Command("tomorrow"))
@router.message(F.text == Button.TOMORROW)
async def send_tomorrow(message: Message) -> None:
    group = await get_user_group(message.chat.id)
    if not group:
        await message.answer(_NO_GROUP_MSG)
        return
    await _send_day(message, group, tomorrow())
