"""Различаем сетевой сбой и баг в коде: python -m scripts.test_error_kind"""

from __future__ import annotations

import socket
import sys

import httpx
from aiogram.exceptions import TelegramNetworkError

from schedule_bot.utils.describe_error import is_network_error

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


check("ConnectError — сетевой", is_network_error(httpx.ConnectError("boom")))
check("ReadTimeout — сетевой", is_network_error(httpx.ReadTimeout("slow")))
check("socket.gaierror — сетевой", is_network_error(socket.gaierror("dns")))
check("ConnectionResetError — сетевой", is_network_error(ConnectionResetError()))
check("TelegramNetworkError — сетевой", is_network_error(TelegramNetworkError(method=None, message="x")))

wrapped = ValueError("parse failed")
try:
    raise wrapped from httpx.ConnectError("under")
except ValueError as e:
    check("обёрнутый сетевой (raise ... from) — сетевой", is_network_error(e))

check("обычный ValueError — НЕ сетевой", not is_network_error(ValueError("bug")))
check("KeyError — НЕ сетевой", not is_network_error(KeyError("x")))

print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
