from __future__ import annotations

import asyncio
import re
from datetime import date

from ..parser.schedule_parser import ScheduleDay, pair_sort_key, resolve_pair_content
from ..parser.zameny_parser import ZamenyBlock, ZamenyRow
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


def _added_pair_row_html(row: ZamenyRow, grid_pair) -> str:
    """Пара, которой нет в расписании группы, но её добавили заменой."""
    time = f"{_esc(grid_pair.time_start)}–{_esc(grid_pair.time_end)}" if grid_pair else "—"
    return (
        f"<tr><td>{_esc(row.pair_number)}</td><td>{time}</td>"
        f"<td>➕ {_esc(row.replacement)}</td><td>{_esc(row.room or '—')}</td></tr>"
    )


def _day_table_html(
    day: ScheduleDay | None, group: str, numerator_week: bool, zameny_block: ZamenyBlock | None
) -> str:
    if day is None:
        return "<p><i>Занятий нет (выходной по расписанию).</i></p>"

    rows: list[tuple[int, str]] = []
    scheduled: set[str] = set()
    for p in day.pairs:
        html = _pair_row_html(p, group, numerator_week, zameny_block)
        if html is None:
            continue
        scheduled.add(p.pair)
        rows.append((pair_sort_key(p.pair), html))

    # Замены, добавляющие пару туда, где у группы по расписанию пусто.
    if zameny_block:
        grid_by_num = {p.pair: p for p in day.pairs}
        for r in zameny_block.rows:
            if r.group != group or r.pair_number in scheduled:
                continue
            if r.replacement.strip().lower() == "нет":
                continue  # отмена несуществующей пары — показывать нечего
            rows.append(
                (pair_sort_key(r.pair_number), _added_pair_row_html(r, grid_by_num.get(r.pair_number)))
            )

    if not rows:
        return "<p><i>Занятий нет.</i></p>"

    rows.sort(key=lambda t: t[0])
    return (
        "<table bordered striped>"
        "<tr><th>№ пары</th><th>Время</th><th>Предмет</th><th>Преподаватель / Аудитория</th></tr>"
        + "".join(html for _, html in rows)
        + "</table>"
    )


def _pair_rows_general_html(pair, group: str) -> str:
    """Как _pair_row_html, но без привязки к дате и заменам: у чередующейся
    пары две строки (Ч/З), делящие ячейку №/Время через rowspan."""
    content = pair.by_group.get(group)
    if not content:
        return ""

    num_cell = f"<td>{_esc(pair.pair)}</td><td>{_esc(pair.time_start)}–{_esc(pair.time_end)}</td>"

    if isinstance(content, str):
        subject, teacher = _split_lesson_text(content)
        return f"<tr>{num_cell}<td>{_esc(subject)}</td><td>{_esc(teacher)}</td></tr>"

    num = _split_lesson_text(content.numerator)
    den = _split_lesson_text(content.denominator)
    span_cell = (
        f'<td rowspan="2">{_esc(pair.pair)}</td>'
        f'<td rowspan="2">{_esc(pair.time_start)}–{_esc(pair.time_end)}</td>'
    )
    return (
        f"<tr>{span_cell}<td>Ч: {_esc(num[0])}</td><td>{_esc(num[1])}</td></tr>"
        f"<tr><td>З: {_esc(den[0])}</td><td>{_esc(den[1])}</td></tr>"
    )


def _day_table_general_html(day: ScheduleDay | None, group: str) -> str:
    if day is None:
        return "<p><i>Занятий нет (выходной по расписанию).</i></p>"

    rows = [r for r in (_pair_rows_general_html(p, group) for p in day.pairs) if r]
    if not rows:
        return "<p><i>Занятий нет.</i></p>"

    return (
        "<table bordered striped>"
        "<tr><th>№ пары</th><th>Время</th><th>Предмет</th><th>Преподаватель / Аудитория</th></tr>"
        + "".join(rows)
        + "</table>"
    )


async def build_full_schedule_html(group: str) -> str:
    """Полный недельный шаблон без привязки к дате: чередующаяся пара
    показывает оба варианта (Ч и З). Замен тоже нет — они привязаны к датам."""
    schedule = await get_schedule()
    parts = ["<h3>📋 Общее расписание</h3><p><i>Ч — числитель, З — знаменатель</i></p>"]

    for day in schedule.days:
        parts.append(f"<h4>{day.weekday}</h4>")
        parts.append(_day_table_general_html(day, group))

    return "".join(parts)


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
