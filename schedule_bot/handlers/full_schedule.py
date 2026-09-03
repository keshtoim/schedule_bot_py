import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from ..keyboards import Button
from ..services.day_view import format_full_schedule
from ..services.rich_message import send_rich_message_html
from ..services.schedule_rich_view import build_full_schedule_html
from ..store.user_store import get_user_group

router = Router(name="full_schedule")


@router.message(Command("schedule"))
@router.message(F.text == Button.FULL_SCHEDULE)
async def send_full_schedule(message: Message) -> None:
    group = await get_user_group(message.chat.id)
    if not group:
        await message.answer("Сначала выберите группу: 👥 Моя группа")
        return

    try:
        await send_rich_message_html(message.chat.id, await build_full_schedule_html(group))
    except Exception:
        logging.exception("sendRichMessage failed, falling back to plain HTML message")
        await message.answer(await format_full_schedule(group))
