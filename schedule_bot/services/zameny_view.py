from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from ..parser.zameny_parser import ZamenyBlock, ZamenyRow
from ..utils.html import escape_html
from .group_reconcile import ZamenyAnomaly


def format_zameny_row(row: ZamenyRow) -> str:
    """Одна строка замены как пункт списка для сообщения с parse_mode="HTML"."""
    room = f" {escape_html(row.room)}" if row.room else ""
    if row.replacement.strip().lower() == "нет":
        return f"  Пара {row.pair_number}: ❌ <i>отменено (было: {escape_html(row.instead_of)})</i>"
    if not row.instead_of.strip():
        return f"  Пара {row.pair_number}: ➕ <i>{escape_html(row.replacement)}{room}</i>"
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


# --- проактивный дайджест «замены обновились» --------------------------

ZamenyDigestKind = Literal["new", "updated", "cleared"]


@dataclass
class ZamenyDigest:
    group: str
    kind: ZamenyDigestKind
    blocks: list[ZamenyBlock]  # уже отфильтрованы к строкам этой группы, без пустых блоков
    cancelled_dates: list[str] = field(default_factory=list)  # даты, чьи замены сняли, пока дата ещё публикуется


def _digest_intro(kind: ZamenyDigestKind, group: str) -> tuple[str, str]:
    g = escape_html(group)
    if kind == "new":
        return (
            f"🔄 Новые замены — {g}",
            "Колледж опубликовал замены для вашей группы. Актуальный список:",
        )
    if kind == "updated":
        return (
            f"🔄 Замены обновились — {g}",
            "Колледж изменил замены для вашей группы. Актуальный список:",
        )
    return f"✅ Замены отменили — {g}", "Снова всё по расписанию."


def _now_text(r: ZamenyRow) -> tuple[str, str]:
    room = f", ауд. {r.room}" if r.room else ""
    if not r.replacement.strip() or r.replacement.strip().lower() == "нет":
        return "❌", "пара отменена"
    return "🔁", f"{r.replacement}{room}"


def build_zameny_digest_rich_html(d: ZamenyDigest) -> str:
    """Rich-HTML — заголовок + таблица на каждую дату, оформлено как расписание."""
    title, subtitle = _digest_intro(d.kind, d.group)
    parts = [f"<h3>{title}</h3>", f"<p><i>{escape_html(subtitle)}</i></p>"]

    for block in d.blocks:
        parts.append(f"<h4>{escape_html(block.weekday)}, {escape_html(block.date)}</h4>")
        parts.append("<table bordered striped><tr><th>№ пары</th><th>Было по расписанию</th><th>Замена</th></tr>")
        for r in block.rows:
            was = escape_html(r.instead_of) if r.instead_of.strip() else "—"
            icon, text = _now_text(r)
            parts.append(f"<tr><td>{escape_html(r.pair_number)}</td><td>{was}</td><td>{icon} {escape_html(text)}</td></tr>")
        parts.append("</table>")

    for date in d.cancelled_dates:
        parts.append(f"<p>✅ Замены на {escape_html(date)} убрали — на этот день всё по расписанию.</p>")

    return "".join(parts)


def format_zameny_digest_plain(d: ZamenyDigest) -> str:
    """Запасной вариант (parse_mode="HTML") на случай, если sendRichMessage недоступен."""
    title, subtitle = _digest_intro(d.kind, d.group)
    lines = [f"<b>{title}</b>", f"<i>{escape_html(subtitle)}</i>", ""]

    for block in d.blocks:
        lines.append(f"<b>{escape_html(block.weekday)}, {escape_html(block.date)}:</b>")
        lines.extend(format_zameny_row(r) for r in block.rows)
        lines.append("")

    for date in d.cancelled_dates:
        lines.append(f"✅ <i>Замены на {escape_html(date)} убрали — на этот день всё по расписанию.</i>")

    return "\n".join(lines).rstrip()
