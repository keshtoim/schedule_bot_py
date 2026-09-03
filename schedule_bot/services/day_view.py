from __future__ import annotations

import asyncio
from datetime import date

from ..parser.schedule_parser import resolve_pair_content
from ..parser.zameny_parser import ZamenyRow
from ..utils.html import escape_html
from ..utils.weekday import (
    add_days,
    format_ddmmyyyy,
    is_numerator_week,
    monday_of_week,
    weekday_name,
)
from .schedule_service import get_schedule, get_zameny


def _format_zameny_note(row: ZamenyRow) -> str:
    if row.replacement.strip().lower() == "нет":
        return f"   ❌ <i>Отменено (было: {escape_html(row.instead_of)})</i>"
    room = f" {escape_html(row.room)}" if row.room else ""
    return f"   🔁 <i>Вместо «{escape_html(row.instead_of)}» — «{escape_html(row.replacement)}»{room}</i>"


async def format_day(group: str, day_date: date) -> str:
    """Результат — текст в разметке Telegram parse_mode="HTML"."""
    weekday = weekday_name(day_date)
    date_str = format_ddmmyyyy(day_date)
    schedule, zameny = await asyncio.gather(get_schedule(), get_zameny())

    day = next((d for d in schedule.days if d.weekday == weekday), None)
    zameny_block = next((z for z in zameny if z.date == date_str), None)
    numerator_week = is_numerator_week(day_date)
    parity_label = "числитель" if numerator_week else "знаменатель"

    lines = [f"<b>{weekday}, {date_str} ({parity_label}):</b>"]

    if day is None:
        lines.append("<i>Занятий нет (выходной по расписанию).</i>")
        return "\n".join(lines)

    has_lessons = False
    for pair in day.pairs:
        text = resolve_pair_content(pair.by_group.get(group), numerator_week)
        if not text:
            continue
        has_lessons = True

        line = f"<b>Пара {pair.pair} ({pair.time_start}–{pair.time_end}):</b> {escape_html(text)}"
        z_row = None
        if zameny_block:
            z_row = next(
                (r for r in zameny_block.rows if r.pair_number == pair.pair and r.group == group), None
            )
        if z_row:
            line += f"\n{_format_zameny_note(z_row)}"

        lines.append(line)

    if not has_lessons:
        lines.append("<i>Занятий нет.</i>")
    return "\n".join(lines)


async def format_week(group: str, around: date | None = None) -> str:
    """Понедельник–суббота недели, содержащей `around` (по умолчанию сегодня)."""
    monday = monday_of_week(around or date.today())
    days = await asyncio.gather(*(format_day(group, add_days(monday, i)) for i in range(6)))
    return "\n\n".join(days)
