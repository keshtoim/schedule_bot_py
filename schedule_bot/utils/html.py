def escape_html(text: str) -> str:
    """Экранирует текст, который попадёт в сообщение Telegram с parse_mode="HTML"."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
