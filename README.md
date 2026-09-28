Genshin Impact Auto Daily Check-in Bot
=====================================

Automated daily check-in system for Genshin Impact with Resin tracker and multi-user support. Powered by GitHub Actions for 24/7 operation without requiring any local machine.

Features
--------

- Automatic daily check-in at 07:00 UTC+8
- Multi-user support with individual Telegram notifications
- Detailed daily report including:
  - Today's reward
  - Tomorrow's reward preview
  - Monthly check-in statistics
  - Current Resin status and recovery time
  - Cookie expiration warning
- Zero cost (uses GitHub free tier)
- No local machine required

Requirements
------------

- GitHub Account
- Genshin Impact Account (HoYoverse)
- Telegram Account
- Telegram Bot Token

Setup Instructions
------------------

### Step 1: Prepare Your Account Information

For each user who wants to use this bot:

1. **Get your Game UID**
   - Open Genshin Impact
   - Check your UID in Paimon Menu or main screen
   - Example: 8xxxxxxxx

2. **Get your Server**
   - Asia: os_asia
   - Taiwan: os_cht
   - Europe: os_euro
   - Americas: os_usa

3. **Get your Cookie**
   - Open https://act.hoyolab.com/ys/event/signin-sea-v3/index.html
   - Press F12 (Developer Tools)
   - Go to Network tab
   - Click Check-in button in webpage
   - Find request named "sign" or "info"
   - Go to Headers > Request Headers
   - Copy entire Cookie value

### Step 2: Create Telegram Bot

1. Open Telegram and search for @BotFather
2. Send /newbot
3. Name your bot (e.g., GenshinCheckIn)
4. Set username (e.g., genshin_checkin_bot_123)
5. Copy the Token (example: 123456789:ABCDEFghijklmnopqrstuvwxyz)

### Step 3: Get Your Telegram Chat ID

1. Send any message to your bot
2. Open this URL in browser (replace TOKEN with your bot token):
   ```
   https://api.telegram.org/botTOKEN/getUpdates
   ```
