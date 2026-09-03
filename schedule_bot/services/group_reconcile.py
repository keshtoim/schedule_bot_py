from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from ..parser.schedule_parser import AlternatingPair, Schedule
from ..parser.zameny_parser import ZamenyBlock, ZamenyRow

# Названия групп в файле замен вбивают вручную, поэтому они иногда не совпадают
# с каноническим списком из расписания:
#  - латинская буква вместо кириллического двойника ("23-ИCП-1" с латинской C),
#    лишний пробел, другой дефис — косметика, безопасно считать той же группой;
#  - настоящая опечатка в верном в остальном имени ("23-ИСП-2" там, где замена
#    на самом деле для "23-ИСП-1") — доверяем только когда заменяемая пара
#    ("вместо ...") реально есть в расписании группы-кандидата на этой паре и
#    её НЕТ у указанной группы.

AnomalyKind = Literal["homoglyph", "typo"]


@dataclass
class ZamenyAnomaly:
    kind: AnomalyKind
    stated_group: str  # ровно как записано в файле замен
    likely_group: str  # каноническая группа, к которой это скорее всего относится
    date: str  # dd.mm.yyyy
    weekday: str
    rows: list[ZamenyRow]  # строки замен, записанные под stated_group на эту дату
    evidence: list[str] = field(default_factory=list)  # человекочитаемое «почему так думаем»


_HOMOGLYPHS = {
    # заглавная латиница -> кириллический двойник
    "A": "А", "B": "В", "C": "С", "E": "Е", "H": "Н", "K": "К", "M": "М", "O": "О",
    "P": "Р", "T": "Т", "X": "Х", "Y": "У",
    # строчная латиница -> кириллический двойник
    "a": "а", "c": "с", "e": "е", "h": "н", "k": "к", "m": "м", "o": "о", "p": "р",
    "t": "т", "x": "х", "y": "у",
}

_ZERO_WIDTH_RE = re.compile("[­​-‍﻿]")  # мягкий перенос, zero-width
_DASH_RE = re.compile("[‐-―−]")  # дефис..горизонтальная черта, минус


def normalize_group(raw: str) -> str:
    """Сводит косметические различия: латинские двойники -> кириллица, любой
    вариант тире -> "-", все пробелы / zero-width удаляются. Две строки с
    одинаковой нормальной формой — одна и та же группа."""
    s = "".join(_HOMOGLYPHS.get(ch, ch) for ch in raw).lower()
    s = _ZERO_WIDTH_RE.sub("", s)
    s = re.sub(r"\s+", "", s)
    s = _DASH_RE.sub("-", s)
    s = re.sub(r"-+", "-", s)
    return s


def edit_distance(a: str, b: str) -> int:
    """Обычное расстояние Левенштейна."""
    m, n = len(a), len(b)
    if m == 0:
        return n
    if n == 0:
        return m

    prev = list(range(n + 1))
    curr = [0] * (n + 1)
    for i in range(1, m + 1):
        curr[0] = i
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev, curr = curr, prev
    return prev[n]


def _normalize_subject(raw: str) -> list[str]:
    cleaned = re.sub(r"[^a-zа-я0-9]+", " ", raw.lower().replace("ё", "е"))
    return [t for t in cleaned.split() if len(t) >= 4]


def _tokens_match(x: str, y: str) -> bool:
    if x == y:
        return True
    # Файл замен сокращает ("тех.оборуд." против "оборудование"), поэтому
    # общий префикс из 4+ символов считаем совпадением.
    shorter, longer = (x, y) if len(x) <= len(y) else (y, x)
    return len(shorter) >= 4 and longer.startswith(shorter)


def lessons_look_same(instead_of: str, schedule_text: str) -> bool:
    """True, если текст заменяемой пары ("вместо ...") похоже указывает на тот
    же урок, что и schedule_text. Осторожно: нужно либо одно весомое общее
    слово (5+ символов — фамилия или основа предмета), либо два покороче, чтобы
    одно общее слово вроде "пара" не считалось."""
    if not instead_of.strip() or not schedule_text.strip():
        return False
    a = _normalize_subject(instead_of)
    b = _normalize_subject(schedule_text)

    matches = 0
    strong_match = False
    for x in a:
        for y in b:
            if _tokens_match(x, y):
                matches += 1
                if min(len(x), len(y)) >= 5:
                    strong_match = True
                break
    return strong_match or matches >= 2


