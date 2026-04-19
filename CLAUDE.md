# Lead Scraper Bot

Scrapes free-contact Czech freelance/job sources for web dev leads and sends digest notifications to Telegram.

## Goal

Get a ranked digest every few hours when someone posts a request for web dev work (portfolio sites, small presentation webs, custom websites, etc.) on Czech platforms. Replace manual checking of these boards without using paid-contact lead marketplaces.

## Sources to Scrape

| Source | Method | Priority | Notes |
|---|---|---|---|
| Reddit (r/czech, r/Prague, r/Jobs4Bitcoins, r/forhire) | Official API (PRAW) | High | Use when API credentials work |
| Workero.cz | HTML scrape (BeautifulSoup) | High | Free-contact source if public project listings are live |
| Jobs.cz (freelance / ICO / web query) | HTML scrape | Medium | Free application flow, mostly employment-like |
| Na volné noze | Not scraped | Low | Directory/community, not a public project feed |

**Do NOT scrape paid-contact lead marketplaces.** Avoid sources where viewing or contacting the client requires paid credits or a subscription.

**Do NOT scrape Facebook groups.** FB blocks scrapers, requires login, violates ToS, accounts get banned. Not worth it.

## Keyword Filter

Match posts containing any of (case-insensitive, also check Czech diacritics variants):

- `web`, `webové stránky`, `webovka`, `webovky`
- `portfolio`, `prezentace`, `prezentační web`
- `webař`, `webaře`, `webdesigner`, `webdesignér`
- `landing page`, `jednoduchý web`, `osobní web`
- `tvorba webu`, `tvorba stránek`

**Exclude** (negative filter, skip post if matches):
- `eshop`, `e-shop`, `shoptet` (user is NOT doing e-shops right now)
- `wordpress`, `wp` (user is NOT doing WordPress work)
- `SEO only`, `jen SEO`, `pouze SEO`
- `grafik`, `grafika` (unless also mentions web)

## Output / Notification

- **Telegram bot** (free). Send one ranked digest every few hours with:
  - Best lead titles
  - Source platform
  - Score and short reason
  - Suggested next step
  - Direct link to post
- Format as markdown for clickable links in Telegram.

## Architecture

```
lead-scraper/
├── main.py               # Entry point, orchestrates all scrapers
├── scrapers/
│   ├── __init__.py
│   ├── base.py           # BaseScraper abstract class (fetch, parse, filter)
│   ├── reddit.py
│   ├── workero.py
│   └── jobs_cz.py
├── notifier/
│   ├── __init__.py
│   └── telegram.py       # send_message(text) using Bot API
├── storage/
│   ├── __init__.py
│   └── seen.py           # SQLite-based dedup, stores post IDs + timestamps
├── config.py             # Keywords, sources, env var loading
├── .env.example          # TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, REDDIT_*
├── requirements.txt
├── README.md
└── .github/workflows/
    └── scrape.yml        # Run every 30 min via GitHub Actions (free)
```

## Key Implementation Details

### Deduplication
- SQLite DB with table `seen_posts(id TEXT PRIMARY KEY, source TEXT, seen_at TIMESTAMP)`
- Post ID = hash of `source + url` or native ID from source
- Before notifying: check if ID exists, skip if yes, insert if no
- GitHub Actions has no persistent storage, so either:
  - Commit the DB back to the repo after each run (simple, works for low volume)
  - Use a gist, or Upstash Redis free tier, or Supabase free tier
  - **Recommended**: commit `seen.db` back to repo, volume will be small

### BaseScraper interface
```python
class BaseScraper(ABC):
    source_name: str

    @abstractmethod
    def fetch(self) -> list[Post]:
        """Fetch recent posts from the source."""

    def filter(self, posts: list[Post]) -> list[Post]:
        """Apply keyword filter from config."""

@dataclass
class Post:
    id: str
    title: str
    body: str
    url: str
    source: str
    posted_at: datetime
```

### Reddit
- Use PRAW library
- Create app at https://www.reddit.com/prefs/apps (script type)
- Subreddits: `czech`, `Prague`, `brno`, `forhire`, `slevomat` (check which have actual volume)
- Fetch `.new(limit=50)` from each, filter by keywords

### Workero.cz
- Check `/robots.txt` first, respect it
- Look for RSS feed first (`/rss`, `/feed`, view page source for `<link rel="alternate">`)
- If no RSS: fetch the public project listing page, parse with BeautifulSoup
- Set realistic User-Agent header
- Rate limit: 1 request per 2 seconds minimum, never hammer

### Jobs.cz
- Filter for freelance / ICO / brigáda listings
- Look for official API first before scraping

### Telegram notifier
- Create bot via @BotFather, get token
- Send `/start` to your bot, then get chat ID via `https://api.telegram.org/bot<TOKEN>/getUpdates`
- `sendMessage` endpoint with `parse_mode=Markdown`
- Rate limit: 30 messages/sec max (won't hit this)

### Error handling
- Wrap each scraper in try/except, log failures but don't crash the whole run
- One broken scraper should not block others
- Log to stdout (GitHub Actions captures it)

## Tech Stack

- Python 3.11+
- `praw` for Reddit
- `requests` + `beautifulsoup4` for HTML scrapers
- `python-telegram-bot` or raw `requests` for Telegram (raw is fine, simpler)
- `python-dotenv` for local dev
- SQLite via stdlib `sqlite3`
- Run via GitHub Actions cron (`*/30 * * * *`)

## Environment Variables

```
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=lead-scraper by /u/yourusername
MIN_LEAD_SCORE=70
SUMMARY_INTERVAL_HOURS=3
SUMMARY_TOP_N=5
LEAD_PREFERENCES=
AI_EVALUATION_ENABLED=false
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-mini
```

## Build Order (MVP first, then expand)

1. Project skeleton + config.py + Post dataclass + BaseScraper
2. SQLite dedup storage
3. Telegram notifier + test message
4. SQLite candidate storage for digest mode
5. Reddit scraper when credentials work
6. Add Workero.cz scraper if public project listings are live
7. Add Jobs.cz scraper
8. Add batch digest evaluation with optional OpenAI
9. GitHub Actions workflow
10. README with setup instructions

## Constraints & Rules

- No em dashes anywhere in code comments, docs, or commit messages
- Respect `robots.txt` and rate limits on all scrapers
- Never scrape Facebook
- Keep the codebase small and readable, no over-engineering
- Prefer stdlib where possible, only add deps that matter
- All user-facing text (Telegram messages, README sections aimed at setup) can be in English; Czech keywords are data, not UI

## Out of Scope (for v1)

- Web UI / dashboard
- Auto-replying to posts
- ML-based relevance scoring (keyword filter is enough)
- Multi-user support
- Paid-contact lead marketplaces
- Scraping FB, LinkedIn, Discord
