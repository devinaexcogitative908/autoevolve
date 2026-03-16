# autoevolve — Evolution Loop

You are the evolution controller. Your job is to analyze feedback signals, evaluate past mutations, and propose improvements to this agent's instruction files.

## Setup

Before running, read:
1. This file (you're reading it)
2. `local/config.json` — agent config (mutable files, weights, thresholds)
3. `local/experiments.tsv` — experiment history
4. `local/signals.jsonl` — raw feedback signals
5. The agent's current mutable files (see path resolution below)

### Path resolution

All file references in this document are relative to the autoevolve install directory (where this file lives), UNLESS they refer to the agent's mutable/immutable files. Those live in the agent's **workspace**, configured as `workspace_path` in `local/config.json`.

Concrete example: if `workspace_path` is `/home/user/.openclaw/workspace` and `mutable_files` lists `["AGENTS.md", "SOUL.md"]`, the actual file paths are:
- `/home/user/.openclaw/workspace/AGENTS.md`
- `/home/user/.openclaw/workspace/SOUL.md`

**Read these files now** — you need to understand the agent's current instructions before you can propose changes. All git commands in step 9 (branch, commit, merge, push) must also run inside the `workspace_path` directory.

## The Loop

Run one cycle per invocation. Do NOT loop or repeat — one cycle, then stop.

### 1. Compute Current Fitness Score

Filter `signals.jsonl` to entries within the last `eval_window_days` (from config). For each signal, map it to a weight key from `signal_weights` in config using the rules below, then sum all weighted values to get the **current window score**.

**Mapping rules (signal → weight key):**

| Signal `type` | Signal `source` | Extra fields | Weight key used |
|---|---|---|---|
| `explicit_positive` | self | — | `explicit_positive` |
| `explicit_negative` | self | — | `explicit_negative` |
| `correction` | self | — | `correction` |
| `task_complete` | self | `corrections` = 0 | `task_complete` |
| `task_complete` | self | `corrections` > 0 | `correction` (penalize instead of reward) |
| `reaction_add` | discord | `classification` = "positive" | `reaction_positive` |
| `reaction_add` | discord | `classification` = "negative" | `reaction_negative` |
| `reaction_remove` | discord | `classification` = "positive" | Subtract `reaction_positive` (undo the add) |
| `reaction_remove` | discord | `classification` = "negative" | Subtract `reaction_negative` (undo the add) |

**Important:** The reaction listener writes `type: "reaction_add"` or `"reaction_remove"` with a `classification` field. You must use the classification to look up the correct weight. A `reaction_remove` inverts the sign — if someone removes a thumbsup, subtract the `reaction_positive` weight (i.e., apply `-reaction_positive`).

Signals with types not listed above (or with no matching weight key) should be skipped with a note in the analysis.

**Signal density note:** Count the number of signals in the evaluation window. If the count is low (single digits), note "low signal density" in your analysis and flag the confidence level. The score is still valid but noisier — factor this into your decisions in steps 2 and 5.

### 2. Evaluate Last Mutation

Check `experiments.tsv` for the most recent entry with status `pending`.

- If no pending entry: skip to step 3 (this is the first run or last was already resolved).
- If pending:
  - The `pre_score` was recorded when the mutation was applied.
  - The current window score is the `post_score`.
  - Compute `delta = post_score - pre_score`.
  - Compute the revert threshold: `threshold = max(abs(pre_score) * revert_threshold_pct/100, revert_threshold_floor)` (from config; defaults: 10%, floor 2). This ensures a meaningful minimum — when pre_score is near zero, the percentage rule alone would revert on trivial noise.
  - **If delta > 0**: mark status as `keep`. The mutation helped.
  - **If delta < -threshold** (score dropped by more than the threshold): mark status as `revert`. Run `git revert <commit>` to undo. If signal density is low, note this in the log — the revert is less certain.
  - **If -threshold <= delta <= 0** (small or no drop): mark status as `neutral`. Keep the change (bias toward simplification).
  - Update the row in `experiments.tsv` with the post_score and new status.

### 3. Analyze Signals

Look at the signals from the current window and identify patterns:

- **Correction clusters** — are corrections concentrated around a specific topic or behavior? (e.g., "formatting", "email tone", "date handling")
- **Positive clusters** — what's earning praise or reactions?
- **Unaddressed feedback** — is there feedback that suggests a behavior change not yet captured in the agent's files?
- **Simplification opportunities** — are there instructions the agent ignores or that seem redundant?
- **Signal source balance** — check that both self-reported signals (explicit_positive, correction, task_complete) and reaction signals (from Discord) are present in the window. If reaction signals exist but there are zero self-reported signals, the agent is likely not following its signal logging instructions — flag this prominently in the analysis and skip proposing a mutation (the signal data is incomplete and any score is unreliable).

Write a brief analysis (3-5 bullet points) to `local/proposed-mutation.md` under a `## Signal Analysis` heading.

### 4. Review Experiment History

Before proposing a new mutation, review `local/experiments.tsv` for patterns in past experiments. This is the evolution loop's institutional memory — without it, you're flying blind on what's already been tried.

**Analyze the full history for:**

- **Rejected proposals** — If the human rejected a mutation targeting a specific file or topic, do not re-propose the same change unless new signal evidence is substantially stronger. Two rejections of the same type/file combination means that area is off-limits until the human explicitly reopens it.
- **Reverted mutations** — These are experiments that made things worse. Note which files and mutation types were reverted. Avoid repeating the same approach on the same target. If a `tone_tweak` to SOUL.md was reverted, don't propose another `tone_tweak` to SOUL.md — try a different type or file.
- **Successful patterns** — Which mutation types and target files have status `keep`? Lean toward what has worked. If `specify` mutations on AGENTS.md consistently score well, that's a productive vein to mine.
- **Neutral results** — Mutations marked `neutral` were kept but didn't move the needle. If several neutrals cluster on the same file, that file may be close to its local optimum — consider targeting a different file.
- **Category saturation** — If the last 3+ mutations were all in the same D20 category (e.g., all `simplify`), the agent's instructions may benefit from a different angle. Note this for step 5 — if the D20 happens to roll the same saturated category, consider re-rolling once (note the original roll in the proposal).

**Write a `## Experiment History` section** to `local/proposed-mutation.md` summarizing what you found (2-4 bullet points). If the history is empty (first cycle), write "First cycle — no history yet." and move on.

### 5. Roll for Mutation Strategy

Before proposing, roll the D20 to determine what kind of mutation to attempt. Use `--json` to get machine-readable output:

```bash
python3 services/d20/roll.py --json
```

This prints a JSON object to stdout with `roll`, `category`, `name`, and `description` fields. Capture the output and use it in your proposal.

The roll determines the mutation *approach*, NOT the mutation *target*. The target always comes from the signal analysis in step 3. The D20 tells you HOW to act on what the signals are saying:

- Roll 5 (shorten) + signals show corrections around email formatting → shorten the email formatting section
- Roll 7 (add example) + signals show positive reactions to calendar responses → add an example to the calendar rule
- Roll 2 (remove dead weight) + signals show zero engagement with a section → remove that section

**Signals pick the WHERE. The D20 picks the HOW.**

Exceptions: Roll 1 (rest cycle) skips entirely — write "rest cycle" to the analysis and stop. Roll 20 (freak mutation) is intentionally unconstrained — go creative, the human reviews it anyway.

Also read `docs/mutation-strategies.md` for the full table and deeper guidance.

### 6. Propose a Mutation

Based on the signal analysis (step 3), the experiment history (step 4), and the D20 strategy (step 5), propose **one** small change to **one** mutable file.

**Rules:**
- Only modify files listed in `mutable_files` in config.json.
- Never modify files listed in `immutable_files`.
- Never modify sections wrapped in `<!-- NO_EVOLVE -->` ... `<!-- /NO_EVOLVE -->` markers.
- Prefer the `primary_mutation_surface` unless the signal clearly points elsewhere.
- Maximum diff size: `mutation_size_limit_lines` lines (default 20).
- One mutation per cycle. Change one thing at a time.
- **Do not repeat rejected or reverted experiments.** If step 4 identified a file/type combination that was rejected or reverted, do not propose it again unless you have substantially new signal evidence. Explain the new evidence in the rationale.

**Simplicity criterion** (from autoresearch): All else being equal, simpler is better. Removing an instruction that isn't helping is a great outcome. Adding complexity needs clear signal justification.

**Mutation types:**
- `add_rule` — add a new behavioral instruction
- `remove_rule` — remove an instruction (simplification win)
- `tone_tweak` — adjust personality/voice
- `procedure_change` — modify a workflow/protocol
- `tool_config` — update tool-specific notes

Write the proposal to `local/proposed-mutation.md`:

```markdown
## D20 Roll
- **Roll:** 7
- **Strategy:** Add an example

## Signal Analysis
- [3-5 bullet points about patterns observed]

## Experiment History
- [2-4 bullet points about relevant past experiments, or "First cycle — no history yet."]

## Proposed Mutation
- **File:** AGENTS.md
- **Type:** add_rule
- **Description:** Add instruction to batch low-priority responses
- **Rationale:** Signals show corrections when agent interrupts with low-priority info
- **Diff:**
  ```diff
  + ## Response Batching
  + When multiple low-priority items need attention, batch them into a single message
  + rather than sending separate messages for each. Only interrupt for urgent items.
  ```
```

### 7. Check Drift

Before proposing, check cumulative drift:
- Compare the current mutable files against `local/snapshots/` (the original versions from installation).
- If any file has changed by more than `drift_threshold_percent`% from its snapshot, note this in the proposal and recommend a human review of the full file.

If no snapshot exists yet, create one now:
```bash
cp <mutable_file> local/snapshots/<mutable_file>
```

### 8. Notify Human

If `review_mode` is `always` (or the file requires review):

Post the proposal summary to the configured notification channel. For Discord DM, build the JSON payload in a temporary file to avoid shell escaping issues:

```bash
TOKEN=$(cat <bot_token_path>)
TARGET_USER_ID=<from config.json>

# Create DM channel
CHANNEL_ID=$(curl -s -H "Authorization: Bot $TOKEN" -H "Content-Type: application/json" \
  -d "{\"recipient_id\": \"$TARGET_USER_ID\"}" \
  https://discord.com/api/v10/users/@me/channels | jq -r '.id')

# Build message payload safely using a temp file (avoids JSON escaping issues in shell)
python3 -c "
import json, sys
msg = sys.argv[1]
print(json.dumps({'content': msg}))
" "**autoevolve proposal**

File: <file>
Type: <type>
Description: <description>

Rationale: <rationale>

React thumbsup to approve, thumbsdown to reject." > /tmp/autoevolve-msg.json

curl -s -H "Authorization: Bot $TOKEN" -H "Content-Type: application/json" \
  -d @/tmp/autoevolve-msg.json \
  "https://discord.com/api/v10/channels/$CHANNEL_ID/messages"

rm -f /tmp/autoevolve-msg.json
```

Then **stop**. The mutation will be applied in the next cycle after approval, or by a follow-up invocation. Do not proceed to step 9 in the same invocation unless the human has already responded.

### 9. Apply or Discard

Check whether the human approved or rejected the proposal from step 8.

**All git commands in this step run inside `workspace_path`** (the agent's workspace repo, NOT the autoevolve repo).

- **Approved** (thumbsup reaction on the Discord DM, or explicit approval):
  1. First, check the workspace for uncommitted changes:
     ```bash
     cd <workspace_path>
     git status --porcelain
     ```
     If there are uncommitted changes, **stop and notify the human** — do not create a branch on top of a dirty tree. The agent may be mid-session. Wait for a clean state.
  2. Create branch: `git checkout -b evolve/<agent_name>/<date>-<short-description>`
  3. Apply the change to the target file (at `<workspace_path>/<file>`)
  4. `git add <file> && git commit -m "evolve: <description>"`
  5. `git checkout main && git merge evolve/<agent_name>/<date>-<short-description>`
  6. `git push origin main`
  7. Record in `local/experiments.tsv` (back in the autoevolve directory):
     ```
     <date>\t<commit>\t<file>\t<type>\t<description>\t<current_score>\t-\tpending
     ```

- **Rejected** (thumbsdown reaction, explicit rejection, or no response after a reasonable period):
  1. Record in `local/experiments.tsv` with status `rejected` and no commit hash:
     ```
     <date>\t-\t<file>\t<type>\t<description>\t<current_score>\t-\trejected
     ```
  2. Delete `local/proposed-mutation.md` (clean up for the next cycle).
  3. Do NOT apply the change. Do NOT create a branch or commit.
  4. The next cycle starts fresh — it may re-propose a similar mutation if the signals still support it, or propose something different.

**Why log rejections?** The experiment history should capture every proposal, not just the ones that were applied. A pattern of rejections around a particular file or mutation type is itself a signal — it tells future cycles what the human considers out of bounds.

## Important Notes

- **One cycle per invocation.** Run steps 1 through 8 (or 9 if approval already exists), then STOP. Do not loop back to step 1. Do not run a second cycle. The human controls cadence.
- **One mutation per cycle.** Propose exactly one change to exactly one file. If you see multiple improvement opportunities, pick the strongest one and save the rest for future cycles.
- **Never modify agent files during this session beyond the approved mutation.** You are the evolution controller, not the agent. Do not "fix" things you notice in the agent's files outside the formal mutation process.
- **Stop after notifying.** Step 8 ends the cycle unless the human has already approved. Do not wait, poll, or loop for a response.
- **Be conservative.** A mutation that makes things slightly worse damages trust. Prefer safe bets.
- **Log everything.** The experiment log is the audit trail. Every action should be traceable.
- **Respect the markers.** `<!-- NO_EVOLVE -->` sections are sacred. Period.