def _lesson_at(schedule: Schedule, group: str, weekday: str, pair_number: str) -> str:
    """Урок(и) группы на этот день недели и пару; оба варианта чётности, если
    пара чередуется — чтобы сопоставление не зависело от недели замены."""
    day = next((d for d in schedule.days if d.weekday == weekday), None)
    pair = next((p for p in day.pairs if p.pair == pair_number), None) if day else None
    content = pair.by_group.get(group) if pair else None
    if content is None:
        return ""
    if isinstance(content, AlternatingPair):
        return f"{content.numerator} {content.denominator}"
    return content


@dataclass
class _Resolution:
    kind: AnomalyKind
    group: str
    evidence: list[str]


def find_zameny_anomalies(schedule: Schedule, zameny: list[ZamenyBlock]) -> list[ZamenyAnomaly]:
    """Все строки замен сверяются с расписанием, чтобы поймать ошибки в имени группы."""
    known = schedule.groups
    known_set = set(known)
    by_normalized: dict[str, list[str]] = {}
    for g in known:
        by_normalized.setdefault(normalize_group(g), []).append(g)

    anomalies: list[ZamenyAnomaly] = []

    for block in zameny:
        rows_by_group: dict[str, list[ZamenyRow]] = {}
        for row in block.rows:
            rows_by_group.setdefault(row.group, []).append(row)

        for stated_group, rows in rows_by_group.items():
            resolved = _resolve_group(stated_group, rows, block, schedule, known, known_set, by_normalized)
            if resolved is None:
                continue

            anomalies.append(
                ZamenyAnomaly(
                    kind=resolved.kind,
                    stated_group=stated_group,
                    likely_group=resolved.group,
                    date=block.date,
                    weekday=block.weekday,
                    rows=rows,
                    evidence=resolved.evidence,
                )
            )

    return anomalies


def _resolve_group(
    stated_group: str,
    rows: list[ZamenyRow],
    block: ZamenyBlock,
    schedule: Schedule,
    known: list[str],
    known_set: set[str],
    by_normalized: dict[str, list[str]],
) -> _Resolution | None:
    stated_norm = normalize_group(stated_group)

    # Только косметическое различие (двойник / тире / пробел) — принимаем без
    # проверки расписания, если оно ведёт ровно к одной группе.
    if stated_group not in known_set:
        exact = by_normalized.get(stated_norm, [])
        if len(exact) == 1:
            return _Resolution("homoglyph", exact[0], ["различие только в написании названия группы"])
        if len(exact) > 1:
            return None  # неоднозначно

    # Если указанная группа реальна и её расписание подтверждает каждую
    # замену — всё в порядке.
    if stated_group in known_set:
        all_backed = all(
            not r.instead_of.strip()
            or lessons_look_same(r.instead_of, _lesson_at(schedule, stated_group, block.weekday, r.pair_number))
            for r in rows
        )
        if all_backed:
            return None

    # Настоящая опечатка: близкая реальная группа, чьё расписание объясняет
    # *каждую* проверяемую замену блока, а расписание указанной группы — ни
    # одной. Требование всего блока (а не одной строки) не даёт принять
    # единичную легитимную межгрупповую / добавленную пару за ошибку в имени.
    candidates: list[tuple[str, list[str]]] = []
    for g in known:
        if g == stated_group:
            continue
        if edit_distance(stated_norm, normalize_group(g)) > 2:
            continue

        evidence: list[str] = []
        backed_by_candidate = 0
        backed_by_stated = 0
        checkable = 0

        for r in rows:
            if not r.instead_of.strip():
                continue
            checkable += 1
            cand_sched = _lesson_at(schedule, g, block.weekday, r.pair_number)
            stated_sched = (
                _lesson_at(schedule, stated_group, block.weekday, r.pair_number)
                if stated_group in known_set
                else ""
            )
            if lessons_look_same(r.instead_of, cand_sched):
                backed_by_candidate += 1
                evidence.append(f"пара {r.pair_number} («{r.instead_of}») стоит в расписании у «{g}»")
            if stated_sched and lessons_look_same(r.instead_of, stated_sched):
                backed_by_stated += 1

        if checkable > 0 and backed_by_stated == 0 and backed_by_candidate == checkable:
            candidates.append((g, evidence))

    if len(candidates) == 1:
        return _Resolution("typo", candidates[0][0], candidates[0][1])
    return None  # не нашли или неоднозначно — не угадываем
