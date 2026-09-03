from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Literal

from aiogram import Bot
from aiogram.types import BufferedInputFile

from ..config import config
from ..parser.zameny_parser import ZamenyBlock
from ..store.user_store import get_chats_for_group
from ..utils.html import escape_html
from .group_reconcile import ZamenyAnomaly
from .schedule_service import get_zameny, get_zameny_anomalies, get_zameny_file_path
from .zameny_view import format_anomaly_alert


@dataclass
class SnapshotEntry:
    date: str
    weekday: str
    group: str
    pair_number: str
    instead_of: str
    replacement: str
    room: str


Snapshot = dict[str, SnapshotEntry]

ChangeType = Literal["added", "changed", "removed"]


@dataclass
class Change:
    type: ChangeType
    current: SnapshotEntry | None = None
    previous: SnapshotEntry | None = None


def _snapshot_key(date: str, group: str, pair_number: str) -> str:
    return f"{date}|{group}|{pair_number}"


def _build_snapshot(blocks: list[ZamenyBlock]) -> Snapshot:
    snapshot: Snapshot = {}
    for block in blocks:
        for row in block.rows:
            snapshot[_snapshot_key(block.date, row.group, row.pair_number)] = SnapshotEntry(
                date=block.date,
                weekday=block.weekday,
                group=row.group,
                pair_number=row.pair_number,
                instead_of=row.instead_of,
                replacement=row.replacement,
                room=row.room,
            )
    return snapshot


def _entries_equal(a: SnapshotEntry, b: SnapshotEntry) -> bool:
    return a.instead_of == b.instead_of and a.replacement == b.replacement and a.room == b.room


def _diff_snapshots(previous: Snapshot, current: Snapshot) -> list[Change]:
    """Колледж отслеживает лишь скользящее окно дат — когда оно сдвигается,
    все строки со старыми датами исчезают разом. Это не отмена, поэтому
    «пропавшая» строка считается отменой, только если её дата всё ещё есть
    где-то в текущих данных (то есть период отслеживается, а выпала конкретно
    эта строка)."""
    changes: list[Change] = []
    current_dates = {e.date for e in current.values()}

    for key, cur in current.items():
        prev = previous.get(key)
        if prev is None:
            changes.append(Change(type="added", current=cur))
        elif not _entries_equal(prev, cur):
            changes.append(Change(type="changed", current=cur, previous=prev))

    for key, prev in previous.items():
        if key in current:
            continue
        if prev.date not in current_dates:
            continue  # весь период сдвинулся, это не отмена
        changes.append(Change(type="removed", previous=prev))

    return changes


def _format_change(c: Change) -> str:
    e = c.current or c.previous
    assert e is not None
    where = f"{e.weekday}, {e.date}, пара {e.pair_number}"

    if c.type == "removed":
        return f"{where}: замена отменена — всё по расписанию"

    entry = c.current
    assert entry is not None
    if entry.replacement.strip().lower() == "нет":
        return f"{where}: ❌ отменено (было: {escape_html(entry.instead_of)})"

    room = f" {escape_html(entry.room)}" if entry.room else ""
    verb = "замена обновлена" if c.type == "changed" else "новая замена"
    return f"{where}: 🔁 {verb} — «{escape_html(entry.instead_of)}» → «{escape_html(entry.replacement)}»{room}"


def _snapshot_path():
    return config.data_path / "zameny-snapshot.json"


def _load_snapshot() -> Snapshot | None:
    try:
        raw = json.loads(_snapshot_path().read_text("utf-8"))
    except (OSError, ValueError):
        return None
    return {key: SnapshotEntry(**value) for key, value in raw.items()}


def _save_snapshot(snapshot: Snapshot) -> None:
    config.data_path.mkdir(parents=True, exist_ok=True)
    raw = {key: vars(entry) for key, entry in snapshot.items()}
    _snapshot_path().write_text(json.dumps(raw, ensure_ascii=False), "utf-8")


# --- уведомления об опечатках в названии группы ------------------------


def _anomaly_key(a: ZamenyAnomaly) -> str:
    rows = ";".join(
        sorted(f"{r.pair_number}:{r.instead_of}>{r.replacement}@{r.room}" for r in a.rows)
    )
    return f"{a.date}|{a.stated_group}=>{a.likely_group}|{rows}"


def _anomalies_state_path():
    return config.data_path / "zameny-anomalies-notified.json"


def _load_notified_anomalies() -> set[str] | None:
    try:
        return set(json.loads(_anomalies_state_path().read_text("utf-8")))
    except (OSError, ValueError):
        return None


def _save_notified_anomalies(keys: set[str]) -> None:
    config.data_path.mkdir(parents=True, exist_ok=True)
    _anomalies_state_path().write_text(json.dumps(sorted(keys), ensure_ascii=False), "utf-8")


