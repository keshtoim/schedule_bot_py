"""Картинки бота: python -m scripts.test_assets"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from schedule_bot.assets import _DIR, photo

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


EXPECTED = ["welcome", "updated", "schedule", "zameny_ok", "offline"]

for name in EXPECTED:
    svg = _DIR / f"{name}.svg"
    check(f"{name}.svg существует", svg.is_file())
    if not svg.is_file():
        continue

    try:
        root = ET.fromstring(svg.read_text("utf-8"))
        parsed = True
    except ET.ParseError as err:
        parsed = False
        print("   ", err)
    check(f"{name}.svg — валидный XML", parsed)
    if not parsed:
        continue

    check(f"{name}.svg: есть viewBox", root.get("viewBox") is not None)
    check(f"{name}.svg: заданы width/height", bool(root.get("width")) and bool(root.get("height")))

    # Без <text> — картинка растеризуется одинаково где угодно, без шрифтов
    texts = root.findall(".//{http://www.w3.org/2000/svg}text")
    check(f"{name}.svg: нет текста (не зависит от шрифтов)", texts == [])


# --- helper photo(): нет PNG -> None, есть -> FSInputFile -------------
missing = photo("definitely-not-a-real-asset")
check("photo() для несуществующего имени -> None", missing is None)

for name in EXPECTED:
    png = _DIR / f"{name}.png"
    got = photo(name)
    if png.is_file():
        check(f"photo('{name}') -> FSInputFile (PNG собран)", got is not None)
    else:
        check(f"photo('{name}') -> None (PNG ещё не собран)", got is None)

print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
