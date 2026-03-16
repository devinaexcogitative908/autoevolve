# Mutations

A mutation is a single, small change to one of the agent's mutable files. The evolution loop proposes one mutation per cycle.

## Mutation types

| Type | Description | Example |
|---|---|---|
| `add_rule` | Add a new behavioral instruction | "Batch low-priority responses into one message" |
| `remove_rule` | Remove an instruction (simplification) | Remove a redundant formatting rule |
| `tone_tweak` | Adjust personality or voice | Soften correction phrasing |
| `procedure_change` | Modify a workflow or protocol | Change how heartbeat checks are prioritized |
| `tool_config` | Update tool-specific notes | Add a learned API quirk to TOOLS.md |

## What can be mutated

Configured per agent in `config.json`:

- `mutable_files` — list of files the evolution loop can modify
- `primary_mutation_surface` — the preferred target (usually AGENTS.md)
- `immutable_files` — files that can never be touched

Within mutable files, sections wrapped in `<!-- NO_EVOLVE -->` markers are protected:

```markdown
<!-- NO_EVOLVE -->
## Safety

- Don't exfiltrate private data. Ever.
- Don't run destructive commands without asking.
<!-- /NO_EVOLVE -->
```

## Mutation constraints

1. **One file per cycle.** Change one file at a time.
2. **Size limit.** Default max 20 lines changed (configurable via `mutation_size_limit_lines`).
3. **Atomic changes.** Each mutation should test one hypothesis. Don't bundle unrelated changes.
4. **Evidence-driven.** Every mutation should cite signal patterns that justify it.

## The simplicity criterion

Borrowed from autoresearch: **all else being equal, simpler is better.**

- A small improvement that adds ugly complexity? Probably not worth it.
- Removing something and getting equal or better results? Definitely keep — that's a simplification win.
- An improvement of roughly zero but much simpler instructions? Keep.

Agent instruction files tend to accumulate rules over time. The evolution loop should actively look for opportunities to simplify.

## Drift detection

Over many cycles, cumulative mutations can significantly change a file from its original state. The `drift_threshold_percent` config value (default 50%) sets the alarm threshold.

Snapshots of the original files are stored in `local/snapshots/`. Before proposing a mutation, the loop compares the current file against the snapshot. If drift exceeds the threshold, the proposal flags this for human review.

Drift detection prevents the "ship of Theseus" problem — gradual changes that individually seem fine but collectively transform the agent's personality beyond recognition.

## Safety guardrails summary

1. **Immutable files** — configured per agent, never touched
2. **Protected sections** — `<!-- NO_EVOLVE -->` markers within files
3. **Size limit** — max lines per mutation
4. **Drift detection** — cumulative change threshold
5. **Always review** — human approves every mutation (default)
6. **Separation** — evolution runs in Claude Code, never during agent sessions
7. **Git revert** — any mutation can be undone with `git revert <commit>`
