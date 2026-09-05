from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

# Расписание и замены колледжа — по московскому времени. Весь бот считает
# «сегодня», «завтра», чётность недели и расписание проверок замен по МСК,
# независимо от часового пояса сервера.
MSK = ZoneInfo("Europe/Moscow")


def now() -> datetime:
    """Текущий момент по Москве (timezone-aware)."""
    return datetime.now(MSK)


def today() -> date:
    """Сегодняшняя дата по Москве."""
    return now().date()
