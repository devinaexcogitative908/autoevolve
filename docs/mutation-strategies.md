# Mutation Strategy Guide

Reference for the evolution controller. Use this when deciding what mutation to propose.

## High-value mutation patterns

These consistently improve agent behavior:

1. **Add a concrete example to an existing rule.** Agents follow examples far better than abstract instructions. If a rule says "keep responses concise," add: "For simple questions, respond in 1-3 sentences. For complex ones, use structured sections."

2. **Remove redundant or conflicting instructions.** Two rules that say similar things create ambiguity. One clear rule beats two fuzzy ones. This is a simplification win — always prefer it.

3. **Convert vague instructions to specific ones.** "Be helpful" is noise. "When the user asks for a status update, include: what changed, what's blocked, and next steps" is actionable. Look for adjective-heavy rules ("be concise," "be thorough," "be careful") and replace them with concrete criteria.

4. **Add error-prevention rules from correction patterns.** If signals show repeated corrections around the same mistake, add a rule that directly addresses it: "When scheduling across timezones, always confirm the timezone before proceeding" rather than "be careful with timezones."

5. **Consolidate scattered related instructions.** If formatting guidance appears in three different sections, merge it into one. Scattered rules are easy to miss and hard to keep consistent.

## Low-value / risky mutation patterns

Avoid these unless signal evidence is overwhelming:

1. **Adding personality traits.** "Be witty" or "use casual tone" are high-variance — they drift unpredictably and are hard to evaluate objectively. Personality should be set by the human, not evolved.

2. **Changing core behavioral rules without strong signal evidence.** Core rules (safety, permissions, communication protocols) exist for reasons that may not be visible in recent signals. Require a clear, sustained pattern before touching them.

3. **Adding complex conditional logic.** "If X and Y but not Z, then do A unless B" is a rule the agent will misapply. If your proposed rule needs more than one condition, it's probably too complex. Split it or simplify.

4. **Duplicating instructions that exist elsewhere.** Before adding a rule, search the mutable files for existing coverage. Adding a second rule about the same behavior creates future conflict.

5. **Reacting to a single correction.** One correction is an anecdote. Three corrections about the same thing in a window is a pattern. Wait for the pattern before mutating. Check signal density — low-density windows amplify noise.

## Deriving mutations from signal patterns

Use these mappings to go from "what the signals say" to "what to change":

| Signal pattern | Likely mutation |
|---|---|
| Corrections cluster around topic X | Add a specific rule about X with a concrete example |
| High positive reactions to a behavior | Reinforce it — add `<!-- NO_EVOLVE -->` markers if it's important enough to protect |
| Repeated `task_complete` with `corrections > 0` in same area | The existing instruction for that area is unclear — rewrite it with specifics |
| Zero signals about a section across multiple windows | That section may be irrelevant — candidate for removal (simplification win) |
| Contradictory signals (positive and negative for same behavior) | The rule is ambiguous — clarify with examples of when to apply vs. when not to |
| `explicit_negative` followed by `explicit_positive` on same topic | The agent self-corrected — add a rule to get it right the first time |

## The simplicity test

Before writing a proposal, ask:

> "Could I achieve the same effect by removing or simplifying an existing instruction instead of adding a new one?"

If yes, do that instead. Instruction files grow monotonically without active pruning. Every added rule increases the chance of conflict and makes the file harder for the agent to follow. A `remove_rule` mutation that maintains or improves the score is always the best outcome.

## Sizing guidance

- A good mutation changes 3-10 lines. Under 3 is often too trivial to move the needle. Over 10 risks testing multiple hypotheses at once.
- If your proposed change needs more than `mutation_size_limit_lines`, break it into sequential cycles. Change one thing, measure, then change the next.
