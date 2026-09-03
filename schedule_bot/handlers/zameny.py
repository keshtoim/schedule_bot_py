from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from ..keyboards import Button
from ..services.schedule_service import get_zameny
from ..store.user_store import get_user_group
from ..utils.html import escape_html

router = Router(name="zameny")


async def send_zameny(message: Message) -> None:
    group = await get_user_group(message.chat.id)
    if not group:
        await message.answer("Сначала выберите группу: 👥 Моя группа")
        return

    blocks = await get_zameny()
    lines: list[str] = []

    for block in blocks:
        rows = [r for r in block.rows if r.group == group]
        if not rows:
            continue

        lines.append(f"<b>{block.weekday}, {block.date}:</b>")
        for row in rows:
            is_cancelled = row.replacement.strip().lower() == "нет"
            room = f" {escape_html(row.room)}" if row.room else ""
            if is_cancelled:
                lines.append(
                    f"  Пара {row.pair_number}: ❌ <i>отменено (было: {escape_html(row.instead_of)})</i>"
                )
            else:
                lines.append(
                    f"  Пара {row.pair_number}: 🔁 <i>«{escape_html(row.instead_of)}» → "
                    f"«{escape_html(row.replacement)}»{room}</i>"
                )

    text = "\n".join(lines) if lines else f"Замен для группы <b>{escape_html(group)}</b> нет."
    await message.answer(text)


@router.message(Command("zameny"))
@router.message(F.text == Button.ZAMENY)
async def handle_zameny(message: Message) -> None:
    await send_zameny(message)
