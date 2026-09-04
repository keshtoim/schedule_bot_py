from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


class Button:
    TODAY = "📅 Сегодня"
    TOMORROW = "📆 Завтра"
    WEEK = "🗓 Неделя"
    ZAMENY = "🔁 Замены"
    MORE = "☰ Ещё"
    BACK = "◀️ Назад"
    LAUNCH = "▶️ Запустить"
    NEXT_WEEK = "➡️ След. неделя"
    FULL_SCHEDULE = "📋 Общее расписание"
    SCHEDULE_FILE = "📄 Файл расписания"
    ZAMENY_FILE = "📄 Файл замен"
    # Кнопка группы динамическая ("👥 23-ИСП-1"), поэтому матчим по префиксу.
    GROUP_PREFIX = "👥"


NO_GROUP_HINT = "Сначала нажми «▶️ Запустить» и выбери группу."


def group_button_text(group: str) -> str:
    return f"{Button.GROUP_PREFIX} {group}"


def build_main_menu(group: str | None) -> ReplyKeyboardMarkup:
    """Клавиатура под пользователя: без группы — одна кнопка «Запустить»,
    с группой — полное меню, где кнопка группы показывает её название."""
    if not group:
        keyboard = [[KeyboardButton(text=Button.LAUNCH)]]
    else:
        keyboard = [
            [KeyboardButton(text=Button.TODAY), KeyboardButton(text=Button.TOMORROW)],
            [KeyboardButton(text=Button.WEEK), KeyboardButton(text=Button.ZAMENY)],
            [KeyboardButton(text=group_button_text(group)), KeyboardButton(text=Button.MORE)],
        ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, is_persistent=True)


def build_more_menu() -> ReplyKeyboardMarkup:
    """Подменю «Ещё»: подменяет нижнюю клавиатуру на реже нужные разделы,
    «Назад» возвращает build_main_menu."""
    keyboard = [
        [KeyboardButton(text=Button.FULL_SCHEDULE)],
        [KeyboardButton(text=Button.NEXT_WEEK)],
        [KeyboardButton(text=Button.SCHEDULE_FILE), KeyboardButton(text=Button.ZAMENY_FILE)],
        [KeyboardButton(text=Button.BACK)],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, is_persistent=True)
