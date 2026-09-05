"""Собирает PNG из SVG в schedule_bot/assets/ — их бот и отправляет.

Запуск:  python -m scripts.render_assets
Нужен один раз и после правок SVG. Готовые PNG коммитим в репозиторий,
чтобы на сервере растеризатор не требовался.

Зависимости только для сборки картинок, не для бота:
    pip install -e ".[assets]"        # svglib + rlPyCairo
или вручную:
    pip install "svglib>=1.5" "rlPyCairo>=0.3"

Если что-то рендерится криво — открой .svg в браузере и сохрани как PNG,
результат тот же (в SVG нет текста и прозрачности специально ради этого).
"""

from __future__ import annotations

import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "schedule_bot" / "assets"


def main() -> int:
    try:
        from reportlab.graphics import renderPM
        from svglib.svglib import svg2rlg
    except ImportError:
        print('Нужен svglib:  pip install "svglib>=1.5"', file=sys.stderr)
        return 1

    svgs = sorted(ASSETS.glob("*.svg"))
    if not svgs:
        print(f"В {ASSETS} нет .svg", file=sys.stderr)
        return 1

    for svg in svgs:
        drawing = svg2rlg(str(svg))
        out = svg.with_suffix(".png")
        # svglib переводит px -> pt (x0.75); dpi=96 возвращает исходный размер
        # в пикселях, т.е. width/height из SVG (1024xN) как есть.
        renderPM.drawToFile(drawing, str(out), fmt="PNG", dpi=96)
        print(f"{svg.name}  ->  {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
