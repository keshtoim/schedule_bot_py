from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from aiogram import Bot
from aiogram.types import BufferedInputFile

from ..config import config
from ..parser.zameny_parser import ZamenyBlock
from ..store.user_store import get_chats_for_group, get_subscribed_groups
from .group_reconcile import ZamenyAnomaly
from .rich_message import send_rich_message_html
from .schedule_service import get_zameny, get_zameny_anomalies, get_zameny_file_path
from .zameny_view import (
    ZamenyDigest,
    ZamenyDigestKind,
    build_zameny_digest_rich_html,
    format_anomaly_alert,
    format_zameny_digest_plain,
)

log = logging.getLogger(__name__)

# ======================================================================
#  Дайджесты замен по группам: когда у подписанной группы появляются или
#  меняются замены — присылаем актуальный список, оформленный как расписание.
# ======================================================================


@dataclass
class GroupDigestState:
    sig: str  # сигнатура текущих замен группы; "" = замен нет
    dates: list[str]  # dd.mm.yyyy даты, на которые у группы сейчас есть замены


DigestStore = dict[str, GroupDigestState]


def _blocks_for_group(blocks: list[ZamenyBlock], group: str) -> list[ZamenyBlock]:
    """Только строки этой группы, без ставших пустыми блоков; стабильный порядок."""
    result: list[ZamenyBlock] = []
    for b in blocks:
        rows = [r for r in b.rows if r.group == group]
        if rows:
            result.append(ZamenyBlock(weekday=b.weekday, date=b.date, rows=rows))
    return result


def _group_signature(group_blocks: list[ZamenyBlock]) -> str:
    parts = [
        f"{b.date}|{r.pair_number}|{r.instead_of}|{r.replacement}|{r.room}"
        for b in group_blocks
        for r in b.rows
    ]
    return "\n".join(sorted(parts))


@dataclass
class _DigestDecision:
    digest: ZamenyDigest | None
    next: GroupDigestState


def diff_group_digest(
    prev: GroupDigestState | None,
    current_blocks: list[ZamenyBlock],
    all_current_dates: set[str],
) -> _DigestDecision:
    """Чистый шаг решения для одной группы.
     - сигнатура не изменилась → ничего не делаем;
     - сигнатура изменилась и у группы всё ещё есть замены → уведомляем
       ("new", если раньше замен не было, иначе "updated");
     - сигнатура стала пустой → уведомляем только про даты, которые всё ещё
       публикуются (настоящая отмена), а не про ушедшие из окна колледжа."""
    sig = _group_signature(current_blocks)
    dates = [b.date for b in current_blocks]
    nxt = GroupDigestState(sig=sig, dates=dates)
    before = prev or GroupDigestState(sig="", dates=[])

    if sig == before.sig:
        return _DigestDecision(digest=None, next=nxt)

    cancelled_dates = [d for d in before.dates if d not in dates and d in all_current_dates]
    has_current = len(current_blocks) > 0
    if not has_current and not cancelled_dates:
        return _DigestDecision(digest=None, next=nxt)

    kind: ZamenyDigestKind = "cleared" if not has_current else ("new" if before.sig == "" else "updated")
    return _DigestDecision(
        digest=ZamenyDigest(group="", kind=kind, blocks=current_blocks, cancelled_dates=cancelled_dates),
        next=nxt,
    )


def _digest_store_path():
    return config.data_path / "zameny-group-digests.json"


def _load_digest_store() -> DigestStore | None:
    try:
        raw = json.loads(_digest_store_path().read_text("utf-8"))
    except (OSError, ValueError):
        return None
    return {group: GroupDigestState(**value) for group, value in raw.items()}


def _save_digest_store(store: DigestStore) -> None:
    config.data_path.mkdir(parents=True, exist_ok=True)
    raw = {group: dataclasses.asdict(state) for group, state in store.items()}
    _digest_store_path().write_text(json.dumps(raw, ensure_ascii=False, indent=2), "utf-8")


async def _send_digest(bot: Bot, chat_id: int, digest: ZamenyDigest) -> None:
    try:
        await send_rich_message_html(chat_id, build_zameny_digest_rich_html(digest))
    except Exception:  # noqa: BLE001
        await bot.send_message(chat_id, format_zameny_digest_plain(digest))


