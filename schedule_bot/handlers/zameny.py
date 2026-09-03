import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message

from ..keyboards import Button
from ..services.group_reconcile import ZamenyAnomaly
from ..services.schedule_service import get_zameny, get_zameny_anomalies, get_zameny_file_path
from ..parser.zameny_parser import ZamenyRow
from ..store.user_store import get_user_group
from ..utils.html import escape_html

router = Router(name="zameny")


def _format_row(row: ZamenyRow) -> str:
    is_cancelled = row.replacement.strip().lower() == "нет"
    room = f" {escape_html(row.room)}" if row.room else ""
    if is_cancelled:
        return f"  Пара {row.pair_number}: ❌ <i>отменено (было: {escape_html(row.instead_of)})</i>"
    return (
        f"  Пара {row.pair_number}: 🔁 <i>«{escape_html(row.instead_of)}» → "
        f"«{escape_html(row.replacement)}»{room}</i>"
    )


def _format_anomaly(a: ZamenyAnomaly, user_group: str) -> str:
    lines: list[str] = []
    for_user = a.likely_group == user_group

    if for_user:
        lines.append("⚠️ <b>Внимание: похоже, в файле замен опечатка в названии группы.</b>")
        lines.append(
            f"Замены на <b>{a.weekday}, {a.date}</b> записаны на группу «{escape_html(a.stated_group)}», "
            f"но, судя по расписанию, это замены для <b>вашей</b> группы «{escape_html(a.likely_group)}»:"
        )
    else:
        lines.append("⚠️ <b>Внимание: часть замен, возможно, не для вашей группы.</b>")
        lines.append(
            f"Замены на <b>{a.weekday}, {a.date}</b> записаны на «{escape_html(a.stated_group)}», "
            f"но по расписанию они похожи на замены для «{escape_html(a.likely_group)}»:"
        )

    lines.append("")
    lines.extend(_format_row(r) for r in a.rows)

    if a.evidence:
        lines.append("")
        lines.append("<i>" + "; ".join(escape_html(e) for e in a.evidence) + ".</i>")

    lines.append("")
    lines.append("Ниже — оригинал файла замен, проверьте сами 👇")
    return "\n".join(lines)


async def send_zameny(message: Message) -> None:
    group = await get_user_group(message.chat.id)
    if not group:
        await message.answer("Сначала выберите группу: 👥 Моя группа")
        return

    blocks = await get_zameny()
    anomalies = await get_zameny_anomalies()
    lines: list[str] = []

    for block in blocks:
        rows = [r for r in block.rows if r.group == group]
        if not rows:
            continue
        lines.append(f"<b>{block.weekday}, {block.date}:</b>")
        lines.extend(_format_row(r) for r in rows)

    await message.answer(
        "\n".join(lines) if lines else f"Замен для группы <b>{escape_html(group)}</b> нет."
    )

    # Замена касается пользователя, если его группа — это либо указанное имя,
    # либо вероятно-правильное: так он узнаёт и когда замены для него записали
    # не туда, и когда показанные выше замены, возможно, не его.
    relevant = [a for a in anomalies if a.likely_group == group or a.stated_group == group]
    if not relevant:
        return

    for a in relevant:
        await message.answer(_format_anomaly(a, group))

    try:
        file_path = await get_zameny_file_path()
        await message.answer_document(BufferedInputFile(file_path.read_bytes(), filename="zameny.xlsx"))
    except Exception:
        logging.exception("Не удалось отправить файл замен")


@router.message(Command("zameny"))
@router.message(F.text == Button.ZAMENY)
async def handle_zameny(message: Message) -> None:
    await send_zameny(message)
