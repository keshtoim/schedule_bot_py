from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


class Button:
    TODAY = "📅 Сегодня"
    TOMORROW = "📆 Завтра"
    WEEK = "🗓 Неделя"
    ZAMENY = "🔁 Замены"
    MORE = "☰ Ещё"
    LAUNCH = "▶️ Запустить"
    # Кнопка группы динамическая ("👥 23-ИСП-1"), поэтому матчим по префиксу.
    GROUP_PREFIX = "👥"

    # Оставлены ради старых закешированных у пользователей клавиатур —
    # команды /schedule и /nextweek и эти тексты всё ещё обрабатываются.
    NEXT_WEEK = "➡️ След. неделя"
    FULL_SCHEDULE = "📋 Общее расписание"


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
