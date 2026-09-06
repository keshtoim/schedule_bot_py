import asyncio
import logging
import time

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramConflictError
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, ErrorEvent

from .assets import photo
from .config import config
from .handlers import full_schedule, group, menu, settings, start, today, week, zameny
from .housekeeping import start_housekeeping, stop_housekeeping
from .keyboards import build_main_menu
from .middlewares import LoggingMiddleware
from .services.zameny_notifier import start_zameny_watcher, stop_zameny_watcher
from .store.user_store import get_all_chats
from .utils.atomic import write_text_atomic
from .utils.describe_error import describe_error, is_network_error
from .utils.html import escape_html

log = logging.getLogger(__name__)

# Не чаще одного раза в это число часов бот сообщает всем «я перезапустился».
# Иначе краш-луп или несколько деплоёв подряд засыпят подписчиков.
_RESTART_NOTIFY_COOLDOWN_H = 12

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
    BotCommand(command="menu", description="Показать кнопки меню"),
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

    stamp = config.data_path / "last-restart-notify"
    try:
        last = float(stamp.read_text())
    except (OSError, ValueError):
        last = 0.0
    if time.time() - last < _RESTART_NOTIFY_COOLDOWN_H * 3600:
        log.info("Уведомление о перезапуске пропущено — было менее %d ч назад", _RESTART_NOTIFY_COOLDOWN_H)
        return

    chats = await get_all_chats()
    if not chats:
        log.info("Уведомление о перезапуске: подписчиков нет")
        return

    log.info("Уведомляю о перезапуске: %d чат(ов)", len(chats))
    pic = photo("updated")
    pic_file_id: str | None = None  # первую отправку кешируем, дальше по file_id
    sent = failed = 0
    for chat_id, group in chats:
        text = (
            f"♻️ Бот перезапущён. Твоя группа — <b>{escape_html(group)}</b>.\n"
            "Если она неверная — открой ⚙️ Настройки → 👥 Группа."
        )
        kb = build_main_menu(group)
        media = pic_file_id or pic
        try:
            if media is not None:
                msg = await bot.send_photo(chat_id, media, caption=text, reply_markup=kb)
                if pic_file_id is None and msg.photo:
                    pic_file_id = msg.photo[-1].file_id
            else:
                await bot.send_message(chat_id, text, reply_markup=kb)
            sent += 1
        except Exception:
            failed += 1
            log.warning("Не удалось уведомить чат %s о перезапуске", chat_id, exc_info=True)
        await asyncio.sleep(0.05)  # бережём лимиты Telegram
    log.info("Уведомление о перезапуске разослано: %d ок, %d с ошибкой", sent, failed)
    try:
        write_text_atomic(stamp, str(time.time()))
    except OSError:
        log.warning("Не записал отметку о рассылке перезапуска — %s", stamp)


async def _on_startup(bot: Bot) -> None:
    log.info("Старт: настраиваю бота")
    try:
        await bot.set_my_commands(COMMANDS)
        log.info("Меню команд обновлено (%d шт.)", len(COMMANDS))
    except Exception:
        log.exception("Не удалось обновить меню команд")
    start_zameny_watcher(bot)
    start_housekeeping()
    global _restart_task
    _restart_task = asyncio.create_task(_notify_restart(bot))


async def _on_shutdown() -> None:
    log.info("Останавливаюсь…")
    stop_zameny_watcher()
    stop_housekeeping()


async def _on_error(event: ErrorEvent) -> None:
    # Без этого необработанная ошибка в хендлере (например недоступен сайт
    # колледжа или API Telegram) только пишется в лог — пользователь видит,
    # что бот замолчал. Все хендлеры уже повторяют временные сетевые ошибки,
    # так что сюда доходит только то, у чего повторы исчерпаны.
    update = event.update
    reason = describe_error(event.exception)
    log.error("Необработанная ошибка (update %s): %s", update.update_id, reason, exc_info=event.exception)

    target = update.message or (update.callback_query.message if update.callback_query else None)
    if target is None:
        return

    text = f"⚠️ Не получилось получить данные: {reason}"
    pic = photo("offline") if is_network_error(event.exception) else None
    try:
        if pic is not None:
            await target.answer_photo(pic, caption=text)
        else:
            await target.answer(text)
    except Exception:  # noqa: BLE001
        pass


async def preflight(bot: Bot, drop_pending: bool = False) -> None:
    """Перед поллингом: гасим вебхук (на всякий) и ловим самую частую ошибку
    деплоя — второй запущенный инстанс — объясняя по-русски. `drop_pending`
    на первом старте выкидывает накопившийся за простой бэклог, чтобы бот не
    отвечал на сутки устаревших «/today»."""
    try:
        await bot.delete_webhook(drop_pending_updates=drop_pending)
        if drop_pending:
            log.info("Накопленные за простой апдейты сброшены")
        await bot.get_updates(limit=1, timeout=1)
    except TelegramConflictError:
        log.error(
            "─── Этот бот уже где-то запущен с тем же токеном ───\n"
            "  Telegram отдаёт getUpdates только одному процессу. Останови\n"
            "  другой инстанс (локальный запуск при живом сервере? второй\n"
            "  контейнер?) или заведи отдельного тестового бота у @BotFather.\n"
            "  Пока не остановишь — polling будет молотить вхолостую."
        )
    except Exception as err:  # noqa: BLE001
        log.warning("Предстартовая проверка не прошла: %s", describe_error(err))


def _mask_credentials(url: str) -> str:
    """socks5://user:pass@host:port -> socks5://***@host:port (для логов)."""
    if "://" in url and "@" in url:
        scheme, rest = url.split("://", 1)
        return f"{scheme}://***@{rest.rsplit('@', 1)[1]}"
    return url


def create_bot() -> tuple[Bot, Dispatcher]:
    session = AiohttpSession(proxy=config.telegram_proxy) if config.telegram_proxy else None
    if session is not None:
        log.info("Telegram через прокси: %s", _mask_credentials(config.telegram_proxy))
    bot = Bot(
        config.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())  # FSM: багрепорт «опиши проблему»

    logging_mw = LoggingMiddleware()
    dp.message.outer_middleware(logging_mw)
    dp.callback_query.outer_middleware(logging_mw)

    dp.include_router(start.router)
    dp.include_router(group.router)
    dp.include_router(today.router)
    dp.include_router(week.router)
    dp.include_router(full_schedule.router)
    dp.include_router(zameny.router)
    dp.include_router(menu.router)
    dp.include_router(settings.router)
    dp.startup.register(_on_startup)
    dp.shutdown.register(_on_shutdown)
    dp.errors.register(_on_error)
    return bot, dp
