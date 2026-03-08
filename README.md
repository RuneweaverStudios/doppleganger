# Doppleganger

**One task, one agent.** Prevents duplicate subagent sessions from running the same task, saving tokens and reducing lag.

## Quick start

```bash
# Install
git clone https://github.com/RuneweaverStudios/doppleganger.git
cp -r doppleganger ~/.openclaw/workspace/skills/

# Check if a task is already running
python3 scripts/doppleganger.py check "fix the login bug" --json

# Guard mode: continuous polling before spawn
python3 scripts/doppleganger.py guard --task "fix the login bug" --interval 5 --timeout 60 --json
```

## What it does

Before calling `sessions_spawn`, run Doppleganger to check whether the same task is already being handled by another subagent. If a duplicate is detected, the orchestrator skips the spawn.

## Commands

| Command | Description |
|---------|-------------|
| `check "<task>"` | One-shot duplicate check |
| `guard --task "<task>"` | Continuous polling until task completes or timeout |

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | No duplicate found -- safe to spawn |
| `1` | Error (tracker failure, timeout, etc.) |
| `2` | Duplicate detected -- do NOT spawn |
| `3` | Dependency missing (subagent-tracker not installed) |

## Dependencies

Requires `subagent-tracker` skill. If not installed, Doppleganger returns exit code 3 with an install instruction. Install it with:

```bash
clawhub install subagent-tracker
```

If subagent-tracker is not available, Doppleganger fails safely (does not crash) and reports the missing dependency.

## Configuration

Edit `config.json` to customize guard behavior:

```json
{
  "guard_poll_interval": 5,
  "guard_timeout": 60,
  "tracker_script_path": ""
}
```

See `SKILL.md` for the full reference.

## License

MIT
