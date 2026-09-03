from __future__ import annotations

import logging
import os

# Время, уровень, короткое имя модуля, сообщение. Дата без года — лог читают
# по горячим следам, а не через месяц.
_FORMAT = "%(asctime)s %(levelname)-7s %(name)-24s %(message)s"
_DATEFMT = "%d.%m %H:%M:%S"

# Библиотеки, которые иначе засыпают консоль на каждый запрос.
_NOISY = ("httpx", "httpcore", "aiogram.event", "asyncio")


class _ShortName(logging.Filter):
    """schedule_bot.services.file_source -> services.file_source."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name == "schedule_bot":
            record.name = "bot"
        elif record.name.startswith("schedule_bot."):
            record.name = record.name[len("schedule_bot.") :]
        return True


def setup_logging(level: str | None = None) -> None:
    """Единый вывод логов в консоль. Уровень — из аргумента, иначе из
    переменной LOG_LEVEL, иначе INFO (DEBUG — чтобы видеть попадания в кеш и
    прочие мелочи)."""
    lvl = (level or os.getenv("LOG_LEVEL") or "INFO").upper()

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATEFMT))
    handler.addFilter(_ShortName())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(lvl)

    for name in _NOISY:
        logging.getLogger(name).setLevel(logging.WARNING)

    logging.getLogger("schedule_bot").info("Логирование настроено, уровень %s", lvl)
