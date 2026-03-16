# Signals

Signals are the raw data that drives evolution decisions. They represent human feedback on agent behavior, collected from two sources.

## Signal sources

### Source 1: Agent self-reporting

The agent logs signals during sessions by appending to `local/signals.jsonl`. This requires a block in the agent's instruction file (see `templates/agents-md-patch.md`).

The agent detects feedback in the human's messages:
- Explicit praise or criticism
- Corrections mid-task
- Task completion (with or without corrections needed)

### Source 2: Discord reaction listener

A background service (`services/reaction-listener/`) monitors Discord for reactions on the agent's messages across **all channels** — DMs, server channels, threads. Any place the agent communicates and receives a reaction, it counts.

Positive reactions (thumbsup, heart, clap, fire, 100, etc.) are positive signals. Negative reactions (thumbsdown) are negative.

## Signal format

One JSON object per line in `signals.jsonl`:

```jsonl
{"ts":"2026-03-16T15:01:00Z","source":"self","type":"explicit_positive","text":"perfect, exactly what I needed","session":"main"}
{"ts":"2026-03-16T16:45:00Z","source":"self","type":"correction","text":"no, I said Thursday not Tuesday","session":"main"}
{"ts":"2026-03-16T17:00:00Z","source":"self","type":"task_complete","context":"calendar rescheduling","corrections":0}
{"ts":"2026-03-16T14:32:00Z","source":"discord","type":"reaction_add","emoji":"thumbsup","message_id":"123456","channel_id":"789"}
{"ts":"2026-03-16T14:33:00Z","source":"discord","type":"reaction_remove","emoji":"thumbsup","message_id":"123456","channel_id":"789"}
```

### Fields

| Field | Required | Description |
|---|---|---|
| `ts` | yes | ISO 8601 timestamp |
| `source` | yes | `"self"` (agent) or `"discord"` (listener) |
| `type` | yes | Signal type (see below) |
| `text` | for self-reported | What the human said |
| `context` | for task_complete | Brief task description |
| `corrections` | for task_complete | Number of corrections needed (0 = clean) |
| `emoji` | for reactions | Emoji name (e.g., "thumbsup") |
| `message_id` | for reactions | Discord message ID |
| `channel_id` | for reactions | Discord channel ID |
| `session` | optional | Session type: main, hook, discord, thread |

### Signal types

| Type | Source | Meaning |
|---|---|---|
| `explicit_positive` | self | Human praised the agent |
| `explicit_negative` | self | Human expressed dissatisfaction |
| `correction` | self | Human corrected the agent |
| `task_complete` | self | Agent finished a task |
| `reaction_add` | discord | Reaction added to agent's message |
| `reaction_remove` | discord | Reaction removed from agent's message |

## Signal weights

Configurable in `config.json`. Defaults:

| Signal | Weight | Rationale |
|---|---|---|
| explicit_positive | +5 | Highest signal — human took time to praise |
| explicit_negative | -5 | Highest negative — something went wrong |
| reaction_positive | +2 | Low-effort but genuine acknowledgment |
| reaction_negative | -3 | Weighted slightly higher than positive (negativity bias) |
| task_complete | +3 | Completing tasks is the core job |
| correction | -3 | Agent needed fixing mid-task |
| no_reaction | -0.5 | Weak signal — silence could mean many things |

## Scoring

The evolution loop computes a score over the evaluation window (default 7 days):

```
score = sum(weight[signal.type] for signal in window_signals)
```

For `task_complete` signals with `corrections > 0`, use the `correction` weight instead.

The absolute score is less important than the **delta** between evaluation windows (before vs after a mutation).

## Emoji classification

The reaction listener classifies Discord emoji as positive or negative:

**Positive:** thumbsup, heart, clap, fire, 100, star, tada, rocket, raised_hands, ok_hand, muscle, sparkles, pray, trophy, medal, crown, brain, sunglasses, chef, goat

**Negative:** thumbsdown, x, no_entry, skull (context-dependent — could be "I'm dying laughing")

**Neutral (ignored):** eyes, thinking, question, shrug

This list is configurable in the reaction listener.
