from __future__ import annotations

import logging
from datetime import datetime, timezone

import praw

from config import (
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_SUBREDDITS,
    REDDIT_USER_AGENT,
)
from scrapers.base import BaseScraper, Post

log = logging.getLogger(__name__)


class RedditScraper(BaseScraper):
    source_name = "reddit"

    def __init__(self) -> None:
        super().__init__()
        self.client = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
            check_for_async=False,
        )

    def fetch(self) -> list[Post]:
        if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
            log.warning("Reddit credentials missing, skipping")
            return []
        out: list[Post] = []
        for sub in REDDIT_SUBREDDITS:
            try:
                for submission in self.client.subreddit(sub).new(limit=50):
                    out.append(
                        Post(
                            id=f"reddit:{submission.id}",
                            title=submission.title or "",
                            body=submission.selftext or "",
                            url=f"https://www.reddit.com{submission.permalink}",
                            source=f"reddit/{sub}",
                            posted_at=datetime.fromtimestamp(
                                submission.created_utc, tz=timezone.utc
                            ),
                        )
                    )
            except Exception as exc:
                log.exception("Reddit fetch failed for r/%s: %s", sub, exc)
        return out
