"""Атомарная запись файлов состояния: python -m scripts.test_atomic"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from schedule_bot.utils.atomic import write_text_atomic

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


with tempfile.TemporaryDirectory() as d:
    target = Path(d) / "sub" / "data.json"
    write_text_atomic(target, '{"a": 1}')
    check("файл создан вместе с родительской папкой", target.read_text() == '{"a": 1}')
    write_text_atomic(target, "second")
    check("перезапись работает", target.read_text() == "second")
    check("временных .tmp не осталось", list(target.parent.glob("*.tmp")) == [])

print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
