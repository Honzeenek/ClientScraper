from __future__ import annotations

import hashlib
import logging
import time
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

from config import (
    EXCLUDE_KEYWORDS,
    INCLUDE_KEYWORDS,
    REQUEST_DELAY_SECONDS,
    USER_AGENT,
)

log = logging.getLogger(__name__)


@dataclass
class Post:
    id: str
    title: str
    body: str
    url: str
    source: str
    posted_at: datetime


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.casefold()


def matches_keywords(text: str) -> bool:
    normalized = _normalize(text)
    for kw in EXCLUDE_KEYWORDS:
        keyword = _normalize(kw)
        if keyword in {"grafik", "grafika"}:
            if keyword in normalized and not any(
                term in normalized for term in ["web", "wordpress", "webdesign"]
            ):
                return False
            continue
        if keyword in normalized:
            return False
    return any(_normalize(kw) in normalized for kw in INCLUDE_KEYWORDS)


def hash_id(source: str, url: str) -> str:
    return hashlib.sha1(f"{source}|{url}".encode("utf-8")).hexdigest()


class BaseScraper(ABC):
    source_name: str = "base"

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self._robots_cache: dict[str, RobotFileParser] = {}

    @abstractmethod
    def fetch(self) -> list[Post]:
        ...

    def filter(self, posts: list[Post]) -> list[Post]:
        return [p for p in posts if matches_keywords(f"{p.title}\n{p.body}")]

    def can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        rp = self._robots_cache.get(base)
        if rp is None:
            rp = RobotFileParser()
            rp.set_url(f"{base}/robots.txt")
            try:
                rp.read()
            except Exception as exc:
                log.warning("robots.txt fetch failed for %s: %s", base, exc)
                self._robots_cache[base] = rp
                return True
            self._robots_cache[base] = rp
        try:
            return rp.can_fetch(USER_AGENT, url)
        except Exception:
            return True

    def get(self, url: str, **kwargs) -> requests.Response | None:
        if not self.can_fetch(url):
            log.info("robots.txt disallows %s", url)
            return None
        time.sleep(REQUEST_DELAY_SECONDS)
        try:
            resp = self.session.get(url, timeout=20, **kwargs)
            resp.raise_for_status()
        except requests.RequestException as exc:
            log.warning("Request failed for %s: %s", url, exc)
            return None
        return resp
