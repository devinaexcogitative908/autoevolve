#!/usr/bin/env python3
"""
Discord reaction listener for autoevolve.

Monitors reactions on the bot's own messages across ALL channels (DMs, servers, threads).
Appends signals to a JSONL file for the evolution loop to analyze.

Usage:
    BOT_TOKEN_PATH=/path/to/token SIGNALS_PATH=/path/to/signals.jsonl python listener.py
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import discord
except ImportError:
    print("discord.py is required: pip install discord.py", file=sys.stderr)
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("autoevolve-reactions")

# ---------------------------------------------------------------------------
# Emoji classification
# ---------------------------------------------------------------------------
# Unicode emoji can carry invisible modifiers that break exact-match lookups:
#   - Skin-tone (Fitzpatrick) modifiers  U+1F3FB .. U+1F3FF  (e.g. 👍🏽)
#   - Variation selector VS16            U+FE0F               (e.g. ❤️ vs ❤)
# Discord sends the full modified form, so we must normalize before lookup.


def _strip_emoji_modifiers(s: str) -> str:
    """Strip skin-tone modifiers and variation selectors from *s*."""
    return "".join(
        ch for ch in s
        if not ("\U0001F3FB" <= ch <= "\U0001F3FF") and ch != "\uFE0F"
    )


def _build_emoji_set(raw: set[str]) -> set[str]:
    """Normalize a set of emoji strings so lookups work regardless of
    skin-tone or variation-selector differences in the input."""
    return {_strip_emoji_modifiers(e) for e in raw}


# Raw definitions (human-readable, may contain variation selectors)
_POSITIVE_RAW = {
    "👍", "❤️", "👏", "🔥", "💯", "⭐", "🎉", "🚀", "🙌", "👌",
    "💪", "✨", "🙏", "🏆", "🥇", "👑", "🧠", "😎", "🧑‍🍳", "🐐",
    # Discord custom names (text, no modifiers possible)
    "thumbsup", "heart", "clap", "fire", "100", "star", "tada", "rocket",
    "raised_hands", "ok_hand", "muscle", "sparkles", "pray", "trophy",
    "medal", "crown", "brain", "sunglasses", "chef", "goat",
}

_NEGATIVE_RAW = {
    "👎", "❌", "⛔",
    "thumbsdown", "x", "no_entry",
}

# Normalized sets used for actual lookups
POSITIVE_EMOJI = _build_emoji_set(_POSITIVE_RAW)
NEGATIVE_EMOJI = _build_emoji_set(_NEGATIVE_RAW)

# Neutral emoji are ignored (eyes, thinking, question, shrug, etc.)


def classify_emoji(emoji_str: str) -> str | None:
    """Classify an emoji as positive, negative, or None (neutral/ignored).

    Handles skin-tone variants (👍🏽 -> 👍) and Discord's text-name format
    (:thumbsup: -> thumbsup) transparently.
    """
    normalized = _strip_emoji_modifiers(emoji_str)
    name = normalized.strip().lower().replace(":", "")
    if name in POSITIVE_EMOJI or normalized in POSITIVE_EMOJI:
        return "positive"
    if name in NEGATIVE_EMOJI or normalized in NEGATIVE_EMOJI:
        return "negative"
    return None


def append_signal(signals_path: Path, signal: dict) -> None:
    """Append a signal to the JSONL file."""
    with open(signals_path, "a") as f:
        f.write(json.dumps(signal, ensure_ascii=False) + "\n")


class ReactionListener(discord.Client):
    def __init__(self, signals_path: Path, **kwargs):
        intents = discord.Intents.default()
        intents.guild_messages = True
        intents.dm_messages = True
        intents.guild_reactions = True
        intents.dm_reactions = True
        intents.message_content = False  # We don't need message content
        super().__init__(intents=intents, **kwargs)
        self.signals_path = signals_path
        self.bot_user_id = None

    async def on_ready(self):
        self.bot_user_id = self.user.id
        log.info(f"Connected as {self.user} (ID: {self.bot_user_id})")
        log.info(f"Signals path: {self.signals_path}")
        log.info(f"Guilds: {[g.name for g in self.guilds]}")

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self._handle_reaction(payload, "reaction_add")

    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self._handle_reaction(payload, "reaction_remove")

    async def _handle_reaction(
        self, payload: discord.RawReactionActionEvent, event_type: str
    ):
        # Only track reactions on the bot's own messages
        # payload.message_author_id is available in discord.py 2.0+
        message_author_id = getattr(payload, "message_author_id", None)

        if message_author_id is None:
            # Fallback: fetch the message to check authorship
            try:
                channel = self.get_channel(payload.channel_id)
                if channel is None:
                    channel = await self.fetch_channel(payload.channel_id)
                message = await channel.fetch_message(payload.message_id)
                message_author_id = message.author.id
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                return

        if message_author_id != self.bot_user_id:
            return

        # Don't track the bot's own reactions
        if payload.user_id == self.bot_user_id:
            return

        emoji_str = str(payload.emoji)
        classification = classify_emoji(emoji_str)

        if classification is None:
            log.debug(f"Ignoring neutral emoji: {emoji_str}")
            return

        signal = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "source": "discord",
            "type": event_type,
            "emoji": emoji_str,
            "emoji_name": payload.emoji.name,
            "classification": classification,
            "message_id": str(payload.message_id),
            "channel_id": str(payload.channel_id),
            "guild_id": str(payload.guild_id) if payload.guild_id else None,
            "user_id": str(payload.user_id),
        }

        append_signal(self.signals_path, signal)
        log.info(
            f"{event_type}: {emoji_str} ({classification}) on message "
            f"{payload.message_id} in channel {payload.channel_id}"
        )


def main():
    # Read config from environment
    token_path = os.environ.get("BOT_TOKEN_PATH")
    signals_path_str = os.environ.get("SIGNALS_PATH")

    if not token_path:
        log.error("BOT_TOKEN_PATH environment variable is required")
        sys.exit(1)

    if not signals_path_str:
        log.error("SIGNALS_PATH environment variable is required")
        sys.exit(1)

    token_path = Path(token_path)
    signals_path = Path(signals_path_str)

    # Read bot token
    if not token_path.exists():
        # Try reading from JSON file (OpenClaw format)
        log.error(f"Token file not found: {token_path}")
        sys.exit(1)

    token_content = token_path.read_text().strip()

    # If the token file is JSON (like openclaw.json), extract the token
    if token_content.startswith("{"):
        try:
            data = json.loads(token_content)
            # Navigate to channels.discord.token
            token = data.get("channels", {}).get("discord", {}).get("token")
            if not token:
                log.error("Could not find channels.discord.token in JSON file")
                sys.exit(1)
        except json.JSONDecodeError:
            log.error("Token file appears to be JSON but failed to parse")
            sys.exit(1)
    else:
        token = token_content

    # Ensure signals file parent directory exists
    signals_path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure signals file exists
    if not signals_path.exists():
        signals_path.touch()

    log.info(f"Starting autoevolve reaction listener")
    log.info(f"Token source: {token_path}")
    log.info(f"Signals output: {signals_path}")

    client = ReactionListener(signals_path=signals_path)
    client.run(token, log_handler=None)


if __name__ == "__main__":
    main()
