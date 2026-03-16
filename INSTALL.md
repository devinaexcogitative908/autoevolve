# Installation Guide

Install autoevolve on any agent with a file-based personality system and a git-tracked workspace.

## Prerequisites

- Agent VM with SSH access
- Git-tracked agent workspace
- Discord bot token (the agent's existing bot token works)
- Claude Code installed on the VM (for running evolution cycles — not needed for signal collection)
- Python 3.10+ with `python3-venv` package

## Step 1: Clone autoevolve on the agent's VM

```bash
ssh <agent-vm>
sudo mkdir -p /opt/autoevolve && sudo chown $(whoami) /opt/autoevolve
git clone git@github.com:abeldantas/autoevolve.git /opt/autoevolve
```

## Step 2: Create the local directory

All agent-specific runtime data lives in `local/` inside the autoevolve repo. This directory is gitignored — nothing in it will ever be pushed to the public repo. A pre-commit hook with LLM review adds a second layer of protection.

```bash
cd /opt/autoevolve
mkdir -p local/snapshots
git config core.hooksPath .githooks
```

## Step 3: Copy and customize templates

```bash
cd /opt/autoevolve
cp templates/config.json local/config.json
cp templates/experiments.tsv local/experiments.tsv
touch local/signals.jsonl
```

Edit `local/config.json` to match this agent:

- `agent_name` — the agent's name
- `workspace_path` — absolute path to the agent's workspace (e.g., `/home/user/.openclaw/workspace`)
- `mutable_files` — which files the evolution loop can modify
- `immutable_files` — which files are off-limits
- `primary_mutation_surface` — the file most mutations should target
- `no_evolve_sections` — section headers within mutable files that are protected
- `notification.target_user_id` — Discord user ID of the human reviewer
- `bot_token_path` — path to the file containing the Discord bot token (plain text or OpenClaw JSON format)
- `signals_path` — usually `/opt/autoevolve/local/signals.jsonl`

## Step 4: Snapshot current mutable files

Save the current state of all mutable files for drift detection:

```bash
WORKSPACE=<agent-workspace>
for f in AGENTS.md SOUL.md HEARTBEAT.md TOOLS.md; do
  [ -f "$WORKSPACE/$f" ] && cp "$WORKSPACE/$f" /opt/autoevolve/local/snapshots/
done
```

## Step 5: Add signal-logging to the agent's instructions

Copy the content from `templates/agents-md-patch.md` and paste it into the agent's main instruction file (e.g., `AGENTS.md`).

Update the signals path in the pasted block to point to `/opt/autoevolve/local/signals.jsonl`.

This block tells the agent to log feedback signals during sessions:
- Explicit positive/negative feedback from the human
- Task completions (with or without corrections)

## Step 6: Add NO_EVOLVE markers

In the agent's mutable files, wrap sections that should never be modified by the evolution loop:

```markdown
<!-- NO_EVOLVE -->
## Safety

- Don't exfiltrate private data. Ever.
- Don't run destructive commands without asking.
<!-- /NO_EVOLVE -->
```

Common sections to protect: Safety, Security, Email policies, Authentication, anything you never want mutated.

## Step 7: Install the Discord reaction listener

Create a virtual environment and install dependencies:

```bash
cd /opt/autoevolve
python3 -m venv venv
source venv/bin/activate
pip install -r services/reaction-listener/requirements.txt
```

If `python3 -m venv` fails, install the venv package first:

```bash
sudo apt install python3-venv  # Debian/Ubuntu
# or: sudo dnf install python3-venv  # Fedora
```

Copy the systemd service and customize it:

```bash
sudo cp services/reaction-listener/reaction-listener.service /etc/systemd/system/
sudo nano /etc/systemd/system/reaction-listener.service
```

Update these values:
- `User` and `Group` — the system user the agent runs as
- `BOT_TOKEN_PATH` — path to the Discord bot token file
- `SIGNALS_PATH` — path to `local/signals.jsonl`
- `ExecStart` — must use the venv python: `/opt/autoevolve/venv/bin/python3`

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable reaction-listener
sudo systemctl start reaction-listener
sudo systemctl status reaction-listener
```

You should see it connect to Discord and list the guilds it's monitoring.

## Step 8: Commit and push workspace changes

```bash
cd <agent-workspace>
git add AGENTS.md
git commit -m "Install autoevolve: signal logging block and NO_EVOLVE markers"
git push
```

## Step 9: Wait for data

Let the agent run normally for 1-2 weeks. Signals come from two sources:
- **Reaction listener** — automatically logs Discord reactions on the agent's messages
- **Agent self-reporting** — the agent logs explicit feedback and task completions during sessions

Check that signals are being collected:

```bash
# Check reaction listener is running
sudo systemctl status reaction-listener
sudo journalctl -u reaction-listener -n 10

# Check signals file
wc -l /opt/autoevolve/local/signals.jsonl
tail -5 /opt/autoevolve/local/signals.jsonl
```

To test: react to one of the agent's Discord messages with a thumbsup. You should see a new line in `signals.jsonl` and a log entry in journalctl.

## Step 10: Run the first evolution cycle

```bash
cd /opt/autoevolve
claude "Read templates/PROGRAM.md and run one evolution cycle. Agent config is in local/config.json."
```

Review the proposal. If it looks good, approve it via Discord DM.

## Step 11: Automate (optional)

Once you trust the process, set up a weekly cron:

```bash
crontab -e
# Add:
# 0 10 * * 0 cd /opt/autoevolve && claude --yes "Read templates/PROGRAM.md and run one evolution cycle. Agent config is in local/config.json." > /tmp/autoevolve-$(date +\%F).log 2>&1
```

## Uninstalling

1. Stop and disable the reaction listener: `sudo systemctl stop reaction-listener && sudo systemctl disable reaction-listener`
2. Remove the systemd service: `sudo rm /etc/systemd/system/reaction-listener.service && sudo systemctl daemon-reload`
3. Remove the signal-logging block from the agent's AGENTS.md
4. Remove `<!-- NO_EVOLVE -->` markers (optional — they're just comments)
5. Remove the autoevolve repo: `rm -rf /opt/autoevolve`
6. Commit and push workspace changes
