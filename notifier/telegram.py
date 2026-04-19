import logging

import requests

from config import SNIPPET_LENGTH, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from evaluator import LeadDigest, LeadEvaluation
from scrapers.base import Post

log = logging.getLogger(__name__)

API_URL = "https://api.telegram.org/bot{token}/sendMessage"
MARKDOWN_ESCAPE = str.maketrans({c: f"\\{c}" for c in "_*[]()~`>#+-=|{}.!"})


def _escape(text: str) -> str:
    return text.translate(MARKDOWN_ESCAPE)


def _truncate(text: str, limit: int = SNIPPET_LENGTH) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def send_lead(post: Post, evaluation: LeadEvaluation | None = None) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("Telegram not configured, skipping notification for %s", post.url)
        return

    snippet = _truncate(post.body) if post.body else ""
    lines = [
        f"*{_escape(post.title)}*",
        f"_{_escape(post.source)}_ · {_escape(post.posted_at.strftime('%Y-%m-%d %H:%M'))}",
    ]
    if evaluation:
        lines.append(
            f"*Worth it:* {_escape(str(evaluation.score))}/100 · {_escape(evaluation.verdict.title())}"
        )
        lines.append(f"*Why:* {_escape(evaluation.reason)}")
        lines.append(f"*Next:* {_escape(evaluation.next_step)}")
    if snippet:
        lines.append(_escape(snippet))
    lines.append(f"[Open post]({post.url})")
    body = "\n".join(lines)

    resp = requests.post(
        API_URL.format(token=TELEGRAM_BOT_TOKEN),
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": body,
            "parse_mode": "MarkdownV2",
            "disable_web_page_preview": False,
        },
        timeout=15,
    )
    if not resp.ok:
        log.error("Telegram send failed: %s %s", resp.status_code, resp.text)
        resp.raise_for_status()


def send_digest(digest: LeadDigest) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("Telegram not configured, skipping digest")
        return

    lines = [
        "*Lead digest*",
        _escape(digest.summary),
    ]
    if digest.items:
        for index, item in enumerate(digest.items, start=1):
            lines.extend(
                [
                    "",
                    f"*{index}\\. {_escape(item.title)}*",
                    f"{_escape(item.source)} · {_escape(str(item.score))}/100",
                    f"{_escape(item.reason)}",
                    f"{_escape(item.next_step)}",
                    f"[Open post]({item.url})",
                ]
            )
    else:
        lines.append("Nothing looks worth chasing in this batch\\.")
    body = "\n".join(lines)

    resp = requests.post(
        API_URL.format(token=TELEGRAM_BOT_TOKEN),
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": body,
            "parse_mode": "MarkdownV2",
            "disable_web_page_preview": True,
        },
        timeout=15,
    )
    if not resp.ok:
        log.error("Telegram digest failed: %s %s", resp.status_code, resp.text)
        resp.raise_for_status()
