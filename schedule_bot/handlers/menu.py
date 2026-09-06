import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message

from ..keyboards import Button, build_main_menu, build_more_menu
from ..services.schedule_service import get_schedule_file_path, get_zameny_file_path
from ..store.user_store import get_user_group
from .common import resolve_group, thinking

router = Router(name="menu")
log = logging.getLogger(__name__)


@router.message(F.text == Button.MORE)
async def handle_more(message: Message) -> None:
    group = await resolve_group(message)
    if not group:
        return
    await message.answer("Ещё:", reply_markup=build_more_menu())


@router.message(F.text == Button.BACK)
async def handle_back(message: Message) -> None:
    group = await resolve_group(message)
    if not group:
        return
    await message.answer("Меню:", reply_markup=build_main_menu(group))


@router.message(Command("menu"))
async def handle_menu(message: Message, state: FSMContext) -> None:
    await state.clear()  # /menu прерывает незавершённый диалог
    group = await get_user_group(message.chat.id)
    await message.answer("Кнопки на месте 👇", reply_markup=build_main_menu(group))


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


@router.message(F.text == Button.SCHEDULE_FILE)
async def handle_schedule_file(message: Message) -> None:
    await _send_source_file(message, "расписание", "raspisanie.xlsx", get_schedule_file_path)


@router.message(F.text == Button.ZAMENY_FILE)
async def handle_zameny_file(message: Message) -> None:
    await _send_source_file(message, "замены", "zameny.xlsx", get_zameny_file_path)
