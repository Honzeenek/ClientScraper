# Setup Guide — Get It Running

Follow these steps in order. Budget ~30 minutes total.

## 1. Install Python 3.11+

Check what you have:

```bash
python3 --version
```

If below 3.11, install via Homebrew:

```bash
brew install python@3.11
```

## 2. Create a virtualenv and install deps

From the project root (`/Users/janpalenik/Developer/ClientScraper`):

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Create a Telegram bot

1. Open Telegram, search for `@BotFather`, start a chat.
2. Send `/newbot`. Pick a name (e.g. "Lead Scraper") and a unique username ending in `bot` (e.g. `jp_leads_bot`).
3. BotFather replies with a token like `1234567890:AAH...`. Copy it.
4. Search for your new bot in Telegram, open it, press **Start** (or send any message).
5. Get your chat id. In a browser open:

   ```
   https://api.telegram.org/bot<PASTE_TOKEN_HERE>/getUpdates
   ```

   Look for `"chat":{"id": 123456789, ...}`. That number is your chat id.

## 4. Create a Reddit app

1. Go to https://www.reddit.com/prefs/apps (log in if needed).
2. Scroll down, click **create another app...**.
3. Fill in:
   - name: `lead-scraper`
   - type: **script** (important)
   - redirect uri: `http://localhost:8080` (unused but required)
4. Click **create app**. You'll see:
   - **client id**: the short string under the app name (under "personal use script")
   - **secret**: the longer string next to `secret`

## 5. Fill in your local .env

```bash
cp .env.example .env
```

Open `.env` and paste in values:

```
TELEGRAM_BOT_TOKEN=1234567890:AAH...
TELEGRAM_CHAT_ID=123456789
REDDIT_CLIENT_ID=abc123xyz
REDDIT_CLIENT_SECRET=very_long_secret_string
REDDIT_USER_AGENT=lead-scraper by /u/your_reddit_username
```

## 6. Test Telegram

Quick hello to confirm the bot can message you:

```bash
python3 -c "
from datetime import datetime, timezone
from scrapers.base import Post
from notifier.telegram import send_lead
send_lead(Post(
    id='test', title='Test lead', body='this is a smoke test',
    url='https://example.com', source='test',
    posted_at=datetime.now(timezone.utc),
))
print('sent')
"
```

You should see the message in Telegram within a few seconds. If it fails, recheck the token and chat id.

## 7. First real run

```bash
python3 main.py
```

Expected output: one log line per scraper with `fetched=N matched=M notified=K`. The first run may notify a handful of leads if the filter matches anything recent. A `seen.db` file will appear.

Run it again immediately:

```bash
python3 main.py
```

All `notified=0` this time because dedup kicked in. Good.

## 8. Tune the HTML scrapers (important)

The 4 HTML scrapers (`poptavka`, `hyperpoptavka`, `nejremeslnici`, `jobs_cz`) use generic CSS selectors. If you see `fetched=0` for any of them, their real HTML differs from my guess. To fix:

1. Open the listing URL in your browser (they're at the top of each `scrapers/*.py`).
2. Right-click a listing, **Inspect**. Find the wrapper element and note its tag + class, e.g. `<div class="demand-card">`.
3. In the scraper file, replace the `soup.select("...")` line with a selector targeting that class, e.g. `soup.select("div.demand-card")`.
4. Re-run `python3 main.py` and check counts.

If you don't want to tune them right now, skip this — Reddit alone will still work.

## 9. Push to GitHub

```bash
cd /Users/janpalenik/Developer/ClientScraper
git init
git add .
git commit -m "initial commit"
```

Create a new repo on github.com (private is fine), then:

```bash
git remote add origin git@github.com:<your-username>/lead-scraper.git
git branch -M main
git push -u origin main
```

## 10. Add GitHub secrets

On the repo page:

1. **Settings → Secrets and variables → Actions → New repository secret**
2. Add all 5, one at a time, same names and values as your `.env`:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `REDDIT_CLIENT_ID`
   - `REDDIT_CLIENT_SECRET`
   - `REDDIT_USER_AGENT`

## 11. Enable write permissions for Actions

Still on the repo:

1. **Settings → Actions → General**
2. Scroll to **Workflow permissions**, pick **Read and write permissions**, save.

This lets the workflow commit `seen.db` back after each run.

## 12. Trigger the workflow manually

1. **Actions** tab → **scrape** workflow (left sidebar) → **Run workflow** → **Run workflow**.
2. Wait ~1 minute, refresh, click into the run. Check the logs look the same as your local run.
3. Look at the repo's commits — you should see `update seen.db [skip ci]` from `github-actions[bot]`.

## 13. Done

From here, GitHub Actions runs every 30 minutes automatically. You'll get Telegram pings when new matching posts appear.

## Troubleshooting

- **No Telegram message ever arrives**: you probably never pressed Start on your bot. Re-open the bot in Telegram and tap Start.
- **Reddit returns 401/403**: client id or secret is wrong; regenerate at reddit.com/prefs/apps.
- **Actions run succeeds but no commit appears**: write permission isn't enabled (step 11).
- **HTML scraper always returns 0**: site layout differs from my guess (step 8).
- **Too many false positives**: tighten `INCLUDE_KEYWORDS` in `config.py`.
- **Missing real leads**: broaden `INCLUDE_KEYWORDS` or check that the source actually lists that kind of request.
