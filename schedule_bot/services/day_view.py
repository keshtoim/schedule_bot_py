from __future__ import annotations

import asyncio
from datetime import date

from ..parser.schedule_parser import pair_sort_key, resolve_pair_content
from ..parser.zameny_parser import ZamenyBlock, ZamenyRow
from ..utils.html import escape_html
from ..utils.weekday import (
    add_days,
    format_ddmmyyyy,
    is_numerator_week,
    monday_of_week,
    today,
    weekday_name,
)
from .schedule_service import get_schedule, get_zameny


def _format_zameny_note(row: ZamenyRow) -> str:
    if row.replacement.strip().lower() == "нет":
        return f"   ❌ <i>Отменено (было: {escape_html(row.instead_of)})</i>"
    room = f" {escape_html(row.room)}" if row.room else ""
    return f"   🔁 <i>Вместо «{escape_html(row.instead_of)}» — «{escape_html(row.replacement)}»{room}</i>"


def day_lesson_lines(day, group: str, numerator_week: bool, zameny_block: ZamenyBlock | None) -> list[str]:
    """Строки занятий одного дня (без заголовка) для plain-HTML сообщения.
    Отдельные пары расписания с наложенными заменами плюс пары, которые
    замена добавила туда, где у группы по расписанию пусто."""
    entries: list[tuple[int, str]] = []
    scheduled: set[str] = set()
    for pair in day.pairs:
        text = resolve_pair_content(pair.by_group.get(group), numerator_week)
        if not text:
            continue
        scheduled.add(pair.pair)

        line = f"<b>Пара {pair.pair} ({pair.time_start}–{pair.time_end}):</b> {escape_html(text)}"
        z_row = None
        if zameny_block:
            z_row = next(
                (r for r in zameny_block.rows if r.pair_number == pair.pair and r.group == group), None
            )
        if z_row:
            line += f"\n{_format_zameny_note(z_row)}"

        entries.append((pair_sort_key(pair.pair), line))

    # Замены, добавляющие пару туда, где у группы по расписанию пусто.
    if zameny_block:
        grid_by_num = {p.pair: p for p in day.pairs}
        for r in zameny_block.rows:
            if r.group != group or r.pair_number in scheduled:
                continue
            if r.replacement.strip().lower() == "нет":
                continue
            grid_pair = grid_by_num.get(r.pair_number)
            when = f" ({grid_pair.time_start}–{grid_pair.time_end})" if grid_pair else ""
            room = f" {escape_html(r.room)}" if r.room else ""
            entries.append(
                (
                    pair_sort_key(r.pair_number),
                    f"<b>Пара {r.pair_number}{when}:</b> ➕ <i>{escape_html(r.replacement)}{room}</i>",
                )
            )

    entries.sort(key=lambda t: t[0])
    return [line for _, line in entries]


async def format_day(group: str, day_date: date) -> str:
    """Запасной вариант на случай сбоя sendRichMessage (schedule_rich_view):
    обычный текст в разметке Telegram parse_mode="HTML"."""
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

    lesson_lines = day_lesson_lines(day, group, numerator_week, zameny_block)
    lines.extend(lesson_lines or ["<i>Занятий нет.</i>"])
    return "\n".join(lines)


async def format_week(group: str, around: date | None = None) -> str:
    """Понедельник–суббота недели, содержащей `around` (по умолчанию сегодня)."""
    monday = monday_of_week(around or today())
    days = await asyncio.gather(*(format_day(group, add_days(monday, i)) for i in range(6)))
    return "\n\n".join(days)


async def format_full_schedule(group: str) -> str:
    """Полный недельный шаблон без привязки к дате — у чередующейся пары
    показываются оба варианта (Ч и З), а не тот, что действует на этой неделе."""
    schedule = await get_schedule()
    lines = ["<b>📋 Общее расписание</b>", "<i>Ч — числитель, З — знаменатель</i>"]

    for day in schedule.days:
        lines.append(f"<b>{day.weekday}:</b>")
        has_lessons = False

        for pair in day.pairs:
            content = pair.by_group.get(group)
            if not content:
                continue
            has_lessons = True

            label = f"<b>Пара {pair.pair} ({pair.time_start}–{pair.time_end}):</b>"
            if isinstance(content, str):
                lines.append(f"{label} {escape_html(content)}")
            else:
                lines.append(label)
                lines.append(f"   Ч: {escape_html(content.numerator)}")
                lines.append(f"   З: {escape_html(content.denominator)}")

        if not has_lessons:
            lines.append("<i>Занятий нет.</i>")

    return "\n".join(lines)
