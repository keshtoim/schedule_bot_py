from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..keyboards import Button
from ..utils.weekday import add_days, today
from .full_schedule import send_full_schedule_for
from .week import send_week_for

router = Router(name="menu")


@router.message(F.text == Button.MORE)
async def handle_more(message: Message) -> None:
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Общее расписание", callback_data="more:schedule")
    kb.button(text="➡️ Расписание на след. неделю", callback_data="more:nextweek")
    kb.adjust(1)
    await message.answer("Что показать?", reply_markup=kb.as_markup())


@router.callback_query(F.data == "more:schedule")
async def handle_more_schedule(callback: CallbackQuery) -> None:
    await callback.answer()
    await send_full_schedule_for(callback.message)


@router.callback_query(F.data == "more:nextweek")
async def handle_more_nextweek(callback: CallbackQuery) -> None:
    await callback.answer()
    await send_week_for(callback.message, add_days(today(), 7))
