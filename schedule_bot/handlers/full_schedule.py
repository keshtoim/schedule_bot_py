import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from ..keyboards import Button
from ..services.day_view import format_full_schedule
from ..services.rich_message import send_rich_message_html
from ..services.schedule_rich_view import build_full_schedule_html
from .common import resolve_group, thinking

router = Router(name="full_schedule")
log = logging.getLogger(__name__)


async def send_full_schedule_for(message: Message) -> None:
    group = await resolve_group(message)
    if not group:
        return

    async with thinking(message):
        try:
            await send_rich_message_html(message.chat.id, await build_full_schedule_html(group))
        except Exception:
            log.warning("Общее расписание: rich-сообщение не ушло, шлю обычным текстом", exc_info=True)
            await message.answer(await format_full_schedule(group))


@router.message(Command("schedule"))
@router.message(F.text == Button.FULL_SCHEDULE)
async def send_full_schedule(message: Message) -> None:
    await send_full_schedule_for(message)
