from __future__ import annotations

import re
from dataclasses import dataclass

from .workbook import Sheet


@dataclass
class ZamenyRow:
    group: str
    pair: str  # сырой текст, например "2пара"
    pair_number: str  # только цифры, например "2"
    instead_of: str
    replacement: str
    room: str


@dataclass
class ZamenyBlock:
    weekday: str  # именительный падеж, например "Среда"
    date: str  # dd.mm.yyyy
    rows: list[ZamenyRow]


# Заголовок — "Изменение в расписании занятий на <день> <dd.mm.yyyy>г.",
# иногда с хвостом: с 2026-27 уч. года там суффикс чётности, например
# "...04.09.2026г. (числитель)". Матчим день + дату, хвост игнорируем; заодно
# терпим множественное "Изменения".
_HEADER_RE = re.compile(
    r"Изменени[ея] в расписании занятий на\s+(\S+)\s+(\d{2}\.\d{2}\.\d{4})",
    re.IGNORECASE,
)
_COLUMN_HEADER_RE = re.compile(r"^ГРУППА$", re.IGNORECASE)
# У настоящей строки замены всегда есть номер пары; строки подвала/подписи
# (например объединённая пометка "Учебная часть") повторяют один текст во
# всех колонках и цифры здесь не имеют — так они и отсеиваются.
_PAIR_RE = re.compile(r"\d")
_DIGITS_RE = re.compile(r"\d+")

# Заголовки замен в винительном падеже ("на вторник", "на среду"); сетка
# расписания — в именительном, поэтому нормализуем для сопоставления.
_WEEKDAY_NOMINATIVE = {
    "понедельник": "Понедельник",
    "вторник": "Вторник",
    "среду": "Среда",
    "четверг": "Четверг",
    "пятницу": "Пятница",
    "субботу": "Суббота",
    "воскресенье": "Воскресенье",
}


def _normalize_weekday(raw: str) -> str:
    return _WEEKDAY_NOMINATIVE.get(raw.lower(), raw)


def parse_zameny(sheet: Sheet) -> list[ZamenyBlock]:
    blocks: list[ZamenyBlock] = []
    current: ZamenyBlock | None = None
    # Когда у группы замены на нескольких парах, имя группы стоит только в
    # первой строке (колонка A), остальные пустые (не объединены). Протягиваем
    # последнее имя вниз до следующего имени / пустой строки-разделителя / нового блока.
    group = ""

    for r in range(1, sheet.max_row + 1):
        col_a = sheet.text(r, 1)

        header = _HEADER_RE.search(col_a)
        if header:
            current = ZamenyBlock(weekday=_normalize_weekday(header.group(1)), date=header.group(2), rows=[])
            blocks.append(current)
            group = ""
            continue

        if current is None:
            continue  # всё до первого заголовка с датой

        if _COLUMN_HEADER_RE.match(col_a):
            group = ""
            continue  # строка "ГРУППА | ПАРА | ВМЕСТО | ЗАМЕНА | кабинет"

        pair = sheet.text(r, 2)
        instead_of = sheet.text(r, 3)
        replacement = sheet.text(r, 4)
        room = sheet.text(r, 5)

        # Полностью пустая строка разделяет группы (например перед подвалом) —
        # сбрасываем, чтобы поздняя случайная строка не унаследовала имя.
        if not col_a and not pair and not instead_of and not replacement and not room:
            group = ""
            continue

        if col_a:
            group = col_a

        if not group or not _PAIR_RE.search(pair):
            continue  # строка-шаблон или подвал/подпись

        current.rows.append(
            ZamenyRow(
                group=group,
                pair=pair,
                pair_number=_DIGITS_RE.search(pair).group(0),
                instead_of=instead_of,
                replacement=replacement,
                room=room,
            )
        )

    return blocks
