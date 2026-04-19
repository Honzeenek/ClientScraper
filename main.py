from __future__ import annotations

import logging

from config import MIN_LEAD_SCORE, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET
from evaluator import evaluate_lead
from notifier.telegram import send_lead
from scrapers.base import BaseScraper
from scrapers.hyperpoptavka import HyperpoptavkaScraper
from scrapers.jobs_cz import JobsCzScraper
from scrapers.nejremeslnici import NejremeslniciScraper
from scrapers.poptavka import PoptavkaScraper
from scrapers.reddit import RedditScraper
from storage.seen import SeenStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("main")


def build_scrapers() -> list[BaseScraper]:
    scrapers: list[BaseScraper] = []
    if REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET:
        scrapers.append(RedditScraper())
    scrapers.extend(
        [
            PoptavkaScraper(),
            HyperpoptavkaScraper(),
            NejremeslniciScraper(),
            JobsCzScraper(),
        ]
    )
    return scrapers


def run_scraper(scraper: BaseScraper, store: SeenStore) -> tuple[int, int, int, int]:
    fetched = scraper.fetch()
    matched = scraper.filter(fetched)
    sent = 0
    skipped = 0
    for post in matched:
        if store.is_seen(post.id):
            continue
        evaluation = evaluate_lead(post)
        if evaluation.score < MIN_LEAD_SCORE:
            store.mark_seen(post.id, post.source)
            skipped += 1
            continue
        try:
            send_lead(post, evaluation)
        except Exception as exc:
            log.exception("Notify failed for %s: %s", post.url, exc)
            continue
        store.mark_seen(post.id, post.source)
        sent += 1
    return len(fetched), len(matched), sent, skipped


def main() -> None:
    store = SeenStore()
    try:
        for scraper in build_scrapers():
            name = scraper.source_name
            try:
                fetched, matched, sent, skipped = run_scraper(scraper, store)
                log.info(
                    "%s: fetched=%d matched=%d notified=%d skipped=%d",
                    name, fetched, matched, sent, skipped,
                )
            except Exception as exc:
                log.exception("%s failed: %s", name, exc)
    finally:
        store.close()


if __name__ == "__main__":
    main()
