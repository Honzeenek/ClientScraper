from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass

import requests

from config import AI_EVALUATION_ENABLED, OPENAI_API_KEY, OPENAI_MODEL
from scrapers.base import Post

log = logging.getLogger(__name__)

API_URL = "https://api.openai.com/v1/responses"


@dataclass
class LeadEvaluation:
    score: int
    verdict: str
    reason: str
    next_step: str


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
    next_step = "Reply quickly with a short offer and one relevant example."
    if verdict == "low":
        next_step = "Probably skip unless the title is unusually relevant."
    return LeadEvaluation(score=score, verdict=verdict, reason=reason, next_step=next_step)


def evaluate_lead(post: Post) -> LeadEvaluation:
    fallback = local_evaluate_lead(post)
    if not AI_EVALUATION_ENABLED or not OPENAI_API_KEY:
        return fallback
    try:
        return _openai_evaluate_lead(post, fallback)
    except Exception as exc:
        log.warning("AI evaluation failed for %s: %s", post.url, exc)
        return fallback


def _openai_evaluate_lead(post: Post, fallback: LeadEvaluation) -> LeadEvaluation:
    body = " ".join(post.body.split())[:2500]
    payload = {
        "model": OPENAI_MODEL,
        "instructions": (
            "Evaluate whether this Czech lead is worth pursuing for a solo web developer. "
            "Prefer small presentation websites, portfolio sites, landing pages, WordPress, "
            "simple CMS, and booking sites. Penalize e-shops, Shoptet, SEO-only work, "
            "graphics-only work, and full-time employment. Return concise JSON."
        ),
        "input": (
            f"Source: {post.source}\n"
            f"Title: {post.title}\n"
            f"Body: {body}\n"
            f"Local score: {fallback.score}\n"
            f"Local reason: {fallback.reason}"
        ),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "lead_evaluation",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "score": {"type": "integer"},
                        "verdict": {"type": "string", "enum": ["high", "medium", "low"]},
                        "reason": {"type": "string"},
                        "next_step": {"type": "string"},
                    },
                    "required": ["score", "verdict", "reason", "next_step"],
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
        timeout=30,
    )
    resp.raise_for_status()
    data = _extract_response_json(resp.json())
    score = max(0, min(100, int(data["score"])))
    verdict = data["verdict"] if data["verdict"] in {"high", "medium", "low"} else _verdict(score)
    return LeadEvaluation(
        score=score,
        verdict=verdict,
        reason=str(data["reason"])[:180],
        next_step=str(data["next_step"])[:180],
    )


def _extract_response_json(data: dict) -> dict:
    if data.get("output_text"):
        return json.loads(data["output_text"])
    for output in data.get("output", []):
        for content in output.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                return json.loads(content["text"])
    raise ValueError("missing response text")
