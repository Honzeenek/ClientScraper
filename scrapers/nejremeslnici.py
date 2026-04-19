from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Post, hash_id

log = logging.getLogger(__name__)

LISTING_URL = "https://www.nejremeslnici.cz/poptavky/tvorba-www-stranek"


class NejremeslniciScraper(BaseScraper):
    source_name = "nejremeslnici.cz"

    def fetch(self) -> list[Post]:
        resp = self.get(LISTING_URL)
        if resp is None:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        out: list[Post] = []
        for item in soup.select("article, li.demand, div.demand, div.job-offer, div.item"):
            link = item.find("a", href=True)
            if not link:
                continue
            url = urljoin(LISTING_URL, link["href"])
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
