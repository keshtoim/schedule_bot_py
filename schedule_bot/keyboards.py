from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


class Button:
    TODAY = "📅 Сегодня"
    TOMORROW = "📆 Завтра"
    WEEK = "🗓 Неделя"
    ZAMENY = "🔁 Замены"
    MORE = "☰ Ещё"
    SETTINGS = "⚙️ Настройки"
    BACK = "◀️ Назад"
    LAUNCH = "▶️ Запустить"
    NEXT_WEEK = "➡️ След. неделя"
    FULL_SCHEDULE = "📋 Общее расписание"
    SCHEDULE_FILE = "📄 Файл расписания"
    ZAMENY_FILE = "📄 Файл замен"
    GROUP = "👥 Группа"
    BUG = "🐞 Сообщить об ошибке"
    RESET = "🗑 Сбросить профиль"
    BUG_CANCEL = "❌ Отмена"
    # Кнопка выбора группы: и новая статичная «👥 Группа», и старая
    # закешированная у пользователей динамическая «👥 23-ИСП-1» — матчим по префиксу.
    GROUP_PREFIX = "👥"


NO_GROUP_HINT = "Сначала нажми «▶️ Запустить» и выбери группу."


def build_main_menu(group: str | None) -> ReplyKeyboardMarkup:
    """Клавиатура под пользователя: без группы — одна кнопка «Запустить»,
    с группой — полное меню. Без is_persistent — Telegram даёт свернуть
    клавиатуру своей иконкой."""
    if not group:
        keyboard = [[KeyboardButton(text=Button.LAUNCH)]]
    else:
        keyboard = [
            [KeyboardButton(text=Button.TODAY), KeyboardButton(text=Button.TOMORROW)],
            [KeyboardButton(text=Button.WEEK), KeyboardButton(text=Button.ZAMENY)],
            [KeyboardButton(text=Button.SETTINGS), KeyboardButton(text=Button.MORE)],
        ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def build_more_menu() -> ReplyKeyboardMarkup:
    """Подменю «Ещё»: реже нужные разделы. «Назад» возвращает build_main_menu."""
    keyboard = [
        [KeyboardButton(text=Button.FULL_SCHEDULE)],
        [KeyboardButton(text=Button.NEXT_WEEK)],
        [KeyboardButton(text=Button.SCHEDULE_FILE), KeyboardButton(text=Button.ZAMENY_FILE)],
        [KeyboardButton(text=Button.BACK)],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def build_settings_menu() -> ReplyKeyboardMarkup:
    """Подменю «Настройки». «Назад» возвращает build_main_menu."""
    keyboard = [
        [KeyboardButton(text=Button.GROUP)],
        [KeyboardButton(text=Button.BUG)],
        [KeyboardButton(text=Button.RESET)],
        [KeyboardButton(text=Button.BACK)],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def build_bug_cancel_menu() -> ReplyKeyboardMarkup:
    """Пока бот ждёт текст багрепорта — на клавиатуре только «Отмена»."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=Button.BUG_CANCEL)]], resize_keyboard=True
    )