async def _check_group_zameny_digests(bot: Bot, blocks: list[ZamenyBlock]) -> None:
    subscribed = await get_subscribed_groups()
    if not subscribed:
        return

    all_current_dates = {b.date for b in blocks}
    stored = _load_digest_store()

    # Самый первый запуск: запоминаем, где стоит каждая подписанная группа, и
    # никого не уведомляем — свежий деплой не должен разослать всю таблицу.
    if stored is None:
        seed: DigestStore = {}
        for group in subscribed:
            seed[group] = diff_group_digest(None, _blocks_for_group(blocks, group), all_current_dates).next
        _save_digest_store(seed)
        log.info("Дайджесты замен: первый прогон, запомнил состояние %d групп(ы)", len(seed))
        return

    # Пересобираем с нуля, чтобы записи групп, которые больше никто не выбрал, отпали.
    store: DigestStore = {}
    notified_groups = 0
    for group in subscribed:
        decision = diff_group_digest(stored.get(group), _blocks_for_group(blocks, group), all_current_dates)
        store[group] = decision.next
        if decision.digest is None:
            continue

        decision.digest.group = group
        chats = await get_chats_for_group(group)
        notified_groups += 1
        log.info("Замены у «%s» изменились (%s) → уведомляю %d чат(ов)", group, decision.digest.kind, len(chats))
        for chat_id in chats:
            try:
                await _send_digest(bot, chat_id, decision.digest)
            except Exception:
                log.exception("Замены: не удалось отправить дайджест чату %s", chat_id)

    if not notified_groups:
        log.info("Дайджесты замен: изменений у подписанных групп нет (%d групп проверено)", len(subscribed))
    _save_digest_store(store)


# ======================================================================
#  Уведомления об опечатках в названии группы
# ======================================================================


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
        log.exception("Замены: не удалось получить данные для проверки несоответствий")
        return

    notified = _load_notified_anomalies()
    result = select_fresh_anomalies(anomalies, notified)

    if result.seed_only:
        _save_notified_anomalies(result.next_notified)  # первый запуск — молча
        log.info("Опечатки в группах: первый прогон, запомнил %d аномалий(ю)", len(result.next_notified))
        return
    if not result.fresh:
        _save_notified_anomalies(result.next_notified)  # выкинуть исчезнувшие ключи
        return

    log.warning(
        "Опечатки в группах: %d новых — рассылаю (%s)",
        len(result.fresh),
        ", ".join(f"{a.stated_group}→{a.likely_group}" for a in result.fresh),
    )
    file_bytes: bytes | None = None
    try:
        file_bytes = (await get_zameny_file_path()).read_bytes()
    except Exception:
        log.exception("Замены: не удалось прочитать файл для рассылки о несоответствии")

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
                log.exception("Замены: не удалось уведомить чат %s о несоответствии", chat_id)

    _save_notified_anomalies(result.next_notified)


# ======================================================================


async def check_for_zameny_changes(bot: Bot) -> None:
    log.info("Проверяю замены на изменения…")
    await _check_for_zameny_anomalies(bot)

    try:
        blocks = await get_zameny()
    except Exception:
        log.exception("Замены: не удалось получить данные для проверки изменений")
        return

    await _check_group_zameny_digests(bot, blocks)


def next_run(now: datetime, start: time, interval_hours: int) -> datetime:
    """Следующий момент проверки замен: сегодня в `start`, затем каждые
    `interval_hours` часов, пока не перевалит за полночь. Все сегодняшние
    слоты прошли — завтра в `start`. Ночью колледж замены не публикует."""
    step = timedelta(hours=max(1, interval_hours))
    slot = datetime.combine(now.date(), start)
    while slot.date() == now.date():
        if slot > now + timedelta(seconds=1):
            return slot
        slot += step
    return datetime.combine(now.date() + timedelta(days=1), start)


_task: asyncio.Task | None = None


def start_zameny_watcher(bot: Bot) -> None:
    global _task

    async def _loop() -> None:
        start, interval_h = config.notify_start, max(1, config.notify_interval_hours)
        log.info(
            "Наблюдатель замен запущен: первая проверка дня в %s, далее каждые %d ч до полуночи",
            start.strftime("%H:%M"), interval_h,
        )
        # Догоняющий прогон вскоре после старта — процесс мог лежать и
        # пропустить слот; дедуп в дайджестах не даст задублировать рассылку.
        await asyncio.sleep(30)
        while True:
            try:
                await check_for_zameny_changes(bot)
            except Exception:
                log.exception("Замены: сбой проверки изменений")

            nxt = next_run(datetime.now(), start, interval_h)
            wait = (nxt - datetime.now()).total_seconds()
            log.info("Следующая проверка замен: %s (через %.1f ч)", nxt.strftime("%d.%m %H:%M"), wait / 3600)
            await asyncio.sleep(max(1.0, wait))

    _task = asyncio.create_task(_loop())


def stop_zameny_watcher() -> None:
    if _task is not None and not _task.done():
        log.info("Останавливаю наблюдатель замен")
        _task.cancel()
