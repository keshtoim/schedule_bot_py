from __future__ import annotations

import logging
from pathlib import Path

from aiogram.types import FSInputFile

log = logging.getLogger(__name__)

_DIR = Path(__file__).parent / "assets"


def photo(name: str) -> FSInputFile | None:
    """FSInputFile для assets/<name>.png или None, если PNG ещё не собран.

    Картинки хранятся как SVG, а PNG для отправки собираются отдельно
    (scripts/render_assets.py). Пока PNG нет — бот просто шлёт текст,
    ничего не падает."""
    path = _DIR / f"{name}.png"
    if path.is_file():
        return FSInputFile(path)
    log.warning("Картинка «%s» не собрана — нет файла %s, шлю текстом", name, path)
    return None
