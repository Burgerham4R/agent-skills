#!/usr/bin/env python3
"""stop_require_apply_evidence.py — Stop hook: refuse to end mid-slice.

Wired into ``.claude/settings.json`` under ``Stop`` (before the project-wide
verifier so the cheap state check runs first). The hook reads the slice
state machine and blocks the Stop event when the AI is about to leave a
slice in an unfinished state:

    code_written  → block — apply.py was never run for this slice
    apply_failed  → block — apply rejected the code; AI must regenerate

Allowed states: not_started, slice_read, apply_passed, all_done, plus the
out-of-scope cases (no session, no queue).

Exit codes:
    0 — allow Stop
    2 — block Stop; stderr explains how to recover
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE_MACHINE_DIR = HERE.parent / "scripts" / "lib"
sys.path.insert(0, str(STATE_MACHINE_DIR))
try:
    import state_machine  # noqa: E402
except Exception:
    # A guardrail must never crash the user's session just because its own
    # dependency failed to import. Fail open (allow Stop) — see main().
    state_machine = None  # type: ignore[assignment]
finally:
    sys.path.pop(0)


_BLOCK_STATES = {"code_written", "apply_failed"}


def _resolve_session_path() -> Path:
    explicit = os.environ.get("TRTC_SESSION_PATH")
    if explicit:
        return Path(explicit)
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        return Path(project_dir) / ".trtc-session.yaml"
    return Path.cwd() / ".trtc-session.yaml"


def main() -> int:
    if state_machine is None:
        # Dependency import failed — fail open (allow Stop).
        return 0

    session_path = _resolve_session_path()
    if not session_path.exists():
        return 0

    scope = state_machine.current_scope(session_path)
    if not scope.get("initialised"):
        return 0
    idx = scope["index"]
    current_id = scope["id"]
    state = scope["state"]
    kind = scope["kind"]

    if state not in _BLOCK_STATES:
        return 0

    if state == "code_written":
        sys.stderr.write(
            f"[topic Stop hook] Cannot end turn: {kind} [{idx}] '{current_id}' "
            f"is in 'code_written' but apply.py has not run.\n"
            f"Run: python3 skills/trtc-topic/scripts/apply.py "
            f"--{'unit' if kind == 'unit' else 'slice'} {current_id}\n"
            f"Then ask the user to confirm before continuing.\n"
        )
        return 2

    # apply_failed
    sys.stderr.write(
        f"[topic Stop hook] Cannot end turn: {kind} [{idx}] '{current_id}' "
        f"is in 'apply_failed'.\n"
        f"Apply rejected the previous code. Regenerate or patch the {kind}'s "
        f"files, then re-run apply.py before stopping.\n"
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Last-resort guard: a hook bug must not trap the user mid-session
        # or spam a traceback. Fail open (allow Stop).
        sys.exit(0)
