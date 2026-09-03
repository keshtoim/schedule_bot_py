from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from ..keyboards import main_menu

router = Router(name="start")


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    await message.answer(
        "<b>Привет!</b> Я показываю расписание и замены.\n\n"
        "Сначала выберите вашу группу — нажмите «👥 Моя группа» ниже.",
        reply_markup=main_menu,
    )
