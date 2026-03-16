# Discord Reaction Listener

A background service that monitors Discord for reactions on the agent's messages. Part of the autoevolve framework.

## What it does

- Connects to Discord Gateway using the agent's bot token
- Listens for `MESSAGE_REACTION_ADD` and `MESSAGE_REACTION_REMOVE` events
- Filters to reactions on the bot's own messages only (ignores reactions on other users' messages)
- Ignores the bot's own reactions
- Classifies emoji as positive, negative, or neutral
- Appends positive/negative signals to `signals.jsonl`
- Works across ALL channels: DMs, server channels, threads

## Emoji classification

**Positive:** thumbsup, heart, clap, fire, 100, star, tada, rocket, raised_hands, ok_hand, muscle, sparkles, pray, trophy, medal, crown, brain, sunglasses, chef, goat

**Negative:** thumbsdown, x, no_entry

**Neutral (ignored):** everything else (eyes, thinking, question, shrug, etc.)

## Setup

### Prerequisites

- Python 3.10+
- The agent's Discord bot token
- The bot must have the following Gateway Intents enabled in the Discord Developer Portal:
  - Server Members Intent (optional)
  - Message Content Intent (not needed, but the Guilds and Reactions intents are)

### Install dependencies

```bash
cd /opt/autoevolve/services/reaction-listener
pip install -r requirements.txt
```

### Configure the systemd service

```bash
sudo cp reaction-listener.service /etc/systemd/system/
sudo nano /etc/systemd/system/reaction-listener.service
```

Edit the following:
- `User` and `Group` — the system user the agent runs as
- `BOT_TOKEN_PATH` — path to the file containing the Discord bot token (plain text or OpenClaw JSON format)
- `SIGNALS_PATH` — path to the agent's `local/signals.jsonl`

### Enable and start

```bash
sudo systemctl daemon-reload
sudo systemctl enable reaction-listener
sudo systemctl start reaction-listener
```

### Verify

```bash
sudo systemctl status reaction-listener
sudo journalctl -u reaction-listener -f
```

You should see:
```
Connected as BotName#1234 (ID: 123456789)
Signals path: /path/to/local/signals.jsonl
```

React to one of the bot's messages in Discord. You should see a log entry and a new line in `signals.jsonl`.

## Token format

The listener supports two token formats:

1. **Plain text file** — just the bot token string
2. **OpenClaw JSON** — reads `channels.discord.token` from the JSON structure

## Running manually (for testing)

```bash
BOT_TOKEN_PATH=/path/to/token SIGNALS_PATH=/path/to/signals.jsonl python listener.py
```

## Troubleshooting

- **"Privileged intent(s) are not being requested"** — Enable the required intents in the Discord Developer Portal under Bot > Privileged Gateway Intents.
- **No reactions being logged** — Check that you're reacting to the BOT's messages, not someone else's. The listener ignores reactions on other users' messages.
- **Token errors** — Verify the token path and format. Try running manually to see the error.
