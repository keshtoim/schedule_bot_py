"""Команды только для владельца (OWNER_CHAT_ID): рассылка и режим техработ."""

from __future__ import annotations

import asyncio
import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .. import maintenance
from ..config import config
from ..services.stats import format_stats
from ..store.user_store import get_all_chats

router = Router(name="admin")
log = logging.getLogger(__name__)

# текст ждущей подтверждения рассылки; владелец один, так что хватит модульной переменной
_pending: str | None = None


def _is_owner(message: Message) -> bool:
    return config.owner_chat_id is not None and message.chat.id == config.owner_chat_id


@router.message(Command("maintenance"))
async def handle_maintenance(message: Message) -> None:
    if not _is_owner(message):
        return
    on = maintenance.toggle()
    if on:
        await message.answer(
            "🔧 Режим техработ <b>включён</b>. Всем, кроме тебя, бот отвечает «вернусь позже».\n"
            "Выключить — снова /maintenance."
        )
    else:
        await message.answer("✅ Режим техработ <b>выключен</b>. Бот снова работает для всех.")


@router.message(Command("stats"))
async def handle_stats(message: Message) -> None:
    if not _is_owner(message):
        return
    await message.answer(format_stats(await get_all_chats()))


@router.message(Command("announce"))
async def handle_announce(message: Message, command: CommandObject) -> None:
    if not _is_owner(message):
        return
    global _pending
    text = (command.args or "").strip()
    if not text:
        await message.answer(
            "Рассылка всем пользователям:\n<code>/announce текст сообщения</code>\n\n"
            "Например: <code>/announce Сегодня в 22:00 бот ненадолго уйдёт на обновление</code>"
        )
        return

    _pending = text
    chats = await get_all_chats()
    kb = InlineKeyboardBuilder()
    kb.button(text=f"Разослать ({len(chats)})", callback_data="ann:go")
    kb.button(text="Отмена", callback_data="ann:no")
    kb.adjust(2)
    await message.answer(f"Разослать это {len(chats)} пользователям?\n\n📢 {text}", reply_markup=kb.as_markup())


@router.callback_query(F.data == "ann:no")
async def announce_cancel(callback: CallbackQuery) -> None:
    global _pending
    _pending = None
    await callback.answer()
    await callback.message.edit_text("Рассылка отменена.")


@router.callback_query(F.data == "ann:go")
async def announce_send(callback: CallbackQuery) -> None:
    global _pending
    if callback.message.chat.id != config.owner_chat_id or not _pending:
        await callback.answer("Нечего рассылать")
        return

    text = _pending
    _pending = None
    await callback.answer("Рассылаю…")
    await callback.message.edit_text("Рассылаю…")

    sent = failed = 0
    for chat_id, _ in await get_all_chats():
        try:
            await callback.bot.send_message(chat_id, f"📢 {text}")
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    log.info("Рассылка владельца: %d ок, %d с ошибкой", sent, failed)
    await callback.message.answer(f"Готово: {sent} доставлено, {failed} с ошибкой.")
