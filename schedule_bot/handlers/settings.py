import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..feedback import report_bug
from ..keyboards import Button, build_bug_cancel_menu, build_main_menu, build_settings_menu
from ..store.user_store import forget_user, get_user_group
from .common import resolve_group
from .start import send_welcome

router = Router(name="settings")
log = logging.getLogger(__name__)


class BugReport(StatesGroup):
    waiting = State()


@router.message(F.text == Button.SETTINGS)
async def handle_settings(message: Message) -> None:
    if not await resolve_group(message):
        return
    await message.answer("Настройки:", reply_markup=build_settings_menu())


# --- /id: узнать свой chat_id (для OWNER_CHAT_ID) ---------------------
@router.message(Command("id"))
async def handle_id(message: Message) -> None:
    await message.answer(f"Твой chat_id: <code>{message.chat.id}</code>")


# --- Сброс профиля --------------------------------------------------
@router.message(F.text == Button.RESET)
async def reset_ask(message: Message) -> None:
    if not await resolve_group(message):
        return
    kb = InlineKeyboardBuilder()
    kb.button(text="Да, сбросить", callback_data="reset:yes")
    kb.button(text="Отмена", callback_data="reset:no")
    kb.adjust(2)
    await message.answer(
        "Сбросить профиль? Бот забудет твою группу — начнём как с чистого листа.",
        reply_markup=kb.as_markup(),
    )


@router.callback_query(F.data == "reset:no")
async def reset_no(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text("Отменил. Профиль на месте.")


@router.callback_query(F.data == "reset:yes")
async def reset_yes(callback: CallbackQuery) -> None:
    await forget_user(callback.message.chat.id)
    log.info("Профиль сброшен: chat=%s", callback.message.chat.id)
    await callback.answer("Профиль сброшен")
    await callback.message.edit_text("Профиль сброшен.")
    await send_welcome(callback.message)


# --- Сообщить об ошибке (FSM) --------------------------------------
@router.message(F.text == Button.BUG)
async def bug_start(message: Message, state: FSMContext) -> None:
    if not await resolve_group(message):
        return
    await state.set_state(BugReport.waiting)
    await message.answer(
        "Опиши проблему одним сообщением — что не так, что ожидал(а) увидеть.\n"
        "Например: «на пятницу показывает числитель, а должен знаменатель».",
        reply_markup=build_bug_cancel_menu(),
    )


@router.message(BugReport.waiting, F.text == Button.BUG_CANCEL)
async def bug_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    group = await get_user_group(message.chat.id)
    await message.answer("Ок, отменил.", reply_markup=build_main_menu(group))


@router.message(BugReport.waiting, F.text)
async def bug_receive(message: Message, state: FSMContext) -> None:
    if message.text.startswith("/"):
        await message.answer("Опиши проблему текстом или нажми «❌ Отмена».")
        return

    await state.clear()
    group = await get_user_group(message.chat.id)
    await report_bug(message.bot, message.from_user, group, message.text)
    await message.answer(
        "Спасибо! Передал разработчику — разберёмся 🙏",
        reply_markup=build_main_menu(group),
    )


@router.message(BugReport.waiting)
async def bug_not_text(message: Message) -> None:
    await message.answer("Опиши проблему текстом или нажми «❌ Отмена».")
