from __future__ import annotations

from aiogram.types import (
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


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
    REMINDER = "⏰ Напоминание"
    BUG = "🐞 Сообщить об ошибке"
    RESET = "🗑 Сбросить профиль"
    BUG_CANCEL = "❌ Отмена"
    # Кнопка выбора группы: и новая статичная «👥 Группа», и старая
    # закешированная у пользователей динамическая «👥 23-ИСП-1» — матчим по префиксу.
    GROUP_PREFIX = "👥"


# Во сколько бот присылает расписание на завтра. "off" — не присылать.
REMINDER_CHOICES = ["17:00", "18:00", "19:00", "20:00", "21:00", "22:00"]


NO_GROUP_HINT = "Сначала нажми «▶️ Запустить» и выбери группу."


def build_main_menu(group: str | None) -> ReplyKeyboardMarkup:
    """Клавиатура под пользователя: без группы — одна кнопка «Запустить»,
    с группой — полное меню. Без is_persistent — Telegram даёт свернуть
    клавиатуру своей иконкой."""
    if not group:
        keyboard = [[KeyboardButton(text=Button.LAUNCH)]]
    else:
        keyboard = [
            [KeyboardButton(text=Button.TOMORROW)],
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
        [KeyboardButton(text=Button.GROUP), KeyboardButton(text=Button.REMINDER)],
        [KeyboardButton(text=Button.BUG)],
        [KeyboardButton(text=Button.RESET)],
        [KeyboardButton(text=Button.BACK)],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def build_reminder_picker(prefix: str) -> InlineKeyboardMarkup:
    """Инлайн-выбор времени напоминания. `prefix` — «rem» (настройки) или
    «remo» (онбординг): по нему хендлер понимает, что делать после выбора."""
    kb = InlineKeyboardBuilder()
    for t in REMINDER_CHOICES:
        kb.button(text=t, callback_data=f"{prefix}:{t}")
    kb.button(text="Не напоминать", callback_data=f"{prefix}:off")
    kb.adjust(3, 3, 1)
    return kb.as_markup()


def build_bug_cancel_menu() -> ReplyKeyboardMarkup:
    """Пока бот ждёт текст багрепорта — на клавиатуре только «Отмена»."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=Button.BUG_CANCEL)]], resize_keyboard=True
    )
