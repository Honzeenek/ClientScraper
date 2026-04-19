from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Post, hash_id

log = logging.getLogger(__name__)

LISTING_URLS = [
    "http://workero.cz/projekty",
    "http://workero.cz/projects",
    "http://workero.cz",
]


class WorkeroScraper(BaseScraper):
    source_name = "workero.cz"

    def fetch(self) -> list[Post]:
        out: list[Post] = []
        seen_urls: set[str] = set()
        for listing_url in LISTING_URLS:
            resp = self.get(listing_url)
            if resp is None:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            title_text = soup.title.get_text(" ", strip=True) if soup.title else ""
            if title_text == "Default index":
                continue
            for item in soup.select("article, li, div[class*=project], div[class*=job]"):
                link = item.find("a", href=True)
                if not link:
                    continue
                url = urljoin(listing_url, link["href"])
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                title = (link.get_text() or "").strip()
                body = (item.get_text(" ", strip=True) or "")[:1000]
                if not title:
                    continue
                out.append(
                    Post(
                        id=hash_id(self.source_name, url),
                        title=title,
                        body=body,
                        url=url,
                        source=self.source_name,
                        posted_at=datetime.now(timezone.utc),
                    )
                )
        return out
