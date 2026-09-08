"""Клавиатуры меню: python -m scripts.test_menu"""

from __future__ import annotations

import sys

from schedule_bot.keyboards import (
    REMINDER_CHOICES,
    Button,
    build_bug_cancel_menu,
    build_main_menu,
    build_more_menu,
    build_reminder_picker,
    build_settings_menu,
)

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


def texts(markup) -> list[str]:
    return [btn.text for row in markup.keyboard for btn in row]


# --- без группы: одна кнопка «Запустить» ------------------------------
no_group = build_main_menu(None)
check("без группы — одна кнопка", texts(no_group) == [Button.LAUNCH])
check("клавиатура НЕ закреплена (Telegram даёт свернуть)", not no_group.is_persistent)

# --- главное меню с группой -----------------------------------------
t = texts(build_main_menu("23-ИСП-1"))
check("главное меню: 5 кнопок", len(t) == 5)
check("«Сегодня» убрана с клавиатуры", Button.TODAY not in t)
check("есть Завтра/Неделя/Замены", all(b in t for b in (Button.TOMORROW, Button.WEEK, Button.ZAMENY)))
check("есть «Настройки» и «Ещё»", Button.SETTINGS in t and Button.MORE in t)
check("«Общее расписание» / «След. неделя» не на главной", Button.FULL_SCHEDULE not in t and Button.NEXT_WEEK not in t)

# --- подменю «Ещё» -------------------------------------------------
mt = texts(build_more_menu())
check("Ещё: расписание/след.неделя/файлы + Назад", all(b in mt for b in (Button.FULL_SCHEDULE, Button.NEXT_WEEK, Button.SCHEDULE_FILE, Button.ZAMENY_FILE, Button.BACK)))
check("Ещё: без кнопок главного меню", not any(b in mt for b in (Button.TODAY, Button.MORE, Button.SETTINGS)))

# --- подменю «Настройки» ------------------------------------------
st = texts(build_settings_menu())
check("Настройки: Группа / Напоминание / Ошибка / Сброс / Назад", st == [Button.GROUP, Button.REMINDER, Button.BUG, Button.RESET, Button.BACK])
check("«👥 Группа» матчится префиксом (как и старая «👥 23-ИСП-1»)", Button.GROUP.startswith(Button.GROUP_PREFIX))

# --- инлайн-выбор времени напоминания ----------------------------
picker = build_reminder_picker("rem")
cbs = [b.callback_data for row in picker.inline_keyboard for b in row]
check("в пикере все варианты времени + off", cbs == [f"rem:{t}" for t in REMINDER_CHOICES] + ["rem:off"])
check("prefix remo для онбординга", build_reminder_picker("remo").inline_keyboard[0][0].callback_data == "remo:17:00")
check("callback rem:20:00 корректно делится", "rem:20:00".split(":", 1) == ["rem", "20:00"])

# --- клавиатура ожидания багрепорта -------------------------------
check("багрепорт: на клавиатуре только «Отмена»", texts(build_bug_cancel_menu()) == [Button.BUG_CANCEL])

print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
