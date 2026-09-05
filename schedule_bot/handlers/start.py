import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from ..assets import photo
from ..keyboards import build_main_menu
from ..store.user_store import get_user_group
from ..utils.html import escape_html

router = Router(name="start")
log = logging.getLogger(__name__)


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    group = await get_user_group(message.chat.id)

    if not group:
        text = (
            "<b>👋 Привет!</b> Показываю расписание и замены твоей группы.\n\n"
            "Нажми «▶️ Запустить», чтобы выбрать группу."
        )
        pic = photo("welcome")
        if pic:
            try:
                await message.answer_photo(pic, caption=text, reply_markup=build_main_menu(None))
                return
            except Exception:
                log.warning("Не отправилось приветственное фото, шлю текстом", exc_info=True)
        await message.answer(text, reply_markup=build_main_menu(None))
        return

    await message.answer(
        f"<b>С возвращением!</b> Твоя группа — <b>{escape_html(group)}</b>.\n\n"
        "Если она неверная, нажми кнопку с группой внизу и выбери заново.",
        reply_markup=build_main_menu(group),
    )
