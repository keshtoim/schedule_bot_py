"""Анти-флуд (token bucket): python -m scripts.test_throttle"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("BOT_TOKEN", "test")
os.environ.setdefault("SCHEDULE_SOURCE", "x")
os.environ.setdefault("ZAMENY_SOURCE", "y")

from schedule_bot.middlewares import TokenBucket  # noqa: E402

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


CAP = 5.0
REFILL = 1 / 3  # токен за 3 с

# --- стартовый запас: ровно CAP действий подряд в один момент времени ---
b = TokenBucket(CAP, now=0.0)
allowed = sum(b.take(0.0, CAP, REFILL) for _ in range(10))
check("подряд пропускает ровно CAP действий", allowed == 5)
check("сразу после — отказ", b.take(0.0, CAP, REFILL) is False)

# --- пополнение во времени ---
check("через 3 с накапывается 1 токен", b.take(3.0, CAP, REFILL) is True)
check("и снова пусто", b.take(3.0, CAP, REFILL) is False)
check("через 1.5 с токена ещё нет", b.take(4.5, CAP, REFILL) is False)

# --- потолок: долгая пауза не даёт больше CAP ---
b2 = TokenBucket(CAP, now=0.0)
for _ in range(5):
    b2.take(0.0, CAP, REFILL)
b2.take(10_000.0, CAP, REFILL)  # огромная пауза — но капнет максимум до CAP
burst = sum(b2.take(10_000.0, CAP, REFILL) for _ in range(10))
check("после долгой паузы запас не превышает CAP", burst == 4)  # 1 уже потрачен строкой выше

print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
