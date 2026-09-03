from __future__ import annotations

import asyncio
import re
from datetime import date

from ..parser.schedule_parser import ScheduleDay, resolve_pair_content
from ..parser.zameny_parser import ZamenyBlock
from ..utils.weekday import (
    add_days,
    format_ddmmyyyy,
    is_numerator_week,
    monday_of_week,
    weekday_name,
)
from .schedule_service import get_schedule, get_zameny


def _esc(text: str) -> str:
    # Rich-разметка понимает лишь небольшой набор именованных сущностей —
    # &, <, > покрывают всё, что нужно нашему тексту.
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


_TEACHER_WORD_RE = re.compile(r"^[А-ЯЁ][а-яё]{2,}$")


def _split_lesson_text(raw: str) -> tuple[str, str]:
    """Эвристика: делим сырой текст "Предмет Преподаватель [...] кабинет" на
    предмет и строку "преподаватель, ауд. кабинет" для двух колонок таблицы.
    Разделителей в источнике нет: слово с заглавной буквы (Токарев) — фамилия,
    аббревиатура капсом (БЖ, ПОПД) или фраза строчными — часть предмета.
    Если не разобрать — всё уходит в колонку предмета."""
    if re.search(r'["«]', raw):
        return raw, "—"

    tokens = raw.split()
    teacher_start = next((i for i, t in enumerate(tokens) if _TEACHER_WORD_RE.match(t)), -1)
    if teacher_start <= 0:
        return raw, "—"

    subject = " ".join(tokens[:teacher_start])
    rest = tokens[teacher_start:]

    teacher_end = 0
    while teacher_end < len(rest) and _TEACHER_WORD_RE.match(rest[teacher_end]):
        teacher_end += 1

    teachers = ", ".join(rest[:teacher_end])
    location = " ".join(rest[teacher_end:]).replace(",", ", ")
    if location:
        prefix = "ауд. " if location[:1].isdigit() else ""
        teacher = f"{teachers}, {prefix}{location}"
    else:
        teacher = teachers

    return subject, teacher


def _pair_row_html(
    pair, group: str, numerator_week: bool, zameny_block: ZamenyBlock | None
) -> str | None:
    text = resolve_pair_content(pair.by_group.get(group), numerator_week)
    if not text:
        return None

    z_row = None
    if zameny_block:
        z_row = next(
            (r for r in zameny_block.rows if r.pair_number == pair.pair and r.group == group), None
        )

    if z_row and z_row.replacement.strip().lower() == "нет":
        subject = "❌ Отменено"
        teacher = f"было: {z_row.instead_of}"
    elif z_row:
        subject = f"🔁 {z_row.replacement}"
        teacher = z_row.room or "—"
    else:
        subject, teacher = _split_lesson_text(text)

    return (
        f"<tr><td>{_esc(pair.pair)}</td><td>{_esc(pair.time_start)}–{_esc(pair.time_end)}</td>"
        f"<td>{_esc(subject)}</td><td>{_esc(teacher)}</td></tr>"
    )


def _day_table_html(
    day: ScheduleDay | None, group: str, numerator_week: bool, zameny_block: ZamenyBlock | None
) -> str:
    if day is None:
        return "<p><i>Занятий нет (выходной по расписанию).</i></p>"

    rows = [
        row
        for row in (_pair_row_html(p, group, numerator_week, zameny_block) for p in day.pairs)
        if row is not None
    ]
    if not rows:
        return "<p><i>Занятий нет.</i></p>"

    return (
        "<table bordered striped>"
        "<tr><th>№ пары</th><th>Время</th><th>Предмет</th><th>Преподаватель / Аудитория</th></tr>"
        + "".join(rows)
        + "</table>"
    )


async def build_day_html(group: str, day_date: date) -> str:
    """Один день как rich-HTML: заголовок <h3> с датой плюс таблица занятий."""
    weekday = weekday_name(day_date)
    date_str = format_ddmmyyyy(day_date)
    schedule, zameny = await asyncio.gather(get_schedule(), get_zameny())

    day = next((d for d in schedule.days if d.weekday == weekday), None)
    zameny_block = next((z for z in zameny if z.date == date_str), None)
    numerator_week = is_numerator_week(day_date)
    parity_label = "числитель" if numerator_week else "знаменатель"

    return f"<h3>{weekday}, {date_str} ({parity_label})</h3>" + _day_table_html(
        day, group, numerator_week, zameny_block
    )


async def build_week_html(group: str, around: date | None = None) -> str:
    """Понедельник–суббота недели, содержащей `around` (по умолчанию сегодня)."""
    monday = monday_of_week(around or date.today())
    numerator_week = is_numerator_week(monday)
    parity_label = "числитель" if numerator_week else "знаменатель"
    schedule, zameny = await asyncio.gather(get_schedule(), get_zameny())

    parts = [f"<h3>🗓️ Расписание ({parity_label})</h3>"]

    for i in range(6):
        d = add_days(monday, i)
        weekday = weekday_name(d)
        date_str = format_ddmmyyyy(d)
        day = next((x for x in schedule.days if x.weekday == weekday), None)
        zameny_block = next((z for z in zameny if z.date == date_str), None)

        parts.append(f"<h4>{weekday}, {date_str}</h4>")
        parts.append(_day_table_html(day, group, numerator_week, zameny_block))

    return "".join(parts)
