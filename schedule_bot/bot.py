import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, ErrorEvent

from .config import config
from .handlers import full_schedule, group, menu, start, today, week, zameny
from .keyboards import build_main_menu
from .services.zameny_notifier import start_zameny_watcher, stop_zameny_watcher
from .store.user_store import get_all_chats
from .utils.describe_error import describe_error
from .utils.html import escape_html

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


# Один раз за жизнь процесса: обрывы поллинга в __main__ перезапускают
# start_polling (а с ним и startup-хендлеры), рассылать при этом повторно не надо.
_restart_notified = False
_restart_task: "asyncio.Task | None" = None


async def _notify_restart(bot: Bot) -> None:
    """После перезапуска бота напоминаем тем, у кого уже выбрана группа,
    проверить её (файлы колледжа к новому семестру часто меняют состав групп)."""
    global _restart_notified
    if _restart_notified:
        return
    _restart_notified = True

    chats = await get_all_chats()
    if not chats:
        return

    logging.info("Уведомление о перезапуске: %d чат(ов)", len(chats))
    for chat_id, group in chats:
        try:
            await bot.send_message(
                chat_id,
                f"♻️ Бот перезапущён. Твоя группа — <b>{escape_html(group)}</b>.\n"
                "Если она неверная — нажми кнопку с группой внизу и выбери заново.",
                reply_markup=build_main_menu(group),
            )
        except Exception:
            logging.warning("Не удалось уведомить чат %s о перезапуске", chat_id, exc_info=True)
        await asyncio.sleep(0.05)  # бережём лимиты Telegram


async def _on_startup(bot: Bot) -> None:
    try:
        await bot.set_my_commands(COMMANDS)
    except Exception:
        logging.exception("set_my_commands failed")
    start_zameny_watcher(bot)
    global _restart_task
    _restart_task = asyncio.create_task(_notify_restart(bot))


async def _on_shutdown() -> None:
    stop_zameny_watcher()


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
    dp.include_router(menu.router)
    dp.startup.register(_on_startup)
    dp.shutdown.register(_on_shutdown)
    dp.errors.register(_on_error)
    return bot, dp
