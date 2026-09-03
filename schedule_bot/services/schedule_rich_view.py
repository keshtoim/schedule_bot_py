from __future__ import annotations

import asyncio
from datetime import date

from ..parser.schedule_parser import resolve_pair_content
from ..parser.zameny_parser import ZamenyRow
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


def _zameny_note_html(row: ZamenyRow) -> str:
    if row.replacement.strip().lower() == "нет":
        return f"<p>❌ <i>Отменено (было: {_esc(row.instead_of)})</i></p>"
    room = f" {_esc(row.room)}" if row.room else ""
    return f"<p>🔁 <i>Вместо «{_esc(row.instead_of)}» — «{_esc(row.replacement)}»{room}</i></p>"


async def build_day_html(group: str, day_date: date) -> str:
    """Один день как rich-HTML: заголовок <h3> с датой плюс <p> на каждую пару."""
    weekday = weekday_name(day_date)
    date_str = format_ddmmyyyy(day_date)
    schedule, zameny = await asyncio.gather(get_schedule(), get_zameny())

    day = next((d for d in schedule.days if d.weekday == weekday), None)
    zameny_block = next((z for z in zameny if z.date == date_str), None)
    numerator_week = is_numerator_week(day_date)
    parity_label = "числитель" if numerator_week else "знаменатель"

    parts = [f"<h3>{weekday}, {date_str} ({parity_label})</h3>"]

    if day is None:
        parts.append("<p><i>Занятий нет (выходной по расписанию).</i></p>")
        return "".join(parts)

    has_lessons = False
    for pair in day.pairs:
        text = resolve_pair_content(pair.by_group.get(group), numerator_week)
        if not text:
            continue
        has_lessons = True

        parts.append(f"<p><b>Пара {pair.pair} ({pair.time_start}–{pair.time_end}):</b> {_esc(text)}</p>")
        z_row = None
        if zameny_block:
            z_row = next(
                (r for r in zameny_block.rows if r.pair_number == pair.pair and r.group == group), None
            )
        if z_row:
            parts.append(_zameny_note_html(z_row))

    if not has_lessons:
        parts.append("<p><i>Занятий нет.</i></p>")
    return "".join(parts)


async def build_week_html(group: str, around: date | None = None) -> str:
    """Понедельник–суббота недели, содержащей `around` (по умолчанию сегодня)."""
    monday = monday_of_week(around or date.today())
    parts: list[str] = []
    for i in range(6):
        if i > 0:
            parts.append("<hr/>")
        parts.append(await build_day_html(group, add_days(monday, i)))
    return "".join(parts)
