# Lead Scraper Bot

Scrapes Czech freelance/job boards (Reddit, Poptavka.cz, Hyperpoptavka.cz, Nejremeslnici.cz, Jobs.cz) for web-dev leads and pushes matches to Telegram. Runs free on GitHub Actions every 30 minutes.

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

### Optional AI evaluation

The bot always scores leads locally. Set `MIN_LEAD_SCORE` to control what gets sent to Telegram. The default is `55`.

To add AI reasoning, set:

```env
AI_EVALUATION_ENABLED=true
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5-mini
```

AI evaluation uses the OpenAI Responses API and returns a score, reason, and suggested next step. If the API fails, the bot falls back to local scoring.

## GitHub Actions

1. Push this repo to GitHub.
2. In **Settings → Secrets and variables → Actions**, add the Telegram and Reddit env vars as repo secrets. If using AI evaluation, add `OPENAI_API_KEY` as a secret and add `AI_EVALUATION_ENABLED`, `OPENAI_MODEL`, and `MIN_LEAD_SCORE` as repository variables.
3. In **Settings → Actions → General**, make sure **Workflow permissions** is set to **Read and write permissions** so the job can commit `seen.db` back.
4. The workflow `scrape.yml` runs every 30 minutes. Trigger manually from the Actions tab to smoke-test.

## How it works

- Each scraper fetches recent posts, filters by the include/exclude keyword lists in `config.py`, and passes matches to the notifier.
- Each new match is scored before notification. Low-scoring leads are marked seen and skipped.
- `seen.db` (SQLite) dedupes by post id so you only get pinged once per lead. Actions commits the db back to the repo each run.
- Diacritics are normalized before matching so `webař` also matches `webar`.

## Tuning

- Keywords live in `config.py` (`INCLUDE_KEYWORDS`, `EXCLUDE_KEYWORDS`).
- Lead scoring threshold is `MIN_LEAD_SCORE`.
- Subreddits in `REDDIT_SUBREDDITS`.
- HTML scrapers use generic selectors; if any source stops returning results, inspect the listing page and refine the CSS selector in the corresponding `scrapers/*.py`.
