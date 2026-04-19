from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass

import requests

from config import (
    AI_EVALUATION_ENABLED,
    LEAD_PREFERENCES,
    MIN_LEAD_SCORE,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    SUMMARY_TOP_N,
)
from scrapers.base import Post

log = logging.getLogger(__name__)

API_URL = "https://api.openai.com/v1/responses"


@dataclass
class LeadEvaluation:
    score: int
    verdict: str
    reason: str
    next_step: str


@dataclass
class DigestItem:
    id: str
    title: str
    source: str
    url: str
    score: int
    reason: str
    next_step: str


@dataclass
class LeadDigest:
    summary: str
    items: list[DigestItem]


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.casefold()


def _contains_any(text: str, values: list[str]) -> bool:
    return any(_normalize(value) in text for value in values)


def _money_values(text: str) -> list[int]:
    values = []
    for raw in re.findall(r"(\d[\d\s]{2,})\s*(?:kč|kc|korun|czk)", text):
        digits = re.sub(r"\D", "", raw)
        if digits:
            values.append(int(digits))
    return values


def _verdict(score: int) -> str:
    if score >= 75:
        return "high"
    if score >= 55:
        return "medium"
    return "low"


def local_evaluate_lead(post: Post) -> LeadEvaluation:
    text = _normalize(f"{post.title}\n{post.body}")
    score = 35
    reasons = []

    if _contains_any(
        text,
        [
            "tvorba webu",
            "tvorbu webu",
            "vyrobu webu",
            "vytvoreni webu",
            "webove stranky",
            "webovych stranek",
            "prezentacni web",
            "landing page",
            "wordpress",
        ],
    ):
        score += 30
        reasons.append("clear web build intent")
    elif _contains_any(text, ["web", "portfolio", "prezentace", "osobni web"]):
        score += 15
        reasons.append("relevant web keyword")

    if _contains_any(text, ["jednoduchy web", "webova prezentace", "rezervacni system"]):
        score += 10
        reasons.append("fits small site work")

    if _contains_any(text, ["ico", "iČo", "freelance", "extern", "dodavatel", "nabidnete"]):
        score += 10
        reasons.append("likely contractor friendly")

    amounts = _money_values(text)
    if amounts:
        best_amount = max(amounts)
        if best_amount >= 30000:
            score += 20
            reasons.append("solid stated budget")
        elif best_amount >= 8000:
            score += 10
            reasons.append("some stated budget")

    if _contains_any(text, ["urgentne", "urgentně", "co nejdrive", "co nejdříve"]):
        score += 8
        reasons.append("time-sensitive request")

    if _contains_any(text, ["eshop", "e-shop", "shoptet"]):
        score -= 35
        reasons.append("includes e-shop scope")

    if _contains_any(text, ["seo only", "jen seo", "pouze seo"]):
        score -= 35
        reasons.append("SEO-only request")

    if _contains_any(text, ["grafik", "grafika"]) and not _contains_any(text, ["web", "wordpress"]):
        score -= 25
        reasons.append("graphics-only signal")

    if post.source == "jobs.cz":
        score -= 15
        reasons.append("job-board listing")

    if _contains_any(text, ["full time", "hpp", "zamestnanec", "zaměstnanec"]):
        score -= 25
        reasons.append("employment signal")

    score = max(0, min(100, score))
    verdict = _verdict(score)
    reason = ", ".join(reasons[:3]) if reasons else "basic keyword match"
    next_step = "Open it and reply with one relevant example if the scope still fits."
    if verdict == "low":
        next_step = "Skip unless the title is unusually relevant."
    return LeadEvaluation(score=score, verdict=verdict, reason=reason, next_step=next_step)


def evaluate_lead(post: Post) -> LeadEvaluation:
    return local_evaluate_lead(post)


def summarize_candidates(candidates: list) -> LeadDigest:
    fallback = local_summarize_candidates(candidates)
    if not AI_EVALUATION_ENABLED or not OPENAI_API_KEY or not candidates:
        return fallback
    try:
        return _openai_summarize_candidates(candidates, fallback)
    except Exception as exc:
        log.warning("OpenAI summary failed: %s", exc)
        return fallback


def local_summarize_candidates(candidates: list) -> LeadDigest:
    ranked = sorted(candidates, key=lambda item: item.local_score, reverse=True)
    items = [
        DigestItem(
            id=item.id,
            title=item.title,
            source=item.source,
            url=item.url,
            score=item.local_score,
            reason=item.local_reason,
            next_step="Open and reply if the budget and scope still fit.",
        )
        for item in ranked
        if item.local_score >= MIN_LEAD_SCORE
    ][:SUMMARY_TOP_N]
    if items:
        summary = f"{len(candidates)} new matches collected. Top {len(items)} look worth checking."
    else:
        summary = f"{len(candidates)} new matches collected, but none reached the score threshold."
    return LeadDigest(summary=summary, items=items)


def _openai_summarize_candidates(candidates: list, fallback: LeadDigest) -> LeadDigest:
    ranked = sorted(candidates, key=lambda item: item.local_score, reverse=True)[:25]
    allowed_ids = {item.id for item in ranked}
    candidate_text = "\n\n".join(
        (
            f"ID: {item.id}\n"
            f"Source: {item.source}\n"
            f"Local score: {item.local_score}\n"
            f"Local reason: {item.local_reason}\n"
            f"Title: {item.title}\n"
            f"Body: {' '.join(item.body.split())[:900]}\n"
            f"URL: {item.url}"
        )
        for item in ranked
    )
    payload = {
        "model": OPENAI_MODEL,
        "instructions": (
            "You evaluate batches of Czech web development leads for a solo developer. "
            "The user wants fewer notifications and only wants opportunities worth checking. "
            f"User preferences: {LEAD_PREFERENCES} "
            "Recommend only leads from sources where contacting the client is free or normal job application is free. "
            "Pick at most the strongest leads. Return JSON."
        ),
        "input": (
            f"Minimum score to recommend: {MIN_LEAD_SCORE}\n"
            f"Maximum recommended items: {SUMMARY_TOP_N}\n"
            f"Candidates:\n{candidate_text}"
        ),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "lead_digest",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "score": {"type": "integer"},
                                    "reason": {"type": "string"},
                                    "next_step": {"type": "string"},
                                },
                                "required": ["id", "score", "reason", "next_step"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["summary", "items"],
                    "additionalProperties": False,
                },
            }
        },
    }
    resp = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=45,
    )
    resp.raise_for_status()
    data = _extract_response_json(resp.json())
    by_id = {item.id: item for item in ranked}
    items = []
    for raw in data.get("items", []):
        item_id = raw.get("id")
        if item_id not in allowed_ids:
            continue
        candidate = by_id[item_id]
        score = max(0, min(100, int(raw.get("score", candidate.local_score))))
        if score < MIN_LEAD_SCORE:
            continue
        items.append(
            DigestItem(
                id=candidate.id,
                title=candidate.title,
                source=candidate.source,
                url=candidate.url,
                score=score,
                reason=str(raw.get("reason", candidate.local_reason))[:180],
                next_step=str(raw.get("next_step", "Open and review."))[:180],
            )
        )
        if len(items) >= SUMMARY_TOP_N:
            break
    if not items and fallback.items:
        return fallback
    return LeadDigest(summary=str(data.get("summary", fallback.summary))[:240], items=items)


def _extract_response_json(data: dict) -> dict:
    if data.get("output_text"):
        return json.loads(data["output_text"])
    for output in data.get("output", []):
        for content in output.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                return json.loads(content["text"])
    raise ValueError("missing response text")
