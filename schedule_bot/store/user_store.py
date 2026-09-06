from __future__ import annotations

import json

from ..config import config
from ..utils.atomic import write_text_atomic

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
    write_text_atomic(_file_path, json.dumps(data, ensure_ascii=False, indent=2))


async def set_user_group(chat_id: int, group: str) -> None:
    data = _load()
    data[str(chat_id)] = group
    _persist(data)


async def get_user_group(chat_id: int) -> str | None:
    return _load().get(str(chat_id))


async def forget_user(chat_id: int) -> None:
    """Убрать пользователя из хранилища — «сброс профиля»."""
    data = _load()
    if data.pop(str(chat_id), None) is not None:
        _persist(data)


async def get_chats_for_group(group: str) -> list[int]:
    """chat_id всех, кто сейчас подписан на `group` (выбрал её через /group)."""
    return [int(chat_id) for chat_id, g in _load().items() if g == group]


async def get_subscribed_groups() -> list[str]:
    """Различные группы, которые выбрал хотя бы один чат."""
    return list(dict.fromkeys(_load().values()))


async def get_all_chats() -> list[tuple[int, str]]:
    """(chat_id, группа) для всех, кто уже выбрал группу."""
    return [(int(chat_id), group) for chat_id, group in _load().items()]
