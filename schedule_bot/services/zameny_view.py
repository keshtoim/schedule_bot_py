from __future__ import annotations

from ..parser.zameny_parser import ZamenyRow
from ..utils.html import escape_html
from .group_reconcile import ZamenyAnomaly


def format_zameny_row(row: ZamenyRow) -> str:
    """Одна строка замены как пункт списка для сообщения с parse_mode="HTML"."""
    room = f" {escape_html(row.room)}" if row.room else ""
    if row.replacement.strip().lower() == "нет":
        return f"  Пара {row.pair_number}: ❌ <i>отменено (было: {escape_html(row.instead_of)})</i>"
    return (
        f"  Пара {row.pair_number}: 🔁 <i>«{escape_html(row.instead_of)}» → "
        f"«{escape_html(row.replacement)}»{room}</i>"
    )


def format_anomaly_alert(a: ZamenyAnomaly, viewer_group: str | None = None) -> str:
    """Предупреждение, что замены записаны под неверным именем группы.
    `viewer_group` подстраивает формулировку под того, кто вызвал /zameny;
    без него — нейтральная формулировка для проактивных уведомлений."""
    lines: list[str] = []
    stated = escape_html(a.stated_group)
    likely = escape_html(a.likely_group)
    when = f"<b>{escape_html(a.weekday)}, {escape_html(a.date)}</b>"

    if viewer_group and a.likely_group == viewer_group:
        lines.append("⚠️ <b>Внимание: похоже, в файле замен опечатка в названии группы.</b>")
        lines.append(
            f"Замены на {when} записаны на группу «{stated}», но, судя по расписанию, "
            f"это замены для <b>вашей</b> группы «{likely}»:"
        )
    elif viewer_group and a.stated_group == viewer_group:
        lines.append("⚠️ <b>Внимание: часть замен, возможно, не для вашей группы.</b>")
        lines.append(
            f"Замены на {when} записаны на «{stated}», но по расписанию они похожи "
            f"на замены для «{likely}»:"
        )
    else:
        lines.append("⚠️ <b>Возможная опечатка в названии группы в заменах.</b>")
        lines.append(
            f"Замены на {when} записаны на «{stated}», но, судя по расписанию, "
            f"относятся к группе «{likely}»:"
        )

    lines.append("")
    lines.extend(format_zameny_row(r) for r in a.rows)

    if a.evidence:
        lines.append("")
        lines.append("<i>" + "; ".join(escape_html(e) for e in a.evidence) + ".</i>")

    lines.append("")
    lines.append("Ниже — оригинал файла замен, проверьте сами 👇")
    return "\n".join(lines)
