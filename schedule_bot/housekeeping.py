"""Фоновые мелочи: heartbeat для healthcheck и суточный бэкап users.json."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import time

from .config import config

log = logging.getLogger(__name__)

HEARTBEAT_FILE = "heartbeat"

_HEARTBEAT_EVERY_S = 60
_BACKUP_EVERY_S = 24 * 3600

_task: asyncio.Task | None = None


def _touch_heartbeat() -> None:
    """Отметка «событийный цикл жив» — healthcheck смотрит на её свежесть."""
    config.data_path.mkdir(parents=True, exist_ok=True)
    (config.data_path / HEARTBEAT_FILE).write_text(str(int(time.time())))


def _backup_users() -> None:
    """Копия users.json в .bak (и предыдущая — в .bak.prev). Бэкапим только
    валидный непустой JSON, чтобы не затереть хорошую копию мусором."""
    src = config.data_path / "users.json"
    try:
        data = json.loads(src.read_text("utf-8"))
    except (OSError, ValueError):
        log.warning("Бэкап users.json пропущен — файла нет или он битый")
        return
    if not data:
        return

    bak = config.data_path / "users.json.bak"
    if bak.is_file():
        bak.replace(config.data_path / "users.json.bak.prev")
    shutil.copy2(src, bak)
    log.info("Бэкап users.json: %d записей", len(data))


def start_housekeeping() -> None:
    global _task

    async def _loop() -> None:
        log.info("Housekeeping запущен (heartbeat раз в %d с, бэкап users.json раз в сутки)", _HEARTBEAT_EVERY_S)
        last_backup = 0.0
        while True:
            try:
                await asyncio.to_thread(_touch_heartbeat)
                if time.time() - last_backup >= _BACKUP_EVERY_S:
                    await asyncio.to_thread(_backup_users)
                    last_backup = time.time()
            except Exception:
                log.exception("Housekeeping: сбой цикла")
            await asyncio.sleep(_HEARTBEAT_EVERY_S)

    _task = asyncio.create_task(_loop())


def stop_housekeeping() -> None:
    if _task is not None and not _task.done():
        _task.cancel()
