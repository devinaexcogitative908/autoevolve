# The Experiment Loop

The evolution loop runs one cycle per invocation. It is invoked as a Claude Code session on the agent's VM, reading `templates/PROGRAM.md` for instructions.

## Lifecycle of a mutation

```
Signal collection (continuous)
        |
        v
Evolution cycle (invocation)
  1. Compute fitness score
  2. Evaluate last mutation (keep/revert/neutral)
  3. Analyze signal patterns
  4. Review experiment history (learn from past cycles)
  5. Roll D20 for mutation strategy
  6. Propose new mutation + check drift
  7. Notify human
        |
        v
Human reviews (Discord DM)
  - Approve (thumbsup) or reject (thumbsdown)
        |
        +--- Approved:
        |      1. Create branch
        |      2. Apply change
        |      3. Commit, merge, push
        |      4. Log to experiments.tsv (status: pending)
        |      5. Next cycle evaluates the result...
        |
        +--- Rejected:
               1. Log to experiments.tsv (status: rejected, no commit)
               2. Delete proposed-mutation.md
               3. Next cycle starts fresh
```

## Evaluation rules

When evaluating a pending mutation, compute `delta = post_score - pre_score` and `threshold = max(abs(pre_score) * 0.10, 2)`:

| Condition | Decision | Action |
|---|---|---|
| delta > 0 | `keep` | Commit stays, advance |
| delta < -threshold | `revert` | `git revert <commit>`, undo |
| -threshold <= delta <= 0 | `neutral` | Keep the change (bias toward simplicity) |

The threshold uses 10% of the absolute pre_score with a floor of 2 points. The floor prevents spurious reverts when pre_score is near zero or negative — without it, a pre_score of 0 would make any drop trigger a revert, and a pre_score of 3 would revert on a 0.3-point fluctuation. Signals are noisy; small score movements should not drive revert decisions.

## Experiment log format

Tab-separated values in `local/experiments.tsv`:

```
date	commit	file	type	description	pre_score	post_score	status
```

| Column | Description |
|---|---|
| date | ISO date (YYYY-MM-DD) |
| commit | Git commit hash (7 chars) |
| file | Which file was mutated |
| type | Mutation type (add_rule, remove_rule, etc.) |
| description | Brief description of the change |
| pre_score | Fitness score at time of mutation |
| post_score | Fitness score at next evaluation (or `-` if pending) |
| status | `pending`, `keep`, `revert`, `neutral`, `rejected` |

## Cadence

- **Manual phase:** Human triggers cycles whenever they want (recommended: weekly)
- **Automated phase:** Cron job runs weekly (e.g., Sunday 10:00 UTC)
- **Why days, not minutes:** Agent quality manifests over days, not minutes. The default 3-day evaluation window (configurable via `eval_window_days`) balances signal density with feedback loop speed. Shorter windows catch issues faster; longer windows reduce noise.

## What happens when there's not enough data

If signal density is low (single digits in the evaluation window), the evolution loop should:
1. Note "low signal density" in the proposal with a confidence flag
2. Still propose a mutation if the existing signals show a clear pattern
3. Skip proposing if there's genuinely nothing to go on
4. If reverting a mutation, note the low confidence — the human can override
