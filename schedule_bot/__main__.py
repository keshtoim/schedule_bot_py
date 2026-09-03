import asyncio
import logging

from .bot import create_bot
from .utils.describe_error import describe_error

_RETRY_DELAY_SEC = 10


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
            print("Bot started")
            await dp.start_polling(bot)
            return
        except Exception as err:  # noqa: BLE001
            logging.error("Не удалось запустить бота (попытка %d): %s", attempt, describe_error(err))
            logging.error("Повтор через %d сек...", _RETRY_DELAY_SEC)
            await asyncio.sleep(_RETRY_DELAY_SEC)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_run())


if __name__ == "__main__":
    main()
