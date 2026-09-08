from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is not set in .env")
    return value


def _parse_time(raw: str | None, default: str) -> time:
    value = raw or default
    try:
        hh, mm = value.split(":")
        return time(int(hh), int(mm))
    except ValueError as err:
        raise RuntimeError(f"Ожидал время в формате ЧЧ:ММ, получил {value!r}") from err


def _parse_reminder(raw: str | None, default: str) -> str:
    """Нормализует REMINDER_DEFAULT: "off" или "HH:MM" (с ведущими нулями)."""
    value = (raw or default).strip().lower()
    if value == "off":
        return "off"
    t = _parse_time(value, default)
    return f"{t.hour:02d}:{t.minute:02d}"


@dataclass(frozen=True)
class Config:
    bot_token: str
    # Прокси для api.telegram.org, если сервер не видит Telegram напрямую.
    # http://host:port или socks5://user:pass@host:port (socks — нужен
    # пакет aiohttp-socks). Пусто = без прокси.
    telegram_proxy: str | None
    # chat_id владельца — туда бот шлёт багрепорты. Свой узнать: /id боту.
    owner_chat_id: int | None
    # Дефолтное время напоминания «пары на завтра» (HH:MM или "off").
    # Применяется к тем, кто не выбрал своё в онбординге/настройках.
    reminder_default: str
    # Обычный режим: COLLEGE_PAGE_URL парсится при каждом обновлении, чтобы
    # найти актуальные ссылки на файлы расписания/замен (они каждый раз
    # перезаливаются под новым именем).
    #
    # Режим разработки: SCHEDULE_SOURCE/ZAMENY_SOURCE (URL или путь к файлу,
    # например scratch_samples/raspisanie.xlsx) отключают парсинг страницы.
    college_page_url: str | None
    schedule_source: str | None
    zameny_source: str | None
    cache_ttl_minutes: int
    data_dir: str
    # Наблюдатель замен: первая проверка дня в notify_start, затем каждые
    # notify_interval_hours часов, пока не наступит полночь; ночью не тревожим.
    # По умолчанию 12:25 и раз в 3 часа (12:25, 15:25, 18:25, 21:25).
    notify_start: time
    notify_interval_hours: int

    @property
    def data_path(self) -> Path:
        return Path(self.data_dir)


def _load() -> Config:
    bot_token = _require("BOT_TOKEN")
    college_page_url = os.getenv("COLLEGE_PAGE_URL")
    schedule_source = os.getenv("SCHEDULE_SOURCE")
    zameny_source = os.getenv("ZAMENY_SOURCE")

    if not college_page_url and not (schedule_source and zameny_source):
        raise RuntimeError(
            "Set COLLEGE_PAGE_URL in .env, or SCHEDULE_SOURCE + ZAMENY_SOURCE for a direct override."
        )

    cache_ttl_minutes = int(os.getenv("CACHE_TTL_MINUTES") or 15)

    owner_raw = os.getenv("OWNER_CHAT_ID")
    try:
        owner_chat_id = int(owner_raw) if owner_raw else None
    except ValueError:
        raise RuntimeError(f"OWNER_CHAT_ID должно быть числом, а не {owner_raw!r}") from None

    return Config(
        bot_token=bot_token,
        telegram_proxy=os.getenv("TELEGRAM_PROXY") or None,
        owner_chat_id=owner_chat_id,
        reminder_default=_parse_reminder(os.getenv("REMINDER_DEFAULT"), "20:00"),
        college_page_url=college_page_url,
        schedule_source=schedule_source,
        zameny_source=zameny_source,
        cache_ttl_minutes=cache_ttl_minutes,
        data_dir=os.getenv("DATA_DIR") or "data",
        notify_start=_parse_time(os.getenv("NOTIFY_START_TIME"), "12:25"),
        notify_interval_hours=int(os.getenv("NOTIFY_INTERVAL_HOURS") or 3),
    )


config = _load()
