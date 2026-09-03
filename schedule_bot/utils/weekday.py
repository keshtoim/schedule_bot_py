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


# Неделя, начинающаяся в понедельник 31.08.2026, — «числитель» (уточнено у
# колледжа на 2026-27 учебный год). Чётность чередуется понедельно в обе стороны.
_NUMERATOR_ANCHOR_MONDAY = date(2026, 8, 31)


def is_numerator_week(d: date) -> bool:
    monday = monday_of_week(d)
    anchor = monday_of_week(_NUMERATOR_ANCHOR_MONDAY)
    diff_weeks = round((monday - anchor).days / 7)
    return diff_weeks % 2 == 0