3. Find "chat":{"id": YOUR_CHAT_ID
4. Copy your Chat ID (example: 987654321)

### Step 4: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: genshin-auto-checkin
3. Create repository

### Step 5: Upload Files

1. Create file: genshin_checkin.py
   - Copy entire code from genshin_checkin_multiuser.py
   - Paste and commit

2. Create file: .github/workflows/genshin-checkin.yml
   - Use workflow file provided
   - Commit

### Step 6: Configure GitHub Secrets

1. Go to Repository Settings > Secrets and variables > Actions
2. Delete all old secrets if any
3. Create new secret: USERS_CONFIG

Name: USERS_CONFIG

Value (JSON format - replace with your actual values):
```json
[
  {
    "name": "Your Name",
    "uid": "8xxxxxxxx",
    "server": "os_asia",
    "cookie": "ltoken=v2_xxxxx; ltuid_v2=8xxxxxxxx; account_id_v2=85415287; account_mid_v2=xxxxx",
    "telegram_token": "123456789:ABCDEFghijklmnopqrstuvwxyz",
    "telegram_chat_id": "111111111"
  },
  {
    "name": "Friend Name",
    "uid": "987654321",
    "server": "os_asia",
    "cookie": "ltoken=v2_xxxxx; ltuid_v2=987654321; account_id_v2=87654321; account_mid_v2=xxxxx",
    "telegram_token": "123456789:ABCDEFghijklmnopqrstuvwxyz",
    "telegram_chat_id": "222222222"
  }
]
```

Important: All users can share the same telegram_token (Bot). Each user needs their own telegram_chat_id.

### Step 7: Enable GitHub Actions

1. Go to Repository Actions tab
2. Click on "Genshin Daily Check-in" workflow
3. Enable workflow

### Step 8: Test

1. Go to Actions tab
2. Select "Genshin Daily Check-in"
3. Click "Run workflow"
4. Check your Telegram for report

Example Report
--------------

```
Genshin Impact - Your Name
Date: 21/08/2026 14:55 (UTC+8)

Status: Check-in successful

Today's reward:
  Mora x8000

Tomorrow's reward (preview):
  Hero's Wit x1

This month:
  Checked in : 21 day(s)
  Missed     : 0 day(s)

Monthly rewards so far:
  Mora x168000
  Primogem x60
  Hero's Wit x3
  Mystic Enhancement Ore x6

Resin Status:
  Current: 120/160
  Full resin at: 14:30 (in 5 hours)

Next check-in:
  22/08/2026 at 07:00 (UTC+8)
```

Troubleshooting
---------------

### Error: USERS_CONFIG is required

Make sure:
- Secret USERS_CONFIG is created (not GENSHIN_COOKIE)
- Workflow file has USERS_CONFIG in env section
- JSON format is valid (use JSON validator)

### Error: Failed to get sign info

Possible causes:
- Cookie has expired (need to update every 30 days)
- Cookie format is wrong
- Account is banned or locked

Solution: Re-extract cookie from Network tab

### Resin unavailable

Open Genshin Impact Battle Chronicle in HoYoLAB with the account that owns the
configured game UID, and enable Real-Time Notes. Confirm that the notes load there.
The game UID is different from the HoYoLAB account ID; use the game UID and its server.

- `retcode -100` / `10001`: refresh the HoYoLAB login cookie in `USERS_CONFIG`.
  A cookie that works for daily check-in may not authenticate Battle Chronicle.
  Copy the Cookie header from a working Battle Chronicle `dailyNote` request.
- `retcode 10102`: check Real-Time Notes settings and account ownership.
- Verification errors: complete the verification in HoYoLAB and retry.
- HTTP/network errors: retry later; the report still includes the check-in result.

Resin capacity and recovery seconds come from the API, rather than a fixed cap.
The report shows an explicit unavailable reason when Resin cannot be fetched.
Do not post cookies or tokens in issue reports; share only the error code/message.

Request format reference: [genshin.py](https://github.com/seriaati/genshin.py),
particularly `genshin/client/routes.py`, `genshin/client/components/chronicle/genshin.py`
and `genshin/utility/ds.py`.

Local regression checks: `python -m unittest -v` (mocked API; no account needed).

### Error: Telegram error 400

Check:
- Telegram token is correct
- Telegram chat ID is correct
- Bot has permission to send messages

### Workflow shows success but no Telegram message

Check:
- Telegram token and chat ID are correct
- Bot can send messages (send test message to bot first)
- Check GitHub Actions log for details

Maintenance
-----------

Cookie Expiration:
- Cookies expire approximately every 30 days
- You'll get warning when day >= 25 of month
- Update USERS_CONFIG secret with new cookie

To get fresh cookie:
1. Open https://act.hoyolab.com/ys/event/signin-sea-v3/index.html
2. F12 > Network tab
3. Click Check-in
4. Copy new cookie from request headers
5. Update USERS_CONFIG in GitHub Secrets

Schedule
--------

Current schedule: 07:00 UTC+8 (Daily)

To change time:
1. Edit .github/workflows/genshin-checkin.yml
2. Find line: cron: '0 16 * * *'
3. Change cron value:
   - 00:00 UTC+8: 0 16 * * *
   - 06:00 UTC+8: 0 22 * * *
   - 12:00 UTC+8: 0 4 * * *
   - 18:00 UTC+8: 0 10 * * *
4. Commit changes

Security
--------

- Secrets are encrypted by GitHub
- Cookie is not visible in logs
- Only GitHub Actions can access secrets
- Cookie acts as your game account verification

Important: Never share your cookie with anyone. It's equivalent to your account password.

Limitations
-----------

- GitHub free tier allows 2,000 workflow minutes per month
- This bot uses ~1 minute per day
- Plenty of capacity for multiple users

API Information
---------------

Uses official HoYoLab API endpoints:
- Check-in: https://sg-hk4e-api.hoyolab.com/event/sol/sign
- Sign Info: https://sg-hk4e-api.hoyolab.com/event/sol/info
- Rewards: https://sg-hk4e-api.hoyolab.com/event/sol/home
- Resin: https://sg-public-api.hoyolab.com/event/game_record/genshin/api/dailyNote

Support
-------

If you encounter issues:

1. Check GitHub Actions log for error details
2. Verify all secrets are correct
3. Try manual workflow run
4. Re-extract cookie from Network tab
5. Verify JSON format in USERS_CONFIG

License
-------

MIT License - Free to use and modify

Contributing
------------

Feel free to fork and improve this project.

Disclaimer
----------

This tool uses official HoYoverse APIs. It is not affiliated with or endorsed by miHoYo/HoYoverse. Use at your own risk.

Happy Gaming!
