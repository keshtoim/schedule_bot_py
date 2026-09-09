"""Проверка парсера замен на новом формате файла: python -m scripts.test_zameny_parse"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from schedule_bot.parser.schedule_parser import parse_schedule
from schedule_bot.parser.workbook import load_active_sheet
from schedule_bot.parser.zameny_parser import expand_group_cell, parse_zameny
from schedule_bot.services.group_reconcile import find_zameny_anomalies

SAMPLES = Path(__file__).resolve().parent.parent / "scratch_samples"

failed = 0


def check(name: str, cond: bool) -> None:
    global failed
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        failed += 1


class _FakeSheet:
    """Достаточно для parse_zameny: он трогает только max_row и text()."""

    def __init__(self, rows: list[list[str]]) -> None:
        self._rows = rows

    @property
    def max_row(self) -> int:
        return len(self._rows)

    @property
    def max_column(self) -> int:
        return 5

    def text(self, row: int, col: int) -> str:
        r = self._rows[row - 1]
        return r[col - 1] if col - 1 < len(r) else ""


def test_multi_group_cell() -> None:
    # --- expand_group_cell: разные способы записать несколько групп ---------
    check("«23-ИСП-1,2,3,4» → 4 группы",
          expand_group_cell("23-ИСП-1,2,3,4") == ["23-ИСП-1", "23-ИСП-2", "23-ИСП-3", "23-ИСП-4"])
    check("пробелы после запятых не мешают",
          expand_group_cell("24-ИСП-1, 2, 3") == ["24-ИСП-1", "24-ИСП-2", "24-ИСП-3"])
    check("разделитель «и»",
          expand_group_cell("23-ИСП-1 и 23-ИСП-2") == ["23-ИСП-1", "23-ИСП-2"])
    check("разделитель «/»",
          expand_group_cell("23-ИСП-1/2") == ["23-ИСП-1", "23-ИСП-2"])
    check("список полных имён через запятую",
          expand_group_cell("23-МТОРПО-1, 23-МТОРПО-2") == ["23-МТОРПО-1", "23-МТОРПО-2"])
    check("одиночная группа — как есть", expand_group_cell("23-ИСП-1") == ["23-ИСП-1"])
    check("группа без номера — как есть", expand_group_cell("24-ТМ") == ["24-ТМ"])
    check("подпись подвала не разворачивается", expand_group_cell("Учебная часть") == ["Учебная часть"])
    check("пустая ячейка → пусто", expand_group_cell("") == [])

    # --- parse_zameny: ячейка с несколькими группами + протяжка вниз --------
    sheet = _FakeSheet([
        ["Изменение в расписании занятий на четверг 10.09.2026г. (знаменатель)"],
        ["ГРУППА", "ПАРА", "ВМЕСТО", "ЗАМЕНА", "кабинет"],
        ["23-ИСП-1,2,3,4", "1пара", "", "ПОПД Захарова", "лекции"],
        ["", "2пара", "", "БЖ Даньков", "лекции"],
        ["25-ЭБУ", "1пара", "ПОПД Зенкина", "ПОПД Захарова", "лекции"],
    ])
    block = parse_zameny(sheet)[0]
    isp3 = [r for r in block.rows if r.group == "23-ИСП-3"]
    check("23-ИСП-3 получил обе пары из общей ячейки",
          sorted(r.pair_number for r in isp3) == ["1", "2"])
    check("развёрнуты все 4 группы × 2 пары = 8 строк",
          len([r for r in block.rows if r.group.startswith("23-ИСП-")]) == 8)
    check("строка-продолжение (пустой A) тоже размножена на все группы",
          len([r for r in block.rows if r.pair_number == "2" and r.group.startswith("23-ИСП-")]) == 4)
    check("следующая одиночная группа не «прилипла» к списку",
          [r.group for r in block.rows if r.group == "25-ЭБУ"] == ["25-ЭБУ"])


def main() -> None:
    test_multi_group_cell()

    if not list(SAMPLES.glob("*.xlsx")):
        print("  skip  проверки на реальных файлах — нет scratch_samples/*.xlsx")
        print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
        sys.exit(0 if failed == 0 else 1)

    # --- формат 2026-09: суффикс чётности в заголовке, имя группы только в
    #     первой строке многострочного блока -------------------------------
    sched = parse_schedule(load_active_sheet(SAMPLES / "raspisanie_2026-09.xlsx"))
    zam = parse_zameny(load_active_sheet(SAMPLES / "zameny_2026-09.xlsx"))

    check("заголовок с суффиксом '(числитель)' парсится", len(zam) >= 1)
    fri = zam[0]
    check("день недели нормализован", fri.weekday == "Пятница")
    check("дата блока извлечена", fri.date == "04.09.2026")

    isp = [r for r in fri.rows if r.group == "23-ИСП-1"]
    check("строки-продолжения наследуют имя группы (3 строки у 23-ИСП-1)", len(isp) == 3)
    check("пары 1, 2 и 4 захвачены", ",".join(sorted(r.pair_number for r in isp)) == "1,2,4")
    check("подвал 'Учебная часть' не считается заменой", not any("учебная часть" in r.group.lower() for r in fri.rows))

    check("нет ложной аномалии на корректном файле", len(find_zameny_anomalies(sched, zam)) == 0)

    # подставляем реальную опечатку (блок записан под 23-ИСП-2)
    zam2 = parse_zameny(load_active_sheet(SAMPLES / "zameny_2026-09.xlsx"))
    for b in zam2:
        for row in b.rows:
            if row.group == "23-ИСП-1":
                row.group = "23-ИСП-2"
    anomalies = find_zameny_anomalies(sched, zam2)
    check("опечатка поймана: 23-ИСП-2 -> 23-ИСП-1", len(anomalies) == 1 and anomalies[0].likely_group == "23-ИСП-1")
    check("аномалия несёт все 3 строки", len(anomalies[0].rows) == 3)

    # --- старый формат 2026-06 всё ещё парсится --------------------------
    zam_old = parse_zameny(load_active_sheet(SAMPLES / "zameny.xlsx"))
    check("старый июньский формат парсит блок с датой", any(re.search(r"\d{2}\.\d{2}\.\d{4}", b.date) for b in zam_old))

    print("\nALL PASS" if failed == 0 else f"\n{failed} FAILED")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
