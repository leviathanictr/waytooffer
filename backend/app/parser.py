from __future__ import annotations

import requests
from bs4 import BeautifulSoup


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

_FALLBACK = {"title": "Вакансия", "text": "Не удалось загрузить описание вакансии"}


def parse_vacancy(url: str) -> dict:
    """
    Fetch the vacancy page at *url* and extract its title and description text.

    Supports hh.ru natively; falls back to generic body-text extraction for
    other sites.  On any network or parsing error returns a safe fallback dict.

    Returns:
        {"title": str, "text": str}
    """
    try:
        response = requests.get(url, headers=_HEADERS, timeout=10)
        response.raise_for_status()
    except Exception:
        return _FALLBACK.copy()

    try:
        soup = BeautifulSoup(response.text, "html.parser")

        # ------------------------------------------------------------------ #
        # hh.ru                                                                #
        # ------------------------------------------------------------------ #
        if "hh.ru" in url:
            title_tag = soup.find("h1", {"data-qa": "vacancy-title"})
            if title_tag is None:
                title_tag = soup.find("h1")
            title = title_tag.get_text(strip=True) if title_tag else "Вакансия"

            desc_tag = soup.find("div", {"data-qa": "vacancy-description"})
            if desc_tag is None:
                # Some hh.ru pages use a different selector
                desc_tag = soup.find("div", class_="vacancy-description")
            if desc_tag is None:
                desc_tag = soup.find("div", {"class": lambda c: c and "description" in c})

            if desc_tag:
                text = desc_tag.get_text(separator="\n", strip=True)
            else:
                # Last-resort: strip all tags from body
                body = soup.find("body")
                text = body.get_text(separator="\n", strip=True) if body else ""

            return {"title": title[:200], "text": text[:5000]}

        # ------------------------------------------------------------------ #
        # Generic fallback                                                     #
        # ------------------------------------------------------------------ #
        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else "Вакансия"

        # Remove scripts, styles, nav, footer to get clean body text
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        body = soup.find("body")
        raw_text = body.get_text(separator="\n", strip=True) if body else ""

        # Collapse blank lines and truncate
        lines = [line for line in raw_text.splitlines() if line.strip()]
        text = "\n".join(lines)[:3000]

        return {"title": title[:200], "text": text}

    except Exception:
        return _FALLBACK.copy()
