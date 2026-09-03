from __future__ import annotations

import asyncio

import httpx

from ..config import config

_MAX_ATTEMPTS = 3
_RETRY_DELAY_SEC = 0.5


async def send_rich_message_html(chat_id: int, html: str) -> None:
    """sendRichMessage (Bot API 10.1) — отправляет структурированный контент
    (заголовки, абзацы, разделители, таблицы) прямо в чат, без внешней ссылки.
    Метода нет в aiogram, поэтому дёргаем API напрямую."""
    payload = {"chat_id": chat_id, "rich_message": {"html": html}}
    last_error: Exception | None = None

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                res = await client.post(
                    f"https://api.telegram.org/bot{config.bot_token}/sendRichMessage",
                    json=payload,
                )
            data = res.json()
            if not data.get("ok"):
                raise RuntimeError(f"sendRichMessage failed: {data.get('description') or res.status_code}")
            return
        except Exception as err:  # noqa: BLE001
            last_error = err
            if attempt < _MAX_ATTEMPTS:
                await asyncio.sleep(_RETRY_DELAY_SEC * attempt)

    assert last_error is not None
    raise last_error
