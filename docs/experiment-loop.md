# The Experiment Loop

The evolution loop runs one cycle per invocation. It is invoked as a Claude Code session on the agent's VM, reading `templates/PROGRAM.md` for instructions.

## Lifecycle of a mutation

```
Signal collection (continuous, 7 days)
        |
        v
Evolution cycle (weekly invocation)
  1. Compute fitness score
  2. Evaluate last mutation (keep/revert/neutral)
  3. Analyze signal patterns
  4. Propose new mutation
  5. Notify human
        |
        v
Human reviews (Discord DM)
  - Approve (thumbsup) or reject (thumbsdown)
        |
        v
Apply mutation (next invocation or follow-up)
  1. Create branch
  2. Apply change
  3. Commit, merge, push
  4. Log to experiments.tsv (status: pending)
        |
        v
Next cycle evaluates the result...
```

## Evaluation rules

When evaluating a pending mutation:

| Condition | Decision | Action |
|---|---|---|
| post_score > pre_score | `keep` | Commit stays, advance |
| post_score < pre_score by >10% | `revert` | `git revert <commit>`, undo |
| Within 10% (roughly equal) | `neutral` | Keep the change (bias toward simplicity) |

The 10% threshold exists because signals are noisy. Small fluctuations in score shouldn't trigger reverts.

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
- **Why weekly:** Agent quality manifests over days, not minutes. A 7-day window provides enough signal density for meaningful evaluation while keeping the feedback loop tight enough to iterate.

## What happens when there's not enough data

If `signals.jsonl` has fewer than 10 signals in the evaluation window, the evolution loop should:
1. Note this in the proposal ("insufficient signal density")
2. Still propose a mutation if the existing signals show a clear pattern
3. Skip proposing if there's genuinely nothing to go on
4. Never revert based on insufficient data — leave the last mutation as `neutral`
