import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message

from ..keyboards import Button
from ..services.schedule_service import get_zameny, get_zameny_anomalies, get_zameny_file_path
from ..services.zameny_view import format_anomaly_alert, format_zameny_row
from ..utils.html import escape_html
from .common import resolve_group, thinking

router = Router(name="zameny")
log = logging.getLogger(__name__)


async def send_zameny(message: Message) -> None:
    group = await resolve_group(message)
    if not group:
        return

    async with thinking(message):
        blocks = await get_zameny()
        anomalies = await get_zameny_anomalies()
        lines: list[str] = []
        days = 0

        for block in blocks:
            rows = [r for r in block.rows if r.group == group]
            if not rows:
                continue
            days += 1
            lines.append(f"<b>{block.weekday}, {block.date}:</b>")
            lines.extend(format_zameny_row(r) for r in rows)

        log.info("Замены для %s: %d дн. с заменами", group, days)
        await message.answer(
            "\n".join(lines) if lines else f"Замен для группы <b>{escape_html(group)}</b> нет."
        )

    # Замена касается пользователя, если его группа — это либо указанное имя,
    # либо вероятно-правильное: так он узнаёт и когда замены для него записали
    # не туда, и когда показанные выше замены, возможно, не его.
    relevant = [a for a in anomalies if a.likely_group == group or a.stated_group == group]
    if not relevant:
        return

    log.warning("Замены для %s: показываю %d предупреждение(й) об опечатке в группе", group, len(relevant))
    for a in relevant:
        await message.answer(format_anomaly_alert(a, group))

    try:
        file_path = await get_zameny_file_path()
        await message.answer_document(BufferedInputFile(file_path.read_bytes(), filename="zameny.xlsx"))
    except Exception:
        log.exception("Не удалось отправить файл замен группе %s", group)


@router.message(Command("zameny"))
@router.message(F.text == Button.ZAMENY)
async def handle_zameny(message: Message) -> None:
    await send_zameny(message)