@dataclass
class FreshAnomalies:
    fresh: list[ZamenyAnomaly]
    next_notified: set[str]
    seed_only: bool


def select_fresh_anomalies(anomalies: list[ZamenyAnomaly], notified: set[str] | None) -> FreshAnomalies:
    """Чистый шаг решения: какие аномалии новые с прошлого раза и каким должно
    стать сохранённое множество «уже сообщили».
     - notified is None (файла состояния нет) → молча засеять, никого не уведомлять;
     - иначе → всё, чей ключ неизвестен, — свежее; как только появилось свежее,
       сохраняем всё текущее множество, иначе просто выкидываем исчезнувшие ключи."""
    current_keys = {_anomaly_key(a) for a in anomalies}
    if notified is None:
        return FreshAnomalies(fresh=[], next_notified=current_keys, seed_only=True)

    fresh = [a for a in anomalies if _anomaly_key(a) not in notified]
    next_notified = current_keys if fresh else {k for k in notified if k in current_keys}
    return FreshAnomalies(fresh=fresh, next_notified=next_notified, seed_only=False)


async def _check_for_zameny_anomalies(bot: Bot) -> None:
    """Предупреждает подписчиков, когда замены завели под опечатанным именем
    группы. Ключ — хеш содержимого: исправленная/переформулированная аномалия
    уведомит снова, неизменная — никогда не повторяется."""
    try:
        anomalies = await get_zameny_anomalies()
    except Exception:
        logging.exception("Замены: не удалось получить данные для проверки несоответствий")
        return

    notified = _load_notified_anomalies()
    result = select_fresh_anomalies(anomalies, notified)

    if result.seed_only:
        _save_notified_anomalies(result.next_notified)  # первый запуск — молча
        return
    if not result.fresh:
        _save_notified_anomalies(result.next_notified)  # выкинуть исчезнувшие ключи
        return

    file_bytes: bytes | None = None
    try:
        file_bytes = (await get_zameny_file_path()).read_bytes()
    except Exception:
        logging.exception("Замены: не удалось прочитать файл для рассылки о несоответствии")

    for a in result.fresh:
        # Подписчики вероятно-правильной группы слышат «эти замены для вас»;
        # подписчики опечатанного имени (если это тоже реальная группа) —
        # «возможно, не для вас». Не пишем одному чату дважды.
        likely_chats = await get_chats_for_group(a.likely_group)
        stated_chats = [c for c in await get_chats_for_group(a.stated_group) if c not in likely_chats]
        targets = [(c, a.likely_group) for c in likely_chats] + [(c, a.stated_group) for c in stated_chats]

        for chat_id, viewer_group in targets:
            try:
                await bot.send_message(chat_id, format_anomaly_alert(a, viewer_group))
                if file_bytes is not None:
                    await bot.send_document(chat_id, BufferedInputFile(file_bytes, filename="zameny.xlsx"))
            except Exception:
                logging.exception("Замены: не удалось уведомить чат %s о несоответствии", chat_id)

    _save_notified_anomalies(result.next_notified)


async def check_for_zameny_changes(bot: Bot) -> None:
    await _check_for_zameny_anomalies(bot)

    try:
        blocks = await get_zameny()
    except Exception:
        logging.exception("Замены: не удалось получить данные для проверки изменений")
        return

    current = _build_snapshot(blocks)
    previous = _load_snapshot()

    if previous is None:
        # Самый первый запуск: сравнивать не с чем, а рассылать всю текущую
        # таблицу замен всем — это спам. Просто запоминаем точку отсчёта.
        _save_snapshot(current)
        return

    changes = _diff_snapshots(previous, current)
    if not changes:
        return

    by_group: dict[str, list[Change]] = {}
    for c in changes:
        entry = c.current or c.previous
        assert entry is not None
        by_group.setdefault(entry.group, []).append(c)

    for group, group_changes in by_group.items():
        chat_ids = await get_chats_for_group(group)
        if not chat_ids:
            continue

        text = "\n".join(
            [f"🔔 <b>Изменения в заменах — {escape_html(group)}</b>", *(_format_change(c) for c in group_changes)]
        )

        for chat_id in chat_ids:
            try:
                await bot.send_message(chat_id, text)
            except Exception:
                logging.exception("Замены: не удалось уведомить чат %s", chat_id)

    _save_snapshot(current)


_task: asyncio.Task | None = None


def start_zameny_watcher(bot: Bot) -> None:
    global _task

    async def _loop() -> None:
        interval = config.notify_interval_minutes * 60
        while True:
            await asyncio.sleep(interval)
            try:
                await check_for_zameny_changes(bot)
            except Exception:
                logging.exception("Замены: сбой проверки изменений")

    _task = asyncio.create_task(_loop())


def stop_zameny_watcher() -> None:
    if _task is not None and not _task.done():
        _task.cancel()
