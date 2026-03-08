#!/usr/bin/env python3
"""
Doppleganger -- Prevent duplicate subagent sessions.

Stops the "multiple Spidermen pointing at each other" problem: same task
spawned multiple times = token overspend and lag. Run before sessions_spawn
to block duplicates.

Usage:
  python3 doppleganger.py check "<task string>" [--json]
  python3 doppleganger.py guard --task "<task>" [--interval N] [--timeout N] [--json]

Exit codes:
  0 = no duplicate (safe to spawn)
  1 = error
  2 = duplicate detected
  3 = dependency missing (subagent-tracker not installed)
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = SKILL_DIR / "config.json"
OPENCLAW_HOME = Path(os.environ.get("OPENCLAW_HOME", Path.home() / ".openclaw"))
TRACKER_SCRIPT = OPENCLAW_HOME / "workspace" / "skills" / "subagent-tracker" / "scripts" / "subagent_tracker.py"


def _load_config() -> dict:
    """Load config.json with defaults."""
    defaults = {
        "guard_poll_interval": 5,
        "guard_timeout": 60,
        "tracker_script_path": "",
    }
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                user = json.load(f)
            defaults.update(user)
        except (json.JSONDecodeError, OSError):
            pass
    return defaults


CONFIG = _load_config()


def _find_tracker():
    """Locate the subagent-tracker script."""
    # Check config override first
    custom = CONFIG.get("tracker_script_path", "")
    if custom and Path(custom).exists():
        return custom
    if TRACKER_SCRIPT.exists():
        return str(TRACKER_SCRIPT)
    fallback = SKILL_DIR / ".." / "subagent-tracker" / "scripts" / "subagent_tracker.py"
    if fallback.exists():
        return str(fallback.resolve())
    return None


def check_dependency() -> bool:
    """Check if subagent-tracker skill is installed and accessible."""
    return _find_tracker() is not None


def check_duplicate(task: str) -> dict:
    """Check if task is already running. Returns result dict."""
    tracker = _find_tracker()
    if not tracker:
        return {
            "duplicate": False,
            "error": "subagent-tracker skill not found. Install it with: clawhub install subagent-tracker",
            "doppleganger_ok": False,
            "dependency_missing": True,
        }
    cmd = [sys.executable, tracker, "check-duplicate", "--task", task, "--json"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        out = result.stdout.strip()
        if not out:
            return {"duplicate": False, "error": result.stderr or "no output", "doppleganger_ok": False}
        data = json.loads(out)
        data["doppleganger_ok"] = True
        return data
    except subprocess.TimeoutExpired:
        return {"duplicate": False, "error": "timeout", "doppleganger_ok": False}
    except json.JSONDecodeError as e:
        return {"duplicate": False, "error": str(e), "doppleganger_ok": False}


def guard_loop(task: str, interval: int, timeout: int) -> dict:
    """
    Continuously poll for duplicates until the task is no longer running or timeout.

    Returns the final check result. Useful for waiting until a previously-detected
    duplicate finishes before spawning a new instance.
    """
    deadline = time.time() + timeout
    last_result = None
    while time.time() < deadline:
        last_result = check_duplicate(task)
        if last_result.get("dependency_missing"):
            return last_result
        if not last_result.get("duplicate"):
            return last_result
        time.sleep(interval)
    # Timed out while duplicate was still running
    if last_result:
        last_result["guard_timeout"] = True
    return last_result or {"duplicate": True, "error": "guard timeout", "guard_timeout": True}


def main():
    parser = argparse.ArgumentParser(
        description="Doppleganger: prevent duplicate subagent sessions (same task = one agent)."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    check_p = sub.add_parser("check", help="One-shot check if this task is already running")
    check_p.add_argument("task", nargs="?", default="", help="Task string (same as for sessions_spawn)")
    check_p.add_argument("--json", action="store_true", help="JSON output")

    guard_p = sub.add_parser("guard", help="Continuous polling: wait until task is no longer running or timeout")
    guard_p.add_argument("--task", required=True, help="Task string")
    guard_p.add_argument("--interval", type=int, default=CONFIG["guard_poll_interval"],
                         help=f"Poll interval in seconds (default: {CONFIG['guard_poll_interval']})")
    guard_p.add_argument("--timeout", type=int, default=CONFIG["guard_timeout"],
                         help=f"Maximum wait time in seconds (default: {CONFIG['guard_timeout']})")
    guard_p.add_argument("--json", action="store_true", help="JSON output")

    args = parser.parse_args()
    task = (getattr(args, "task", None) or "").strip()
    json_out = getattr(args, "json", False)

    if args.command == "check":
        result = check_duplicate(task)
    elif args.command == "guard":
        result = guard_loop(task, args.interval, args.timeout)
    else:
        result = {"error": f"Unknown command: {args.command}"}

    if json_out:
        print(json.dumps(result))
        if result.get("dependency_missing"):
            sys.exit(3)
        elif result.get("duplicate"):
            sys.exit(2)
        elif result.get("error"):
            sys.exit(1)
        sys.exit(0)
    else:
        if result.get("dependency_missing"):
            print(f"Doppleganger: dependency missing -- {result['error']}", file=sys.stderr)
            sys.exit(3)
        if result.get("guard_timeout"):
            print(f"Doppleganger: guard timed out -- duplicate still running. sessionId={result.get('sessionId', '?')}")
            sys.exit(2)
        if result.get("duplicate"):
            print(f"Doppleganger: duplicate detected (already running). sessionId={result.get('sessionId', '?')}")
            sys.exit(2)
        if result.get("error"):
            print(f"Doppleganger: check failed -- {result['error']}")
            sys.exit(1)
        print("Doppleganger: no duplicate; safe to spawn.")
        sys.exit(0)


if __name__ == "__main__":
    main()
