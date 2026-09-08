"""Режим техработ: бот остаётся живым, но всем кроме владельца отвечает
«вернусь позже». Флаг — файл data/maintenance, переживает перезапуск.
Владелец включает/выключает командой /maintenance.
"""

from __future__ import annotations

import logging

from .config import config

log = logging.getLogger(__name__)

NOTICE = "🔧 Бот на технических работах, скоро вернусь. Загляни попозже."

_file = config.data_path / "maintenance"
_on = _file.exists()


def is_on() -> bool:
    return _on


def toggle() -> bool:
    """Переключить и вернуть новое состояние."""
    global _on
    _on = not _on
    if _on:
        config.data_path.mkdir(parents=True, exist_ok=True)
        _file.touch()
    else:
        _file.unlink(missing_ok=True)
    log.warning("Режим техработ: %s", "ВКЛ" if _on else "выкл")
    return _on
