from aiogram import Bot, Dispatcher

from .config import config
from .handlers import start


def create_bot() -> tuple[Bot, Dispatcher]:
    bot = Bot(config.bot_token)
    dp = Dispatcher()
    dp.include_router(start.router)
    return bot, dp
