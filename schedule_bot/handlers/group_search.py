"""Поиск группы по свободному тексту.

Роутер подключается последним — все кнопки меню, команды и FSM-диалоги
(багрепорт) забирают сообщение раньше. Сюда доходит только текст, который
никто больше не разобрал: считаем его попыткой найти группу по названию.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import Message

from ..keyboards import build_group_search_results
from ..services.schedule_service import get_schedule
from ..utils.html import escape_html

router = Router(name="group_search")
log = logging.getLogger(__name__)

# Сколько совпадений показываем кнопками, прежде чем просить уточнить запрос.
MAX_RESULTS = 24

# Латинская клавиша → кириллическая буква на том же месте (ЙЦУКЕН).
# «забыл переключить раскладку»: 23-bcg-1 → 23-исп-1.
_QWERTY_TO_RU = str.maketrans(
    {
        "q": "й", "w": "ц", "e": "у", "r": "к", "t": "е", "y": "н", "u": "г",
        "i": "ш", "o": "щ", "p": "з", "[": "х", "]": "ъ",
        "a": "ф", "s": "ы", "d": "в", "f": "а", "g": "п", "h": "р", "j": "о",
        "k": "л", "l": "д", ";": "ж", "'": "э",
        "z": "я", "x": "ч", "c": "с", "v": "м", "b": "и", "n": "т", "m": "ь",
        ",": "б", ".": "ю",
    }
)

# Латинские двойники кириллических букв (23-иcп-1 с латинской «c»).
_LATIN_LOOKALIKES = str.maketrans(
    {
        "a": "а", "e": "е", "o": "о", "c": "с", "p": "р", "x": "х",
        "y": "у", "k": "к", "m": "м", "h": "н", "t": "т", "b": "в",
    }
)


def _norm(s: str) -> str:
    """Только буквы и цифры, в нижнем регистре — без дефисов, пробелов, точек."""
    return "".join(ch for ch in s.lower() if ch.isalnum())


def match_groups(query: str, groups: list[str], *, limit: int = MAX_RESULTS) -> list[str]:
    """Группы, чьё нормализованное имя содержит нормализованный запрос.
    Игнорирует регистр, дефисы и пробелы; дополнительно пробует вариант
    «набрано в латинской раскладке» и латинские двойники букв. Запрос короче
    двух значащих символов совпадений не даёт. Результат отсортирован."""
    base = _norm(query)
    if len(base) < 2:
        return []

    variants = {
        base,
        _norm(query.translate(_LATIN_LOOKALIKES)),
        _norm(query.translate(_QWERTY_TO_RU)),
    }
    hits = [g for g in groups if any(v and v in _norm(g) for v in variants)]
    return sorted(hits)[:limit]


@router.message(StateFilter(None), F.text, ~F.text.startswith("/"))
async def handle_group_search(message: Message) -> None:
    query = message.text.strip()
    if len(_norm(query)) < 2:
        await message.answer(
            "Напиши хотя бы пару символов из названия группы — например «исп» или «23»."
        )
        return

    schedule = await get_schedule()
    matches = match_groups(query, schedule.groups)

    if not matches:
        await message.answer(
            "Не нашёл такую группу. Проверь написание или выбери из списка: "
            "⚙️ Настройки → 👥 Группа."
        )
        return

    log.info("Поиск группы: chat=%s «%s» → %d", message.chat.id, query, len(matches))
    head = (
        f"Нашёл по запросу «{escape_html(query)}» — выбери свою:"
        if len(matches) > 1
        else "Нашёл — это она?"
    )
    if len(matches) == MAX_RESULTS:
        head += f"\n(показал первые {MAX_RESULTS}, уточни запрос, если нужной нет)"
    await message.answer(head, reply_markup=build_group_search_results(matches))
