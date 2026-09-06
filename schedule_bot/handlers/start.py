import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ..assets import photo
from ..keyboards import build_main_menu
from ..store.user_store import get_user_group
from ..utils.html import escape_html

router = Router(name="start")
log = logging.getLogger(__name__)

_WELCOME = (
    "<b>👋 Привет!</b> Показываю расписание и замены твоей группы.\n\n"
    "Нажми «▶️ Запустить», чтобы выбрать группу."
)


async def send_welcome(message: Message) -> None:
    """Приветствие для нового пользователя (или после сброса профиля):
    фото + текст + клавиатура с одной кнопкой «Запустить»."""
    pic = photo("welcome")
    if pic:
        try:
            await message.answer_photo(pic, caption=_WELCOME, reply_markup=build_main_menu(None))
            return
        except Exception:
            log.warning("Не отправилось приветственное фото, шлю текстом", exc_info=True)
    await message.answer(_WELCOME, reply_markup=build_main_menu(None))


@router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext) -> None:
    await state.clear()  # /start прерывает любой незавершённый диалог (багрепорт)
    group = await get_user_group(message.chat.id)

    if not group:
        await send_welcome(message)
        return

    await message.answer(
        f"<b>С возвращением!</b> Твоя группа — <b>{escape_html(group)}</b>.\n\n"
        "Если она неверная, открой ⚙️ Настройки → 👥 Группа.",
        reply_markup=build_main_menu(group),
    )
