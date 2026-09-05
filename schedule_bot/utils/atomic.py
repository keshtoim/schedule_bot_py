from __future__ import annotations

import os
from pathlib import Path


def write_text_atomic(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Пишет во временный файл рядом и переименовывает на место (атомарно в
    пределах тома). Читатель никогда не увидит недописанный или битый файл,
    даже если процесс упал в момент записи."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(text, encoding=encoding)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
