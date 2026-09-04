"""Клавиатура меню под пользователя: python -m scripts.test_menu"""

from __future__ import annotations

import sys

from schedule_bot.keyboards import Button, build_main_menu, build_more_menu, group_button_text

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
check("клавиатура закреплена", no_group.is_persistent is True)

# --- с группой: полное меню, кнопка группы с названием ----------------
menu = build_main_menu("23-ИСП-1")
t = texts(menu)
check("кнопка группы показывает название", "👥 23-ИСП-1" in t)
check("есть «Ещё»", Button.MORE in t)
check("есть «Сегодня»/«Завтра»/«Неделя»/«Замены»", all(b in t for b in (Button.TODAY, Button.TOMORROW, Button.WEEK, Button.ZAMENY)))
check("«Общее расписание» ушло с клавиатуры", Button.FULL_SCHEDULE not in t)
check("«След. неделя» ушла с клавиатуры", Button.NEXT_WEEK not in t)
check("6 кнопок", len(t) == 6)

# --- матчинг кнопки группы по префиксу -------------------------------
check("текст кнопки группы совпадает с префиксом", group_button_text("24-ТМ").startswith(Button.GROUP_PREFIX))
check("«👥 24-ТМ».startswith(префикс)", "👥 24-ТМ".startswith(Button.GROUP_PREFIX))

# --- подменю «Ещё»: то, что ушло с главной клавиатуры, — здесь ---------
more = build_more_menu()
mt = texts(more)
check(
    "подменю содержит общее расписание/след. неделю/файлы",
    all(b in mt for b in (Button.FULL_SCHEDULE, Button.NEXT_WEEK, Button.SCHEDULE_FILE, Button.ZAMENY_FILE)),
)
check("в подменю есть «Назад»", Button.BACK in mt)
check("в подменю нет кнопок главного меню", not any(b in mt for b in (Button.TODAY, Button.TOMORROW, Button.MORE)))
check("подменю закреплено", more.is_persistent is True)

print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
