"""heartbeat + бэкап users.json: python -m scripts.test_housekeeping"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

_DATA = Path(tempfile.mkdtemp(prefix="hk-test-"))
os.environ["DATA_DIR"] = str(_DATA)
os.environ.setdefault("BOT_TOKEN", "test")
os.environ.setdefault("SCHEDULE_SOURCE", "x")
os.environ.setdefault("ZAMENY_SOURCE", "y")

from schedule_bot import healthcheck  # noqa: E402
from schedule_bot.housekeeping import HEARTBEAT_FILE, _backup_users, _touch_heartbeat  # noqa: E402

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


def write_users(mapping: dict[str, str]) -> None:
    (_DATA / "users.json").write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")


def read_bak() -> str:
    return (_DATA / "users.json.bak").read_text(encoding="utf-8")


try:
    # --- heartbeat / healthcheck ------------------------------------
    _touch_heartbeat()
    check("heartbeat создан", (_DATA / HEARTBEAT_FILE).is_file())
    check("healthcheck: свежий heartbeat -> 0", healthcheck.main() == 0)

    (_DATA / HEARTBEAT_FILE).write_text(str(int(time.time()) - 10 * 60))
    check("healthcheck: протухший heartbeat -> 1", healthcheck.main() == 1)

    (_DATA / HEARTBEAT_FILE).unlink()
    check("healthcheck: нет heartbeat -> 1", healthcheck.main() == 1)

    # --- бэкап users.json -----------------------------------------
    bak = _DATA / "users.json.bak"

    _backup_users()
    check("нет users.json -> бэкап не создан", not bak.exists())

    write_users({"1": "23-ИСП-1", "2": "24-ТМ"})
    _backup_users()
    check("валидный users.json -> .bak создан", bak.is_file())
    check(".bak = копия содержимого", read_bak() == (_DATA / "users.json").read_text(encoding="utf-8"))

    write_users({"1": "23-ИСП-1", "2": "24-ТМ", "3": "25-ЭБУ"})
    _backup_users()
    check("второй бэкап -> прошлая копия в .bak.prev", (_DATA / "users.json.bak.prev").is_file())

    good = read_bak()
    (_DATA / "users.json").write_text("{битый json", encoding="utf-8")
    _backup_users()
    check("битый users.json -> хорошую .bak не затёрли", read_bak() == good)

    (_DATA / "users.json").write_text("{}", encoding="utf-8")
    _backup_users()
    check("пустой users.json -> .bak не тронут", read_bak() == good)

finally:
    shutil.rmtree(_DATA, ignore_errors=True)

print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
