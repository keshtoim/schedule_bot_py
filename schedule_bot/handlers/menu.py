import logging

from aiogram import F, Router
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..keyboards import Button
from ..services.schedule_service import get_schedule_file_path, get_zameny_file_path
from ..utils.weekday import add_days, today
from .common import thinking
from .full_schedule import send_full_schedule_for
from .week import send_week_for

router = Router(name="menu")
log = logging.getLogger(__name__)


@router.message(F.text == Button.MORE)
async def handle_more(message: Message) -> None:
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Общее расписание", callback_data="more:schedule")
    kb.button(text="➡️ Расписание на след. неделю", callback_data="more:nextweek")
    kb.button(text="📄 Файл расписания (как на сайте)", callback_data="more:schedule_file")
    kb.button(text="📄 Файл замен (как на сайте)", callback_data="more:zameny_file")
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


async def _send_source_file(message: Message, kind: str, filename: str, get_path) -> None:
    """Отдаёт пользователю ту же книгу .xlsx, что бот скачал с сайта колледжа
    — без разбора и форматирования, для самостоятельной проверки."""
    async with thinking(message):
        try:
            path = await get_path()
            await message.answer_document(BufferedInputFile(path.read_bytes(), filename=filename))
        except Exception:
            log.exception("Не удалось отправить файл: %s", kind)
            await message.answer(f"⚠️ Не получилось отправить файл «{kind}». Попробуйте ещё раз позже.")


@router.callback_query(F.data == "more:schedule_file")
async def handle_more_schedule_file(callback: CallbackQuery) -> None:
    await callback.answer()
    await _send_source_file(callback.message, "расписание", "raspisanie.xlsx", get_schedule_file_path)


@router.callback_query(F.data == "more:zameny_file")
async def handle_more_zameny_file(callback: CallbackQuery) -> None:
    await callback.answer()
    await _send_source_file(callback.message, "замены", "zameny.xlsx", get_zameny_file_path)
