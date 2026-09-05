from __future__ import annotations

import socket

import httpx
from aiogram.exceptions import TelegramNetworkError

_NETWORK_ERRORS: tuple[type[BaseException], ...] = (
    httpx.TransportError,
    socket.gaierror,
    ConnectionError,
    TelegramNetworkError,
    TimeoutError,
)

_HINTS: list[tuple[type[BaseException], str]] = [
    (httpx.ConnectTimeout, "сервер не отвечает (тайм-аут) — похоже, нет доступа к Telegram (нужен VPN?)"),
    (httpx.ReadTimeout, "сервер не отвечает (тайм-аут)"),
    (socket.gaierror, "не удалось определить адрес сервера (проблема с DNS)"),
    (ConnectionResetError, "соединение оборвалось на середине запроса"),
    (ConnectionRefusedError, "сервер отказал в соединении"),
    (httpx.ConnectError, "не удалось подключиться к серверу"),
    (TelegramNetworkError, "нет связи с Telegram (сеть или блокировка)"),
]


def is_network_error(err: BaseException) -> bool:
    """True, если ошибка (или её причина) — сетевой сбой, а не баг в коде."""
    for exc in (err, err.__cause__, err.__context__):
        if exc is not None and isinstance(exc, _NETWORK_ERRORS):
            return True
    return False


def describe_error(err: BaseException) -> str:
    """Превращает пойманную ошибку (часто обёрнутый сетевой сбой) в одну
    читаемую строку."""
    for exc in (err, err.__cause__, err.__context__):
        if exc is None:
            continue
        for cls, hint in _HINTS:
            if isinstance(exc, cls):
                return f"{hint} ({type(exc).__name__})"

    cause = err.__cause__
    if cause is not None and str(cause):
        return str(cause)
    return str(err) or type(err).__name__
