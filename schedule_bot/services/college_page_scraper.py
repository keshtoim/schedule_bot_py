from __future__ import annotations

import re
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup


@dataclass
class CollegeLinks:
    schedule_url: str
    zameny_url: str


_SCHEDULE_TEXT_RE = re.compile(r"^Расписание учебных занятий", re.IGNORECASE)
_ZAMENY_TEXT_RE = re.compile(r"^Замен", re.IGNORECASE)


async def fetch_college_links(page_url: str) -> CollegeLinks:
    """Книги перезаливаются под новым именем при каждом изменении (URL медиа
    WordPress), поэтому статическую ссылку не закрепить. Вместо этого читаем
    *текст* ссылок на странице — он предсказуем: расписание очной формы
    начинается с «Расписание учебных занятий», замены — с «Замены». Заодно
    отсекается ссылка на заочное («ЗАОЧНОЙ») расписание, которое нам не нужно."""
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        res = await client.get(page_url)
        res.raise_for_status()

    soup = BeautifulSoup(res.text, "lxml")

    schedule_url: str | None = None
    zameny_url: str | None = None

    for a in soup.select('a[href$=".xlsx"], a[href$=".xls"]'):
        href = a.get("href")
        text = a.get_text().strip()
        if not href:
            continue
        if schedule_url is None and _SCHEDULE_TEXT_RE.match(text):
            schedule_url = href
        if zameny_url is None and _ZAMENY_TEXT_RE.match(text):
            zameny_url = href

    if not schedule_url:
        raise ValueError(f"Could not find schedule (.xlsx) link on {page_url}")
    if not zameny_url:
        raise ValueError(f"Could not find zameny (.xlsx) link on {page_url}")

    return CollegeLinks(schedule_url=schedule_url, zameny_url=zameny_url)
