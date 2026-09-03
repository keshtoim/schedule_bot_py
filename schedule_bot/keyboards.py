from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


class Button:
    TODAY = "📅 Сегодня"
    TOMORROW = "📆 Завтра"
    WEEK = "🗓 Неделя"
    NEXT_WEEK = "➡️ След. неделя"
    FULL_SCHEDULE = "📋 Общее расписание"
    ZAMENY = "🔁 Замены"
    GROUP = "👥 Моя группа"


main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=Button.TODAY), KeyboardButton(text=Button.TOMORROW)],
        [KeyboardButton(text=Button.WEEK), KeyboardButton(text=Button.NEXT_WEEK)],
        [KeyboardButton(text=Button.FULL_SCHEDULE)],
        [KeyboardButton(text=Button.ZAMENY), KeyboardButton(text=Button.GROUP)],
    ],
    resize_keyboard=True,
)
