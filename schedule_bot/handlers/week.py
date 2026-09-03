import logging
from datetime import date

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from ..keyboards import Button
from ..services.day_view import format_week
from ..services.rich_message import send_rich_message_html
from ..services.schedule_rich_view import build_week_html
from ..store.user_store import get_user_group
from ..utils.weekday import add_days, today

router = Router(name="week")


async def _send_week_for(message: Message, around: date) -> None:
    group = await get_user_group(message.chat.id)
    if not group:
        await message.answer("Сначала выберите группу: 👥 Моя группа")
        return

    try:
        await send_rich_message_html(message.chat.id, await build_week_html(group, around))
    except Exception:
        logging.exception("sendRichMessage failed, falling back to plain HTML message")
        await message.answer(await format_week(group, around))


@router.message(Command("week"))
@router.message(F.text == Button.WEEK)
async def send_week(message: Message) -> None:
    await _send_week_for(message, today())


@router.message(Command("nextweek"))
@router.message(F.text == Button.NEXT_WEEK)
async def send_next_week(message: Message) -> None:
    await _send_week_for(message, add_days(today(), 7))
