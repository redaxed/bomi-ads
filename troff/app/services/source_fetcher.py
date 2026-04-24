from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


class SourceFetchError(RuntimeError):
    pass


@dataclass
class SourceSnapshot:
    url: str
    title: str
    summary: str
    extracted_text: str


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def fetch_source_snapshot(url: str, timeout_seconds: int = 20, max_chars: int = 20000) -> SourceSnapshot:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise SourceFetchError("Only http/https URLs are supported.")

    headers = {
        "User-Agent": "troff-source-fetcher/2.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    response = requests.get(url, headers=headers, timeout=timeout_seconds)
    if response.status_code >= 400:
        raise SourceFetchError(f"Source fetch failed with HTTP {response.status_code}.")

    content_type = (response.headers.get("content-type") or "").lower()
    raw_text = response.text

    title = url
    extracted_text = ""
    if "html" in content_type or "<html" in raw_text.lower():
        soup = BeautifulSoup(raw_text, "html.parser")
        if soup.title and soup.title.string:
            title = _normalize_whitespace(soup.title.string)

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        extracted_text = _normalize_whitespace(soup.get_text(" "))
    else:
        extracted_text = _normalize_whitespace(raw_text)

    extracted_text = extracted_text[:max_chars]
    if len(extracted_text) < 80:
        raise SourceFetchError("Source content is too short to generate a useful rewrite.")

    summary = extracted_text[:1200]
    return SourceSnapshot(
        url=url,
        title=title[:400],
        summary=summary,
        extracted_text=extracted_text,
    )
