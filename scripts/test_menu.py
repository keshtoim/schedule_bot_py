"""Клавиатуры меню: python -m scripts.test_menu"""

from __future__ import annotations

import sys

from schedule_bot.keyboards import (
    GROUPS_PER_PAGE,
    REMINDER_CHOICES,
    Button,
    build_bug_cancel_menu,
    build_group_confirm,
    build_group_picker,
    build_group_search_results,
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

# --- выбор группы: листание по страницам --------------------------
def cbs_of(markup) -> list[str]:
    return [b.callback_data for row in markup.inline_keyboard for b in row]


small = [f"23-ИСП-{i}" for i in range(1, 5)]  # 4 группы — влезают на одну страницу
sm = build_group_picker("23", small, 0)
check("мало групп — без строки листания", not any(c == "noop" or c.startswith("year:") for c in cbs_of(sm)))
check("мало групп — есть «Назад» к курсам", "back:courses" in cbs_of(sm))
check("мало групп — все группы показаны", [f"grp:{g}" for g in small] == [c for c in cbs_of(sm) if c.startswith("grp:")])

big = [f"24-ТЕСТ-{i:02d}" for i in range(1, GROUPS_PER_PAGE * 2 + 3)]  # 3 страницы
p0 = cbs_of(build_group_picker("24", big, 0))
check("много групп, стр.1: ровно GROUPS_PER_PAGE групп", len([c for c in p0 if c.startswith("grp:")]) == GROUPS_PER_PAGE)
check("много групп, стр.1: есть «вперёд», нет «назад»", "year:24:1" in p0 and "year:24:-1" not in p0)
check("много групп, стр.1: индикатор 1/3", any(b.text == "1/3" for row in build_group_picker("24", big, 0).inline_keyboard for b in row))

p1 = cbs_of(build_group_picker("24", big, 1))
check("стр.2: есть и «назад», и «вперёд»", "year:24:0" in p1 and "year:24:2" in p1)

last = build_group_picker("24", big, 9)  # за пределами — зажимается к последней
lc = cbs_of(last)
check("страница за пределами зажимается к последней", "year:24:1" in lc and not any(c == "year:24:3" for c in lc))
check("последняя страница: нет «вперёд»", not any(c.startswith("year:24:") and c.endswith(":3") for c in lc))
check("последняя страница: остаток групп", len([c for c in lc if c.startswith("grp:")]) == len(big) - GROUPS_PER_PAGE * 2)
check("на каждой странице есть «Назад» к курсам", "back:courses" in p0 and "back:courses" in p1)

# --- результаты текстового поиска группы --------------------------
res = build_group_search_results(["23-ИСП-1", "24-ИСП-1"])
rcbs = cbs_of(res)
check("поиск: кнопки групп через grp:", rcbs[:2] == ["grp:23-ИСП-1", "grp:24-ИСП-1"])
check("поиск: есть выход «Все курсы» → back:courses", "back:courses" in rcbs)

# --- подтверждение выбранной группы ------------------------------
conf = build_group_confirm("23-ИСП-1")
ccbs = cbs_of(conf)
check("подтверждение: «Да» → grpok:<группа>", "grpok:23-ИСП-1" in ccbs)
check("подтверждение: «Выбрать другую» → back:courses", "back:courses" in ccbs)
check("grpok: не перехватывается фильтром grp:", not "grpok:23-ИСП-1".startswith("grp:"))

# --- клавиатура ожидания багрепорта -------------------------------
check("багрепорт: на клавиатуре только «Отмена»", texts(build_bug_cancel_menu()) == [Button.BUG_CANCEL])

print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
sys.exit(0 if failed == 0 else 1)
