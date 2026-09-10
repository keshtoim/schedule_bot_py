"""FSM-хранилище в одном JSON-файле (data/fsm.json).

Единственный FSM в боте — «опиши проблему» для багрепорта. С MemoryStorage
незаконченный диалог терялся при каждом перезапуске/деплое; здесь состояние
и данные переживают рестарт. Объём мизерный (обычно 0–1 запись), пишем весь
файл целиком атомарно на каждое изменение.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey

from ..utils.atomic import write_text_atomic

log = logging.getLogger(__name__)


class JSONFileStorage(BaseStorage):
    """{ "<chat>:<user>:<thread>:<destiny>": {"state": str, "data": {...}} }"""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._lock = asyncio.Lock()
        self._data: dict[str, dict[str, Any]] = self._read()

    def _read(self) -> dict[str, dict[str, Any]]:
        try:
            raw = json.loads(self._path.read_text("utf-8"))
        except (OSError, ValueError):
            return {}
        if not isinstance(raw, dict):
            return {}
        return {k: v for k, v in raw.items() if isinstance(v, dict)}

    def _flush(self) -> None:
        try:
            write_text_atomic(self._path, json.dumps(self._data, ensure_ascii=False))
        except OSError:
            log.warning("FSM: не удалось записать %s", self._path, exc_info=True)

    @staticmethod
    def _key(key: StorageKey) -> str:
        return f"{key.chat_id}:{key.user_id}:{key.thread_id}:{key.destiny}"

    def _record(self, k: str) -> dict[str, Any]:
        return self._data.setdefault(k, {})

    def _prune(self, k: str) -> None:
        if not self._data.get(k):
            self._data.pop(k, None)

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        value = state.state if isinstance(state, State) else state
        k = self._key(key)
        async with self._lock:
            rec = self._record(k)
            if value is None:
                rec.pop("state", None)
            else:
                rec["state"] = value
            self._prune(k)
            self._flush()

    async def get_state(self, key: StorageKey) -> str | None:
        return self._data.get(self._key(key), {}).get("state")

    async def set_data(self, key: StorageKey, data: dict[str, Any]) -> None:
        k = self._key(key)
        async with self._lock:
            rec = self._record(k)
            if data:
                rec["data"] = dict(data)
            else:
                rec.pop("data", None)
            self._prune(k)
            self._flush()

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        return dict(self._data.get(self._key(key), {}).get("data", {}))

    async def close(self) -> None:  # noqa: D102 — ресурсов нет, файл пишется сразу
        return None
