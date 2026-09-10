import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..keyboards import (
    Button,
    build_group_confirm,
    build_group_picker,
    build_main_menu,
    build_reminder_picker,
)
from ..services.schedule_service import get_schedule
from ..store.reminders import was_asked
from ..store.user_store import set_user_group
from ..utils.html import escape_html

router = Router(name="group")
log = logging.getLogger(__name__)


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
    # "year:23" — первая страница; "year:23:2" — листание внутри курса
    parts = callback.data.split(":", 2)
    year = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 0

    schedule = await get_schedule()
    groups = sorted(g for g in schedule.groups if _year_of(g) == year)

    await callback.message.edit_text(
        "Выберите группу:", reply_markup=build_group_picker(year, groups, page)
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def handle_noop(callback: CallbackQuery) -> None:
    # кнопка-индикатор «N/M» — нажатие ничего не делает
    await callback.answer()


@router.callback_query(F.data == "back:courses")
async def handle_back(callback: CallbackQuery) -> None:
    await _show_courses(callback.message, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("grp:"))
async def handle_pick_group(callback: CallbackQuery) -> None:
    # Сначала подтверждаем — особенно важно после нечёткого текстового поиска.
    group = callback.data.split(":", 1)[1]
    await callback.message.edit_text(
        f"Выбрана группа <b>{escape_html(group)}</b>. Всё верно?",
        reply_markup=build_group_confirm(group),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("grpok:"))
async def handle_confirm_group(callback: CallbackQuery) -> None:
    group = callback.data.split(":", 1)[1]
    chat_id = callback.message.chat.id
    await set_user_group(chat_id, group)
    log.info("Группа сохранена: chat=%s → %s", chat_id, group)
    await callback.message.edit_text(f"Группа сохранена: <b>{escape_html(group)}</b>")
    await callback.answer()

    if not was_asked(chat_id):
        # первый онбординг — спрашиваем вечернее время, «Готово» пришлёт remo-хендлер
        await callback.message.answer(
            "Во сколько присылать расписание на завтра?\n"
            "<i>Утренние напоминания «на сегодня» потом включаются в ⚙️ Настройки → 🔔 Уведомления.</i>",
            reply_markup=build_reminder_picker("remo", "evening"),
        )
    else:
        await callback.message.answer("Готово! Пользуйся меню внизу 👇", reply_markup=build_main_menu(group))
