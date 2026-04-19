import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "lead-scraper by /u/unknown")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
AI_EVALUATION_ENABLED = os.getenv("AI_EVALUATION_ENABLED", "").casefold() in {
    "1",
    "true",
    "yes",
    "on",
}
MIN_LEAD_SCORE = int(os.getenv("MIN_LEAD_SCORE", "70"))
SUMMARY_INTERVAL_HOURS = float(os.getenv("SUMMARY_INTERVAL_HOURS", "3"))
SUMMARY_TOP_N = int(os.getenv("SUMMARY_TOP_N", "5"))
DEFAULT_LEAD_PREFERENCES = (
    "Recommend small paid web projects from free-contact sources worth replying to quickly. "
    "Prefer presentation websites, portfolios, landing pages, WordPress, simple CMS, "
    "booking systems, and clear client requests. Avoid e-shops, Shoptet, SEO-only work, "
    "graphics-only work, full-time jobs, and listings where contacting the client requires a paid credit or subscription."
)
LEAD_PREFERENCES = os.getenv("LEAD_PREFERENCES") or DEFAULT_LEAD_PREFERENCES

REDDIT_SUBREDDITS = ["czech", "Prague", "brno", "forhire"]

INCLUDE_KEYWORDS = [
    "web",
    "webové stránky",
    "webovka",
    "webovky",
    "portfolio",
    "prezentace",
    "prezentační web",
    "wordpress",
    "wp",
    "webař",
    "webaře",
    "webdesigner",
    "webdesignér",
    "landing page",
    "jednoduchý web",
    "osobní web",
    "tvorba webu",
    "tvorba stránek",
]

EXCLUDE_KEYWORDS = [
    "eshop",
    "e-shop",
    "shoptet",
    "seo only",
    "jen seo",
    "pouze seo",
    "grafik",
    "grafika",
]

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)

REQUEST_DELAY_SECONDS = 2.0
DB_PATH = "seen.db"
SNIPPET_LENGTH = 200
