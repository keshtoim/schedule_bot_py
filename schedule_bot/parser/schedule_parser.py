from __future__ import annotations

import re
from dataclasses import dataclass

from .workbook import Sheet


@dataclass
class SchedulePair:
    pair: str  # "0", "1", "2"... ("0" = внеурочный слот перед первой парой)
    time_start: str
    time_end: str
    by_group: dict[str, str]  # имя группы -> сырой текст пары (предмет/преподаватель/кабинет)


@dataclass
class ScheduleDay:
    weekday: str
    pairs: list[SchedulePair]


@dataclass
class Schedule:
    groups: list[str]
    days: list[ScheduleDay]


_DAYS_HEADER_RE = re.compile(r"^дни недели$", re.IGNORECASE)
_MERGE_RE = re.compile(r"^([A-Z]+)(\d+):([A-Z]+)(\d+)$")
_TIME_RE = re.compile(r"\d{1,2}\.\d{2}")


def _find_header_row(sheet: Sheet) -> int:
    for r in range(1, sheet.max_row + 1):
        if _DAYS_HEADER_RE.match(sheet.text(r, 1)):
            return r
    raise ValueError('Header row ("дни недели") not found')


def _find_group_columns(sheet: Sheet, header_row: int) -> list[tuple[int, str]]:
    groups: list[tuple[int, str]] = []
    for c in range(4, sheet.max_column + 1):
        name = sheet.text(header_row, c)
        if not name:
            break
        groups.append((c, name))
    return groups


def _find_day_blocks(sheet: Sheet, header_row: int) -> list[tuple[int, int, str]]:
    """Вертикальные объединения только в колонке A ниже заголовка = блоки дней."""
    blocks: list[tuple[int, int, str]] = []
    for ref in sheet.merges:
        m = _MERGE_RE.match(ref)
        if not m:
            continue
        col_start, row_start, col_end, row_end = m.groups()
        if col_start != "A" or col_end != "A":
            continue
        start = int(row_start)
        if start <= header_row:
            continue
        name = sheet.text(start, 1)
        if not name:
            continue
        blocks.append((start, int(row_end), name))

    blocks.sort(key=lambda b: b[0])
    return blocks


def parse_schedule(sheet: Sheet) -> Schedule:
    header_row = _find_header_row(sheet)
    group_cols = _find_group_columns(sheet, header_row)
    day_blocks = _find_day_blocks(sheet, header_row)

    days: list[ScheduleDay] = []

    # Строки между заголовком и первым блоком дня (например отдельная строка
    # "пара 0") относятся к первому дню.
    lead_in_start = header_row + 1
    lead_in_end = day_blocks[0][0] - 1 if day_blocks else header_row
    first_name = day_blocks[0][2] if day_blocks else ""
    all_blocks = [(lead_in_start, lead_in_end, first_name), *day_blocks]

    for start, end, name in all_blocks:
        if end < start:
            continue
        pairs: list[SchedulePair] = []

        for r in range(start, end + 1, 2):
            pair_num = sheet.text(r, 2)
            if not pair_num:
                continue

            # Пробелы вокруг "-" в файле непостоянны ("10.50 -11.35"), поэтому
            # вытаскиваем токены H.MM напрямую, а не делим по " - ".
            start_times = _TIME_RE.findall(sheet.text(r, 3))
            end_times = _TIME_RE.findall(sheet.text(r + 1, 3))
            time_start = start_times[0] if start_times else ""
            time_end = end_times[-1] if end_times else (start_times[-1] if start_times else "")

            by_group = {name: sheet.text(r, col) for col, name in group_cols}
            pairs.append(SchedulePair(pair=pair_num, time_start=time_start, time_end=time_end, by_group=by_group))

        if not pairs:
            continue

        existing = next((d for d in days if d.weekday == name), None)
        if existing:
            existing.pairs.extend(pairs)
        else:
            days.append(ScheduleDay(weekday=name, pairs=pairs))

    return Schedule(groups=[name for _, name in group_cols], days=days)
