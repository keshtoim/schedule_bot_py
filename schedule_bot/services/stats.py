"""Короткая статистика для владельца: сколько людей и какие группы популярнее."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

_TOP_N = 10


def format_stats(chats: Iterable[tuple[int, str]]) -> str:
    """`chats` — пары (chat_id, группа) из user_store.get_all_chats()."""
    groups = [g for _, g in chats]
    total = len(groups)
    if not total:
        return "📊 <b>Статистика</b>\n\nПока никто не выбрал группу."

    counts = Counter(groups)
    distinct = len(counts)
    # по убыванию количества, при равенстве — по алфавиту
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:_TOP_N]
    width = len(str(top[0][1]))

    lines = [
        "📊 <b>Статистика</b>",
        "",
        f"👤 Пользователей: <b>{total}</b>",
        f"👥 Групп задействовано: <b>{distinct}</b>",
        "",
        "<b>Самые частые группы:</b>",
    ]
    lines += [f"<code>{cnt:>{width}}</code>  {group}" for group, cnt in top]
    if distinct > _TOP_N:
        lines.append(f"<i>…и ещё {distinct - _TOP_N}</i>")
    return "\n".join(lines)
