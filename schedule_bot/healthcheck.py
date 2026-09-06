"""Docker HEALTHCHECK: свежий ли heartbeat, который пишет housekeeping.

    python -m schedule_bot.healthcheck

Читает DATA_DIR напрямую — конфиг и токен не нужны. exit 0 = здоров.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# housekeeping.HEARTBEAT_FILE — держим синхронно, но не импортируем оттуда:
# тот модуль тянет config (BOT_TOKEN и пр.), а здесь это лишнее.
_HEARTBEAT_FILE = "heartbeat"
_MAX_AGE_S = 5 * 60


def main() -> int:
    hb = Path(os.getenv("DATA_DIR") or "data") / _HEARTBEAT_FILE
    try:
        ts = int(hb.read_text())
    except (OSError, ValueError):
        print(f"нет heartbeat: {hb}", file=sys.stderr)
        return 1

    age = time.time() - ts
    if age > _MAX_AGE_S:
        print(f"heartbeat протух: {age:.0f} с назад", file=sys.stderr)
        return 1

    print(f"ok: heartbeat {age:.0f} с назад")
    return 0


if __name__ == "__main__":
    sys.exit(main())
