from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is not set in .env")
    return value


@dataclass(frozen=True)
class Config:
    bot_token: str


config = Config(bot_token=_require("BOT_TOKEN"))
