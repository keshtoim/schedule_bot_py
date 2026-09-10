import logging
from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..feedback import report_bug
from ..keyboards import (
    Button,
    build_bug_cancel_menu,
    build_main_menu,
    build_notifications_menu,
    build_reminder_picker,
    build_settings_menu,
)
from ..store.reminders import effective_reminder, forget_reminder, set_reminder
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
    chat_id = callback.message.chat.id
    await forget_user(chat_id)
    await forget_reminder(chat_id)
    log.info("Профиль сброшен: chat=%s", chat_id)
    await callback.answer("Профиль сброшен")
    await callback.message.edit_text("Профиль сброшен.")
    await send_welcome(callback.message)


# --- Уведомления: утреннее и вечернее напоминание -----------------
def _reminder_label(value: str) -> str:
    return "выключено" if value == "off" else f"в {value}"


def _notif_summary(chat_id: int) -> tuple[str, InlineKeyboardMarkup]:
    m = effective_reminder(chat_id, "morning")
    e = effective_reminder(chat_id, "evening")
    text = (
        "🔔 <b>Уведомления</b>\n\n"
        f"🌅 Утром, на сегодня — <b>{_reminder_label(m)}</b>\n"
        f"🌆 Вечером, на завтра — <b>{_reminder_label(e)}</b>\n"
        "🔁 Замены — приходят сами, как только появятся на сайте\n\n"
        "Что настроить:"
    )
    return text, build_notifications_menu(_reminder_label(m), _reminder_label(e))


async def _edit(message: Message, text: str, kb: InlineKeyboardMarkup) -> None:
    # «message is not modified» при повторном тапе того же варианта — не ошибка
    with suppress(TelegramBadRequest):
        await message.edit_text(text, reply_markup=kb)


@router.message(F.text == Button.NOTIFICATIONS)
@router.message(F.text == "⏰ Напоминание")  # старая кнопка, закешированная у пользователей
async def notifications_menu(message: Message) -> None:
    if not await resolve_group(message):
        return
    text, kb = _notif_summary(message.chat.id)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "notif:home")
async def notif_home(callback: CallbackQuery) -> None:
    text, kb = _notif_summary(callback.message.chat.id)
    await _edit(callback.message, text, kb)
    await callback.answer()


@router.callback_query(F.data.in_({"notif:morning", "notif:evening"}))
async def notif_pick_kind(callback: CallbackQuery) -> None:
    kind = callback.data.split(":", 1)[1]
    cur = effective_reminder(callback.message.chat.id, kind)
    when = "на сегодня" if kind == "morning" else "на завтра"
    icon = "🌅" if kind == "morning" else "🌆"
    label = "Утреннее" if kind == "morning" else "Вечернее"
    head = (
        f"{icon} <b>{label} напоминание</b> — расписание {when}.\n"
        f"Сейчас: <b>{_reminder_label(cur)}</b>. Выбери время:"
    )
    await _edit(callback.message, head, build_reminder_picker("rem", kind, back="notif:home"))
    await callback.answer()


@router.callback_query(F.data.startswith("rem:") | F.data.startswith("remo:"))
async def reminder_pick(callback: CallbackQuery) -> None:
    parts = callback.data.split(":", 2)
    if len(parts) == 3:
        prefix, kind, value = parts
    else:  # старый двухчастный callback из давно открытого сообщения — это вечернее
        prefix, kind, value = parts[0], "evening", parts[1]
    chat_id = callback.message.chat.id
    await set_reminder(chat_id, kind, value)
    log.info("Напоминание: chat=%s %s → %s", chat_id, kind, value)
    await callback.answer("Сохранено")

    if prefix == "remo":  # финал онбординга (спрашиваем только вечернее)
        group = await get_user_group(chat_id)
        note = "" if value == "off" else f"\nБуду присылать расписание на завтра {_reminder_label(value)}."
        await callback.message.edit_text("Готово! 🎉" + note)
        await callback.message.answer("Пользуйся меню внизу 👇", reply_markup=build_main_menu(group))
    else:
        text, kb = _notif_summary(chat_id)
        await _edit(callback.message, text, kb)


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
