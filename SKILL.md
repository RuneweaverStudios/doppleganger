---
name: doppleganger
displayName: Doppleganger
description: Prevents duplicate subagent sessions running the same task. One-shot check and continuous guard mode with configurable polling.
version: 1.1.0
---

# Doppleganger

**One task, one agent.** Doppleganger stops duplicate subagent sessions from running the same task. That prevents token overspend, UI lag, and the chaos of five identical "task completed" announcements.

## When to use

- The orchestrator **already runs** a duplicate check before `sessions_spawn` (see delegate rule); Doppleganger is the named skill for that behavior.
- User says: "prevent duplicate agents", "stop dopplegangers", "why are so many agents doing the same thing?"
- You want a single entry point to **check** whether a task is already running before spawning.

## Commands

### check (one-shot)

Given a task string, returns whether that task is already running. If yes, the orchestrator must not spawn again.

```bash
python3 <skill-dir>/scripts/doppleganger.py check "<task string>" [--json]
```

### guard (continuous polling)

Polls repeatedly until the task is no longer running, or until timeout. Use this when you want to wait for a previous duplicate to finish before spawning a new instance.

```bash
python3 <skill-dir>/scripts/doppleganger.py guard --task "<task>" [--interval 5] [--timeout 60] [--json]
```

| Flag | Description | Default |
|------|-------------|---------|
| `--interval N` | Seconds between polls | `5` (from config) |
| `--timeout N` | Maximum wait in seconds | `60` (from config) |

## JSON output

- `{"duplicate": false, "doppleganger_ok": true}` -- safe to spawn.
- `{"duplicate": true, "reason": "running", "sessionId": "...", "doppleganger_ok": true}` -- do not spawn.
- `{"duplicate": true, "guard_timeout": true, ...}` -- guard timed out, duplicate still running.
- `{"dependency_missing": true, "error": "..."}` -- subagent-tracker not installed.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | No duplicate found -- safe to spawn |
| `1` | Error (tracker failure, parse error, etc.) |
| `2` | Duplicate detected -- do NOT spawn |
| `3` | Dependency missing (subagent-tracker skill not installed) |

## Configuration (`config.json`)

| Key | Description | Default |
|-----|-------------|---------|
| `guard_poll_interval` | Seconds between guard polls | `5` |
| `guard_timeout` | Maximum guard wait in seconds | `60` |
| `tracker_script_path` | Custom path to subagent_tracker.py (optional) | Auto-detected |

## Dependencies

Requires `subagent-tracker` skill. If not installed, Doppleganger returns exit code 3 with an install instruction rather than crashing.

```bash
clawhub install subagent-tracker
```

## Orchestrator integration

The delegate rule runs a duplicate check before every `sessions_spawn`; that check can be implemented by calling Doppleganger with the router's task string. If `duplicate: true`, do not call `sessions_spawn`.

## Name

"Doppleganger" = the duplicate agent doing the same thing. One Spiderman is enough.

## Links

- **GitHub:** https://github.com/RuneweaverStudios/doppleganger
- **Related:** [subagent-tracker](https://github.com/RuneweaverStudios/subagent-tracker) - Underlying session tracking
