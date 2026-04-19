from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Post, hash_id

log = logging.getLogger(__name__)

LISTING_URL = "https://www.poptavky.cz/poptavky/tvorba-webovych-stranek"


class PoptavkyScraper(BaseScraper):
    source_name = "poptavky.cz"

    def fetch(self) -> list[Post]:
        resp = self.get(LISTING_URL)
        if resp is None:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        out: list[Post] = []
        seen_urls: set[str] = set()
        for link in soup.select('a[href*="/poptavka/"]'):
            url = urljoin(LISTING_URL, link["href"])
            if url in seen_urls:
                continue
            seen_urls.add(url)
            item = None
            for parent in link.parents:
                classes = parent.get("class") or []
                if parent.name == "div" and "border-gray-200" in classes:
                    item = parent
                    break
            if item is None:
                item = link.parent
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
