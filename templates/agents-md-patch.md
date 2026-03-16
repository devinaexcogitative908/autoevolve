# Signal Logging Block for AGENTS.md

Copy the block below and paste it into your agent's main instruction file (e.g., `AGENTS.md`). This instructs the agent to log feedback signals during sessions for the autoevolve framework.

---

```markdown
## Evolution — Signal Logging

You are part of an ongoing self-improvement loop. During sessions, log feedback signals to `local/signals.jsonl` (one JSON object per line). This data drives weekly evolution proposals.

**When to log:**

- **Explicit positive feedback** — your human says something clearly positive about your work ("great", "perfect", "exactly what I needed", "nice", "love it")
  ```json
  {"ts":"ISO8601","source":"self","type":"explicit_positive","text":"what they said","session":"SESSION_TYPE"}
  ```

- **Explicit negative feedback / correction** — your human corrects you or expresses dissatisfaction ("no", "wrong", "I said X not Y", "stop", "that's not right")
  ```json
  {"ts":"ISO8601","source":"self","type":"correction","text":"what they said","session":"SESSION_TYPE"}
  ```

- **Task completion** — you finish a task. Note whether corrections were needed.
  ```json
  {"ts":"ISO8601","source":"self","type":"task_complete","context":"brief description","corrections":0}
  ```

**Rules:**
- Use `exec` to append (the file is outside workspace if needed): `echo '{"ts":"..."}' >> local/signals.jsonl`
- One line per signal. Valid JSON. ISO 8601 timestamps.
- Don't over-log. One signal per distinct feedback moment, not per message.
- Session type: "main", "hook", "discord", "thread" — whatever applies.
- This logging should be lightweight. Don't let it interfere with your primary task.
```

---

## Where to paste it

Add it near the end of the agent's AGENTS.md, before any "Make It Yours" or closing section. The section should be clearly visible but not dominate the file.
