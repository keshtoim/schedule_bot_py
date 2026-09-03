import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, ErrorEvent

from .config import config
from .handlers import full_schedule, group, start, today, week, zameny
from .utils.describe_error import describe_error

# Наполняет меню команд "/" в Telegram. Это же заставляет работать нативную
# кнопку "Start" (показывается до первого сообщения или после перезапуска
# бота): она просто отправляет /start.
COMMANDS = [
    BotCommand(command="start", description="Начать / перезапустить бота"),
    BotCommand(command="group", description="Выбрать группу"),
    BotCommand(command="today", description="Расписание на сегодня"),
    BotCommand(command="tomorrow", description="Расписание на завтра"),
    BotCommand(command="week", description="Расписание на эту неделю"),
    BotCommand(command="nextweek", description="Расписание на следующую неделю"),
    BotCommand(command="schedule", description="Общее расписание (числитель и знаменатель)"),
    BotCommand(command="zameny", description="Замены"),
]


async def _on_startup(bot: Bot) -> None:
    try:
        await bot.set_my_commands(COMMANDS)
    except Exception:
        logging.exception("set_my_commands failed")


async def _on_error(event: ErrorEvent) -> None:
    # Без этого необработанная ошибка в хендлере (например недоступен сайт
    # колледжа или API Telegram) только пишется в лог — пользователь видит,
    # что бот замолчал. Все хендлеры уже повторяют временные сетевые ошибки,
    # так что сюда доходит только то, у чего повторы исчерпаны.
    update = event.update
    reason = describe_error(event.exception)
    logging.error("Unhandled error for update %s: %s", update.update_id, reason, exc_info=event.exception)

    target = update.message or (update.callback_query.message if update.callback_query else None)
    if target is not None:
        try:
            await target.answer(f"⚠️ Не получилось получить данные: {reason}")
        except Exception:  # noqa: BLE001
            pass


def create_bot() -> tuple[Bot, Dispatcher]:
    bot = Bot(config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(group.router)
    dp.include_router(today.router)
    dp.include_router(week.router)
    dp.include_router(full_schedule.router)
    dp.include_router(zameny.router)
    dp.startup.register(_on_startup)
    dp.errors.register(_on_error)
    return bot, dp
