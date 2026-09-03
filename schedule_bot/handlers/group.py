from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..keyboards import Button, build_main_menu
from ..services.schedule_service import get_schedule
from ..store.user_store import set_user_group
from ..utils.html import escape_html

router = Router(name="group")


def _year_of(group: str) -> str:
    return group.split("-")[0]


async def _show_courses(message: Message, *, edit: bool) -> None:
    schedule = await get_schedule()
    years = sorted({_year_of(g) for g in schedule.groups}, reverse=True)
    kb = InlineKeyboardBuilder()
    for year in years:
        kb.button(text=f"Курс {year}", callback_data=f"year:{year}")
    kb.adjust(2)
    if edit:
        await message.edit_text("Выберите курс:", reply_markup=kb.as_markup())
    else:
        await message.answer("Выберите курс:", reply_markup=kb.as_markup())


@router.message(Command("group"))
@router.message(F.text == Button.LAUNCH)
@router.message(F.text.startswith(Button.GROUP_PREFIX))
async def handle_group_command(message: Message) -> None:
    await _show_courses(message, edit=False)


@router.callback_query(F.data.startswith("year:"))
async def handle_year(callback: CallbackQuery) -> None:
    year = callback.data.split(":", 1)[1]
    schedule = await get_schedule()
    groups = [g for g in schedule.groups if _year_of(g) == year]

    kb = InlineKeyboardBuilder()
    for group in groups:
        kb.button(text=group, callback_data=f"grp:{group}")
    kb.adjust(2)
    kb.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back:courses"))

    await callback.message.edit_text("Выберите группу:", reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query(F.data == "back:courses")
async def handle_back(callback: CallbackQuery) -> None:
    await _show_courses(callback.message, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("grp:"))
async def handle_pick_group(callback: CallbackQuery) -> None:
    group = callback.data.split(":", 1)[1]
    await set_user_group(callback.message.chat.id, group)
    await callback.message.edit_text(f"Группа сохранена: <b>{escape_html(group)}</b>")
    await callback.answer()
    await callback.message.answer("Готово! Пользуйся меню внизу 👇", reply_markup=build_main_menu(group))
