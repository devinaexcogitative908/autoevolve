# autoevolve

A self-improving agent framework. Install it on any AI agent that uses file-based personality/instruction systems, and it will propose improvements based on feedback signals from human interactions.

Inspired by [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) — where an AI agent autonomously runs ML experiments overnight (mutate code, train, evaluate, keep or discard). Autoevolve applies the same evolutionary loop to **agent behavior files** instead of neural network training code.

## How it works

```
1. Agent runs normally, collecting feedback signals
   (reactions, explicit feedback, task outcomes)

2. Weekly: Claude Code runs the evolution loop
   - Analyzes signals from the past 7 days
   - Evaluates the last mutation (keep or revert?)
   - Proposes a single, small mutation to one agent file

3. Human reviews the proposal and approves or rejects

4. If approved: mutation is applied, committed, pushed
   Next cycle will evaluate its impact
```

The core insight from autoresearch: **mutate, evaluate, keep-or-discard, repeat**. The difference is that agent quality is measured through human feedback signals (reactions, corrections, praise), not a numeric loss function.

## Stack

This framework is built for a specific stack. It's not trying to be universal — it solves one setup well:

- **Agent platform:** [OpenClaw](https://github.com/anthropics/openclaw) (or any system where agents load personality from markdown files at session start)
- **Chat platform:** Discord (reaction listener uses Discord Gateway; notifications via Discord DM)
- **Evolution engine:** Claude Code (runs the mutation loop as a CLI session on the agent's VM)
- **Service manager:** systemd (for the reaction listener daemon)
- **Version control:** Git (commits = experiments, reverts = discards)

If your agents use a different chat platform or service manager, the core concepts still apply but the reaction listener and notification mechanism would need adapting.

## Concept mapping

| autoresearch | autoevolve |
|---|---|
| `train.py` (mutation surface) | Agent's mutable files (AGENTS.md, SOUL.md, etc.) |
| `prepare.py` (fixed ground truth) | Agent's immutable files (IDENTITY.md, USER.md) + framework |
| `val_bpb` (fitness metric) | Composite signal: reactions + feedback + task outcomes |
| 5-min training run | 7-day evaluation window |
| `results.tsv` | `evolution/experiments.tsv` |
| `program.md` | `evolution/PROGRAM.md` |

## What's in this repo

```
autoevolve/
  README.md                          # You're here
  INSTALL.md                         # Step-by-step installation for any agent
  templates/
    PROGRAM.md                       # Evolution loop instructions (Claude Code reads this)
    config.json                      # Default config with signal weights, thresholds
    agents-md-patch.md               # Instruction block to add to agent's AGENTS.md
    experiments.tsv                  # Header-only template
  services/
    reaction-listener/
      listener.py                    # Discord reaction listener (Gateway-based)
      requirements.txt               # Python deps
      reaction-listener.service      # systemd unit template
      README.md                      # Service-specific docs
  docs/
    concepts.md                      # Design philosophy
    signals.md                       # Signal types, weights, collection
    mutations.md                     # Mutation types, safety, guardrails
    experiment-loop.md               # The evolution loop in detail
```

## What's NOT in this repo

Agent-specific data. After installation, each agent gets an `evolution/` directory in its own workspace:

```
evolution/                           # In agent's workspace
  PROGRAM.md                         # Copied from template, possibly customized
  config.json                        # Agent-specific config
  signals.jsonl                      # Raw feedback signals (append-only)
  experiments.tsv                    # Experiment history (append-only)
  proposed-mutation.md               # Current pending proposal
  snapshots/                         # File snapshots for drift detection
```

## Quick start

See [INSTALL.md](INSTALL.md) for full installation instructions. The short version:

1. Clone this repo on the agent's VM
2. Create `evolution/` in the agent's workspace, copy and customize templates
3. Add the signal-logging block to the agent's AGENTS.md
4. Install and start the Discord reaction listener service
5. Let it collect signals for 1-2 weeks
6. Run the first evolution cycle manually with Claude Code

## Requirements

- An AI agent with file-based personality/instructions (tested with OpenClaw agents)
- Git-tracked agent workspace
- Discord bot token (for reaction tracking)
- Claude Code installed on the agent's VM (for running the evolution loop)
- Python 3.10+ (for the reaction listener service)

## Safety

Self-modifying agents need guardrails:

- **Immutable files** — configure which files can never be touched (e.g., IDENTITY.md)
- **Protected sections** — mark sections within mutable files with `<!-- NO_EVOLVE -->`
- **Mutation size limit** — default max 20 lines changed per experiment
- **Drift detection** — pauses if cumulative changes exceed a threshold
- **Always review** — mutations are proposed, not applied, until human approves
- **Separation** — the evolution loop runs in a separate Claude Code session, never during normal agent operation

## License

MIT
