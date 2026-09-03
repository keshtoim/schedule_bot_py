from __future__ import annotations

import json

from ..config import config

# chat_id (str) -> имя группы
_UserMap = dict[str, str]

_file_path = config.data_path / "users.json"
_cache: _UserMap | None = None


def _load() -> _UserMap:
    global _cache
    if _cache is not None:
        return _cache
    try:
        _cache = json.loads(_file_path.read_text("utf-8"))
    except (OSError, ValueError):
        _cache = {}
    return _cache


def _persist(data: _UserMap) -> None:
    config.data_path.mkdir(parents=True, exist_ok=True)
    _file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


async def set_user_group(chat_id: int, group: str) -> None:
    data = _load()
    data[str(chat_id)] = group
    _persist(data)


async def get_user_group(chat_id: int) -> str | None:
    return _load().get(str(chat_id))
