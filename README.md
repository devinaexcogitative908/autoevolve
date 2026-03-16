# autoevolve

*Upgrades.*

Your AI agents watch how humans react to them, propose mutations to their own behavior files, keep what works, and revert what doesn't. Over time, they evolve.

The idea: take the evolutionary loop from [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) — where an AI agent autonomously mutates training code, runs experiments, and keeps improvements — and apply it to **agent behavior files** instead. In autoresearch, the agent optimizes `train.py` and measures `val_bpb`. Here, the agent optimizes its own personality and instruction files (`AGENTS.md`, `SOUL.md`, etc.) and measures fitness through human feedback signals: Discord reactions, explicit praise or corrections, and task outcomes. A weekly evolution cycle analyzes these signals, proposes a single small mutation, and waits for your approval. If the mutation helps, it stays. If it hurts, it gets reverted. Mutate, evaluate, keep-or-discard, repeat.

This framework is built for agents running on [OpenClaw](https://github.com/anthropics/openclaw) with Discord as the chat platform, [Claude Code](https://docs.anthropic.com/en/docs/claude-code) as the evolution engine, and systemd + Git for infrastructure. The concepts are general but the implementation targets this stack.

## How it works

The repo is deliberately kept small. There are really only four things that matter:

- **`templates/PROGRAM.md`** — the evolution loop instructions. Claude Code reads this and runs one cycle: analyze signals, evaluate the last mutation, propose a new one. **This is what you'd iterate on to improve the evolution process itself.**
- **`templates/config.json`** — declares which agent files are mutable vs immutable, signal weights, safety thresholds. **Customize this per agent.**
- **`templates/agents-md-patch.md`** — a block of instructions you paste into your agent's AGENTS.md telling it to log feedback signals during sessions.
- **`services/reaction-listener/`** — a Discord Gateway listener that tracks reactions (thumbsup, heart, etc.) on the agent's messages across all channels and threads.

After installation, agent-specific runtime data (signals, experiment log, proposals) lives in `local/` inside the cloned repo — gitignored so it never touches the public repo. A pre-commit hook with LLM review adds a second layer of protection.

### The loop

```
1. Agent runs normally, logging feedback signals
   (reactions, explicit praise/corrections, task outcomes)

2. Weekly: Claude Code runs one evolution cycle on the agent's VM
   - Computes a fitness score from the past 7 days of signals
   - Evaluates the last mutation (improved? keep. regressed? revert.)
   - Analyzes signal patterns for improvement opportunities
   - Proposes a single, small mutation to one behavior file

3. Human reviews the proposal (Discord DM) and approves or rejects

4. If approved: mutation applied, committed, pushed
   Next cycle evaluates its impact
```

### Concept mapping

| autoresearch | autoevolve |
|---|---|
| `train.py` (mutation surface) | Agent's mutable files (AGENTS.md, SOUL.md, etc.) |
| `prepare.py` (fixed ground truth) | Agent's immutable files (IDENTITY.md, USER.md) + framework |
| `val_bpb` (fitness metric) | Composite signal: reactions + feedback + task outcomes |
| 5-min training run | 7-day evaluation window |
| `results.tsv` | `local/experiments.tsv` |
| `program.md` | `templates/PROGRAM.md` |
| "NEVER STOP" autonomous loop | Weekly cycle, human-gated |

## Quick start

**Requirements:** An OpenClaw agent with a Discord bot, a Linux VM with systemd, Claude Code, Python 3.10+, Git.

```bash
# 1. Clone autoevolve on the agent's VM
git clone https://github.com/abeldantas/autoevolve.git /opt/autoevolve
cd /opt/autoevolve

# 2. Create local directory (gitignored — agent-specific data lives here)
mkdir -p local/snapshots
cp templates/config.json local/
cp templates/experiments.tsv local/
touch local/signals.jsonl
# Edit local/config.json — set agent name, workspace path, mutable files, Discord user ID

# 3. Add signal logging to the agent's instructions
# Paste the block from templates/agents-md-patch.md into your agent's AGENTS.md

# 4. Install and start the reaction listener
cd /opt/autoevolve/services/reaction-listener
pip install -r requirements.txt
sudo cp reaction-listener.service /etc/systemd/system/
# Edit the service file: set BOT_TOKEN_PATH and SIGNALS_PATH
sudo systemctl daemon-reload && sudo systemctl enable --now reaction-listener

# 5. Let it collect signals for 1-2 weeks, then run the first cycle
cd /opt/autoevolve
claude "Read templates/PROGRAM.md and run one evolution cycle. Agent config is in local/config.json."
```

See [INSTALL.md](INSTALL.md) for the full guide.

## Project structure

```
templates/                          # Framework (tracked, public)
  PROGRAM.md                        — evolution loop instructions (Claude Code reads this)
  config.json                       — default config with signal weights and thresholds
  agents-md-patch.md                — instruction block to paste into agent's AGENTS.md
  experiments.tsv                   — header-only template for experiment tracking
services/
  reaction-listener/                — Discord reaction listener (Gateway-based, systemd)
docs/                               — design philosophy, signals, mutations, loop details
local/                              # Agent-specific data (gitignored, never pushed)
  config.json                       — this agent's config (copied from template)
  signals.jsonl                     — raw feedback signals (append-only)
  experiments.tsv                   — experiment history (append-only)
  proposed-mutation.md              — current pending proposal
  snapshots/                        — file snapshots for drift detection
```

## Design choices

- **One mutation at a time.** Like autoresearch's single-file constraint. Change one thing, measure its impact, decide. Don't bundle.
- **Signal-driven, not random.** Every mutation is justified by observed feedback patterns. No random exploration — the signal data tells you what to try.
- **Simplicity criterion.** Borrowed from autoresearch: all else being equal, simpler is better. Removing an unhelpful instruction is as valuable as adding a helpful one. Agent files tend to accumulate cruft — the evolution loop actively fights that.
- **Human-gated.** Unlike autoresearch's fully autonomous "NEVER STOP" loop, autoevolve always waits for human approval. Agent personality drift damages trust in ways that a bad training run doesn't.
- **Separation of concerns.** The evolution loop runs in its own Claude Code session, never during normal agent operation. The agent doesn't know it's being evolved — it just reads its files each session as usual.

## Safety

Self-modifying agents need guardrails:

- **Immutable files** — configure which files can never be touched (e.g., IDENTITY.md, USER.md)
- **Protected sections** — mark sections within mutable files with `<!-- NO_EVOLVE -->`
- **Mutation size limit** — default max 20 lines changed per experiment
- **Drift detection** — pauses evolution if cumulative changes exceed a threshold vs the original file
- **Always review** — mutations are proposed, not applied, until human approves
- **Git-native** — every mutation is a commit, every revert is a `git revert`. Full audit trail.

## License

MIT
