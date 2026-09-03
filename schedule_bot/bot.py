from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .config import config
from .handlers import group, start, today, week, zameny


def create_bot() -> tuple[Bot, Dispatcher]:
    bot = Bot(config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(group.router)
    dp.include_router(today.router)
    dp.include_router(week.router)
    dp.include_router(zameny.router)
    return bot, dp
