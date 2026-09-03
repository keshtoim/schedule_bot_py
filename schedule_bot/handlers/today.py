import logging
from datetime import date

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from ..keyboards import Button
from ..services.day_view import format_day
from ..services.rich_message import send_rich_message_html
from ..services.schedule_rich_view import build_day_html
from ..utils.weekday import today, tomorrow
from .common import resolve_group

router = Router(name="today")
log = logging.getLogger(__name__)


async def _send_day(message: Message, group: str, day_date: date) -> None:
    try:
        await send_rich_message_html(message.chat.id, await build_day_html(group, day_date))
    except Exception:
        log.warning("День %s: rich-сообщение не ушло, шлю обычным текстом", day_date, exc_info=True)
        await message.answer(await format_day(group, day_date))


@router.message(Command("today"))
@router.message(F.text == Button.TODAY)
async def send_today(message: Message) -> None:
    group = await resolve_group(message)
    if not group:
        return
    await _send_day(message, group, today())


@router.message(Command("tomorrow"))
@router.message(F.text == Button.TOMORROW)
async def send_tomorrow(message: Message) -> None:
    group = await resolve_group(message)
    if not group:
        return
    await _send_day(message, group, tomorrow())
