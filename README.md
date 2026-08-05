# Blind Date Bot (Persian) — Telegram + Gemini

## 1. Get your keys
- **Telegram bot token**: message [@BotFather](https://t.me/BotFather) on Telegram, run `/newbot`, copy the token.
- **Gemini API key**: go to [Google AI Studio](https://aistudio.google.com/apikey) and create a free API key.

## 2. Add the bot to your group
- Add the bot to your group as a normal member (admin rights not required for the bot itself).
- Make sure **you** (the operator) are an admin of the group — only group admins can run `/match`.

## 3. How it works
1. Both people you want to match must open a private chat with the bot and send `/start`.
2. **Register the group once** (admin, in the group): `/register`
3. Trigger a match. Two ways:
   - In the group: `/match @username1 @username2` — the bot deletes this command message right after processing (best effort, needs delete permission) so it doesn't sit in the group's history.
   - **Fully hidden**: DM the bot privately with `/match @username1 @username2` — nothing about who you picked ever touches the group chat. This uses the group you last `/register`ed.
4. The bot asks Gemini to generate a fresh set of Persian blind-date questions for this session (falls back to a small built-in list if generation fails), then DMs each person the same questions one at a time and collects their answers privately.
5. Once both finish, the bot posts the full Q&A to the group **anonymized** as "نفر اول" (Person 1) / "نفر دوم" (Person 2) — no names or usernames shown to the group.
6. At the same time, the bot sends Gemini's compatibility verdict to the **admin only**, privately, with two buttons: ✅ Approve or ❌ Reject.
7. **Approve** → bot reveals both identities in the group so they can keep talking there. **Reject** → bot posts a generic "didn't work out" message to the group; identities stay hidden permanently.

Number of questions per session is controlled by `NUM_QUESTIONS` (default 6).

## 4. Run locally (for testing)
```bash
pip install -r requirements.txt
export BOT_TOKEN="your-token"
export GEMINI_API_KEY="your-key"
python bot.py
```
No `WEBHOOK_URL` set → runs in polling mode. This works for local testing and for an always-on VM (Oracle Cloud Always Free).

## 5. Deploy to Render (free tier)
1. Push this folder to a GitHub repo.
2. On [render.com](https://render.com), create a **new Web Service**, connect the repo.
3. Build command: `pip install -r requirements.txt`
   Start command: `python bot.py`
4. Add environment variables: `BOT_TOKEN`, `GEMINI_API_KEY`, and `WEBHOOK_URL` = your Render service URL (e.g. `https://your-app.onrender.com`) — Render shows this once the service exists, so deploy once, copy the URL, then set `WEBHOOK_URL` and redeploy.
5. Render's free tier sleeps after ~15 min of no HTTP traffic. Set up a free [UptimeRobot](https://uptimerobot.com) monitor pinging your Render URL every 5 minutes to keep it awake, or upgrade to a paid instance later if the group gets busy.

## 6. Deploy to Oracle Cloud Always Free (no sleep, more setup)
1. Create an Always Free Ampere A1 VM (Ubuntu).
2. SSH in, install Python 3.11+, `git clone` this folder, `pip install -r requirements.txt`.
3. Don't set `WEBHOOK_URL` — run in polling mode.
4. Run it persistently with `systemd` or `tmux`/`screen` so it survives SSH disconnects, e.g. a simple systemd service running `python3 bot.py` with `Restart=always`.

## Notes / limitations
- Deleting the `/match` message in-group requires the bot to have "delete messages" admin rights in that group; without it, the message just stays visible (use the private-DM method instead if that matters to you).
- SQLite (`blind_date.db`) stores users, admin↔group registrations, sessions, and answers. On Render's free tier the filesystem is ephemeral — data resets on redeploy. Fine for testing; for production persistence, either move to Oracle or add a free database add-on (e.g. Render's free Postgres, with a small code change).
- A user can only be in one active question session at a time.
- Gemini free tier has generous but rate-limited quotas — fine for a small group's usage.
- The `gemini-2.5-flash` model name may change over time; check [ai.google.dev](https://ai.google.dev/gemini-api/docs/models) if you get a "model not found" error and update `GEMINI_MODEL`.
