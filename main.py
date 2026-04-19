from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, SUMMARY_INTERVAL_HOURS
from evaluator import local_evaluate_lead, summarize_candidates
from notifier.telegram import send_digest
from scrapers.base import BaseScraper
from scrapers.jobs_cz import JobsCzScraper
from scrapers.poptavky import PoptavkyScraper
from scrapers.reddit import RedditScraper
from scrapers.workero import WorkeroScraper
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
            WorkeroScraper(),
            PoptavkyScraper(),
            JobsCzScraper(),
        ]
    )
    return scrapers


def run_scraper(scraper: BaseScraper, store: SeenStore) -> tuple[int, int, int]:
    fetched = scraper.fetch()
    matched = scraper.filter(fetched)
    collected = 0
    for post in matched:
        if store.is_seen(post.id):
            continue
        evaluation = local_evaluate_lead(post)
        store.add_candidate(post, evaluation)
        store.mark_seen(post.id, post.source)
        collected += 1
    return len(fetched), len(matched), collected


def send_summary_if_due(store: SeenStore) -> None:
    now = datetime.now(timezone.utc)
    last_summary_at = store.get_meta_datetime("last_summary_at")
    if last_summary_at is None:
        store.set_meta_datetime("last_summary_at", now)
        log.info("summary: first run initialized")
        return
    if now - last_summary_at < timedelta(hours=SUMMARY_INTERVAL_HOURS):
        log.info("summary: not due")
        return
    candidates = store.get_unreported_candidates()
    if not candidates:
        store.set_meta_datetime("last_summary_at", now)
        log.info("summary: due but no new candidates")
        return
    digest = summarize_candidates(candidates)
    try:
        if digest.items:
            send_digest(digest)
    except Exception as exc:
        log.exception("summary notification failed: %s", exc)
        return
    store.mark_candidates_reported([candidate.id for candidate in candidates])
    store.set_meta_datetime("last_summary_at", now)
    log.info(
        "summary: candidates=%d recommended=%d",
        len(candidates),
        len(digest.items),
    )


def main() -> None:
    store = SeenStore()
    try:
        for scraper in build_scrapers():
            name = scraper.source_name
            try:
                fetched, matched, collected = run_scraper(scraper, store)
                log.info(
                    "%s: fetched=%d matched=%d collected=%d",
                    name, fetched, matched, collected,
                )
            except Exception as exc:
                log.exception("%s failed: %s", name, exc)
        send_summary_if_due(store)
    finally:
        store.close()


if __name__ == "__main__":
    main()
