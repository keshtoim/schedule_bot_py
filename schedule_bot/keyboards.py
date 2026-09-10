from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
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
    NOTIFICATIONS = "🔔 Уведомления"
    BUG = "🐞 Сообщить об ошибке"
    RESET = "🗑 Сбросить профиль"
    BUG_CANCEL = "❌ Отмена"
    # Кнопка выбора группы: и новая статичная «👥 Группа», и старая
    # закешированная у пользователей динамическая «👥 23-ИСП-1» — матчим по префиксу.
    GROUP_PREFIX = "👥"


# Время напоминаний. "off" — не присылать. Утро — про пары на сегодня,
# вечер — про пары на завтра.
MORNING_CHOICES = ["06:30", "07:00", "07:30", "08:00", "08:30", "09:00"]
EVENING_CHOICES = ["17:00", "18:00", "19:00", "20:00", "21:00", "22:00"]
REMINDER_CHOICES = EVENING_CHOICES  # обратная совместимость со старыми импортами


def reminder_choices(kind: str) -> list[str]:
    return MORNING_CHOICES if kind == "morning" else EVENING_CHOICES


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
        [KeyboardButton(text=Button.GROUP), KeyboardButton(text=Button.NOTIFICATIONS)],
        [KeyboardButton(text=Button.BUG)],
        [KeyboardButton(text=Button.RESET)],
        [KeyboardButton(text=Button.BACK)],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def build_reminder_picker(prefix: str, kind: str, *, back: str | None = None) -> InlineKeyboardMarkup:
    """Инлайн-выбор времени напоминания. `prefix` — «rem» (настройки) или
    «remo» (онбординг); `kind` — «morning»/«evening». callback_data:
    «{prefix}:{kind}:{ЧЧ:ММ|off}». `back` — на какой экран вернуться кнопкой «Назад»."""
    kb = InlineKeyboardBuilder()
    for t in reminder_choices(kind):
        kb.button(text=t, callback_data=f"{prefix}:{kind}:{t}")
    kb.button(text="Не напоминать", callback_data=f"{prefix}:{kind}:off")
    kb.adjust(3, 3, 1)
    if back:
        kb.row(InlineKeyboardButton(text="◀️ Назад", callback_data=back))
    return kb.as_markup()


def build_notifications_menu(morning_label: str, evening_label: str) -> InlineKeyboardMarkup:
    """Экран «Уведомления»: две кнопки — настроить утреннее / вечернее напоминание."""
    kb = InlineKeyboardBuilder()
    kb.button(text=f"🌅 Утром: {morning_label}", callback_data="notif:morning")
    kb.button(text=f"🌆 Вечером: {evening_label}", callback_data="notif:evening")
    kb.adjust(1)
    return kb.as_markup()


GROUPS_PER_PAGE = 8


def build_group_picker(year: str, groups: list[str], page: int = 0) -> InlineKeyboardMarkup:
    """Список групп курса. Если групп больше одной страницы — добавляет строку
    листания «◀ N/M ▶». `groups` уже отсортирован; `page` считается от 0 и
    зажимается в допустимые границы."""
    total_pages = max(1, (len(groups) + GROUPS_PER_PAGE - 1) // GROUPS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    start = page * GROUPS_PER_PAGE
    chunk = groups[start : start + GROUPS_PER_PAGE]

    kb = InlineKeyboardBuilder()
    for group in chunk:
        kb.button(text=group, callback_data=f"grp:{group}")
    kb.adjust(2)

    if total_pages > 1:
        nav: list[InlineKeyboardButton] = []
        if page > 0:
            nav.append(InlineKeyboardButton(text="◀", callback_data=f"year:{year}:{page - 1}"))
        nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton(text="▶", callback_data=f"year:{year}:{page + 1}"))
        kb.row(*nav)

    kb.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back:courses"))
    return kb.as_markup()


def build_group_confirm(group: str) -> InlineKeyboardMarkup:
    """Подтверждение выбранной группы перед сохранением («верно ли выбрана»)."""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, сохранить", callback_data=f"grpok:{group}")
    kb.button(text="↩️ Выбрать другую", callback_data="back:courses")
    kb.adjust(1)
    return kb.as_markup()


def build_group_search_results(groups: list[str]) -> InlineKeyboardMarkup:
    """Совпадения по текстовому поиску группы: кнопки-группы + выход к списку курсов."""
    kb = InlineKeyboardBuilder()
    for group in groups:
        kb.button(text=group, callback_data=f"grp:{group}")
    kb.adjust(2)
    kb.row(InlineKeyboardButton(text="📚 Все курсы", callback_data="back:courses"))
    return kb.as_markup()


def build_bug_cancel_menu() -> ReplyKeyboardMarkup:
    """Пока бот ждёт текст багрепорта — на клавиатуре только «Отмена»."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=Button.BUG_CANCEL)]], resize_keyboard=True
    )
