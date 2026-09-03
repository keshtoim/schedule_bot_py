from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


class Button:
    TODAY = "📅 Сегодня"
    TOMORROW = "📆 Завтра"
    WEEK = "🗓 Неделя"
    ZAMENY = "🔁 Замены"
    GROUP = "👥 Моя группа"


main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=Button.TODAY), KeyboardButton(text=Button.TOMORROW)],
        [KeyboardButton(text=Button.WEEK)],
        [KeyboardButton(text=Button.ZAMENY), KeyboardButton(text=Button.GROUP)],
    ],
    resize_keyboard=True,
)
