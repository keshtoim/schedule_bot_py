from __future__ import annotations

from datetime import date, timedelta

# date.weekday(): 0 = понедельник ... 6 = воскресенье
_WEEKDAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


def weekday_name(d: date) -> str:
    return _WEEKDAYS[d.weekday()]


def today() -> date:
    return date.today()


def tomorrow() -> date:
    return date.today() + timedelta(days=1)


def add_days(d: date, n: int) -> date:
    return d + timedelta(days=n)


def monday_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())


def format_ddmmyyyy(d: date) -> str:
    return d.strftime("%d.%m.%Y")
