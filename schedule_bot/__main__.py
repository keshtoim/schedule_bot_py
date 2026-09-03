import asyncio
import logging

from .bot import create_bot


async def _run() -> None:
    bot, dp = create_bot()
    print("Bot started")
    await dp.start_polling(bot)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_run())


if __name__ == "__main__":
    main()
