# Lead Scraper Bot

Scrapes free-contact Czech freelance/job sources for web-dev leads, stores new matches, and sends a ranked Telegram digest every few hours. Runs free on GitHub Actions every 30 minutes.

## Local setup

1. Python 3.11+
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in values (see below).
4. `python main.py`

## Credentials

### Telegram

1. Chat with [@BotFather](https://t.me/BotFather), send `/newbot`, follow prompts, copy the bot token into `TELEGRAM_BOT_TOKEN`.
2. Send `/start` to your new bot from your personal account.
3. Open `https://api.telegram.org/bot<TOKEN>/getUpdates`, find `chat.id` in the JSON, put it in `TELEGRAM_CHAT_ID`.

### Reddit

1. Go to https://www.reddit.com/prefs/apps, create a **script** app.
2. Copy the client id (under the app name) to `REDDIT_CLIENT_ID`, the secret to `REDDIT_CLIENT_SECRET`.
3. Set `REDDIT_USER_AGENT` to something like `lead-scraper by /u/yourusername`.

### Digest evaluation

The bot always scores leads locally as it scrapes. Set `MIN_LEAD_SCORE` to control what can be recommended in the digest. The default is `70`.

Tune the digest with:

```env
SUMMARY_INTERVAL_HOURS=3
SUMMARY_TOP_N=5
LEAD_PREFERENCES=Recommend paid custom website projects from free-contact sources. Prefer people who clearly want a website, full custom web, presentation website, business website, landing page, or simple portfolio. Reject WordPress, WP, e-shops, Shoptet, SEO-only work, graphics-only work, full-time jobs, and listings where contacting the client requires a paid credit or subscription. Prefer good budgets, but accept lower payments for genuinely simple portfolio or presentation websites.
```

To use OpenAI for the batch digest only, set:

```env
AI_EVALUATION_ENABLED=true
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5-mini
```

OpenAI is only used when the digest is due. The scraper still collects leads every run and falls back to local scoring if the API is unavailable.

## GitHub Actions

1. Push this repo to GitHub.
2. In **Settings → Secrets and variables → Actions**, add the Telegram and Reddit env vars as repo secrets. If using OpenAI summaries, add `OPENAI_API_KEY` as a secret. Add `AI_EVALUATION_ENABLED`, `OPENAI_MODEL`, `MIN_LEAD_SCORE`, `SUMMARY_INTERVAL_HOURS`, `SUMMARY_TOP_N`, and `LEAD_PREFERENCES` as repository variables if you want to override the defaults.
3. In **Settings → Actions → General**, make sure **Workflow permissions** is set to **Read and write permissions** so the job can commit `seen.db` back.
4. The workflow `scrape.yml` runs every 30 minutes. Trigger manually from the Actions tab to smoke-test.

## How it works

- Each scraper fetches recent posts, filters by the include/exclude keyword lists in `config.py`, and stores new matches as lead candidates.
- Every `SUMMARY_INTERVAL_HOURS`, the bot evaluates unreported candidates and sends one Telegram digest with the best options.
- Paid-contact marketplaces are not active sources. Current active non-Reddit sources are `workero.cz` and `jobs.cz`.
- Na volné noze is not scraped right now because it is a freelancer directory/community, not a public project feed.
- `seen.db` (SQLite) dedupes by post id so you only get pinged once per lead. Actions commits the db back to the repo each run.
- Diacritics are normalized before matching so `webař` also matches `webar`.

## Tuning

- Keywords live in `config.py` (`INCLUDE_KEYWORDS`, `EXCLUDE_KEYWORDS`).
- Lead scoring threshold is `MIN_LEAD_SCORE`.
- Digest cadence is `SUMMARY_INTERVAL_HOURS`; digest size is `SUMMARY_TOP_N`.
- Recommendation preferences live in `LEAD_PREFERENCES`.
- Subreddits in `REDDIT_SUBREDDITS`.
- HTML scrapers use generic selectors; if any source stops returning results, inspect the listing page and refine the CSS selector in the corresponding `scrapers/*.py`.
