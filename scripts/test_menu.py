"""Клавиатуры меню: python -m scripts.test_menu"""

from __future__ import annotations

import sys

from schedule_bot.keyboards import (
    Button,
    build_bug_cancel_menu,
    build_main_menu,
    build_more_menu,
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
check("главное меню: 6 кнопок", len(t) == 6)
check("есть Сегодня/Завтра/Неделя/Замены", all(b in t for b in (Button.TODAY, Button.TOMORROW, Button.WEEK, Button.ZAMENY)))
check("есть «Настройки» и «Ещё»", Button.SETTINGS in t and Button.MORE in t)
check("группы на кнопке больше нет (ушла в Настройки)", not any(x.startswith("👥 2") for x in t))
check("«Общее расписание» / «След. неделя» не на главной", Button.FULL_SCHEDULE not in t and Button.NEXT_WEEK not in t)

# --- подменю «Ещё» -------------------------------------------------
mt = texts(build_more_menu())
check("Ещё: расписание/след.неделя/файлы + Назад", all(b in mt for b in (Button.FULL_SCHEDULE, Button.NEXT_WEEK, Button.SCHEDULE_FILE, Button.ZAMENY_FILE, Button.BACK)))
check("Ещё: без кнопок главного меню", not any(b in mt for b in (Button.TODAY, Button.MORE, Button.SETTINGS)))

# --- подменю «Настройки» ------------------------------------------
st = texts(build_settings_menu())
check("Настройки: Группа / Сообщить об ошибке / Сбросить профиль / Назад", st == [Button.GROUP, Button.BUG, Button.RESET, Button.BACK])
check("«👥 Группа» матчится префиксом (как и старая «👥 23-ИСП-1»)", Button.GROUP.startswith(Button.GROUP_PREFIX))

# --- клавиатура ожидания багрепорта -------------------------------
check("багрепорт: на клавиатуре только «Отмена»", texts(build_bug_cancel_menu()) == [Button.BUG_CANCEL])

print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
