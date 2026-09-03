import asyncio
import logging

from .bot import create_bot
from .logging_setup import setup_logging
from .utils.describe_error import describe_error

_RETRY_DELAY_SEC = 10

log = logging.getLogger("schedule_bot")


async def _run() -> None:
    bot, dp = create_bot()

    # start_polling сначала дёргает get_me() — если Telegram недоступен (эта
    # сеть периодически рвёт соединение до api.telegram.org), это падало
    # необработанным исключением и убивало весь процесс, а не одну команду.
    # Теперь запуск повторяется с понятным сообщением о причине.
    attempt = 0
    while True:
        attempt += 1
        try:
            log.info("Запускаю поллинг (попытка %d)…", attempt)
            await dp.start_polling(bot)
            return
        except Exception as err:  # noqa: BLE001
            log.error("Не удалось запустить бота (попытка %d): %s", attempt, describe_error(err))
            log.error("Повтор через %d с…", _RETRY_DELAY_SEC)
            await asyncio.sleep(_RETRY_DELAY_SEC)


def main() -> None:
    setup_logging()
    log.info("=== schedule_bot запускается ===")
    try:
        asyncio.run(_run())
    except (KeyboardInterrupt, SystemExit):
        log.info("Остановлен вручную")


if __name__ == "__main__":
    main()
