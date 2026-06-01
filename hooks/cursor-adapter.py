#!/usr/bin/env python3
"""cursor-adapter.py — Translate Cursor hook protocol to existing Claude-format guardrails.

Wired from hooks-cursor.json. Each Cursor hook event runs:

    python3 ./hooks/cursor-adapter.py <dispatch-key>

This script:
  1. Reads the Cursor hook envelope from stdin (camelCase fields).
  2. Normalizes it to the {tool_name, tool_input} shape the existing
     guardrail scripts in skills/*/guardrails/ expect.
  3. Sets CLAUDE_PLUGIN_ROOT and CLAUDE_PROJECT_DIR env vars so the
     existing scripts find sessions and shared libs unchanged.
  4. Spawns the underlying script and propagates stdout/stderr.
  5. Translates exit codes:
       Claude Code: 0=allow, 1=fail, 2=block
       Cursor:      0=success, 2=deny (with JSON), other=fail-open
     We map Claude exit 1 and exit 2 -> Cursor deny (exit 2 + JSON on stdout).

Fail-open principle: if anything goes wrong inside the adapter (missing
script, malformed stdin, dispatch key unknown), we exit 0 silently so a
broken adapter never blocks the user's workflow.

Cursor event mapping (see hooks-cursor.json):
  sessionStart        -> trtc-prepare-ui
  beforeReadFile      -> gate-slice-read
  preToolUse          -> gate-slice-write       (filtered to Write/Edit inside)
  afterFileEdit       -> verify-ui-post-write, verify-slice-must
  afterAgentResponse  -> stop-apply-evidence, trtc-verify-ui, verify-apply-project
                         (Claude Code's `Stop` event fires per agent loop
                          iteration end — the same semantic as Cursor's
                          `afterAgentResponse`. Cursor's documented `stop`
                          event was verified to never fire as of 2026-06,
                          so we use afterAgentResponse instead.

                          IMPORTANT: Cursor treats afterAgentResponse as a
                          pure observer event. Our deny envelope is
                          received and logged in Cursor's Hooks Output
                          panel ("Hook 1 blocked action") but does NOT
                          surface to the user (no chat warning) or to the
                          AI (no self-correction). Tested with
                          user_message and followup_message fields — both
                          ignored. This is a Cursor platform limitation,
                          not an adapter issue. Until Cursor implements
                          enforcement on afterAgentResponse, the 3
                          end-of-task guardrails act as audit logs only.)

To enable verbose tracing during development, set the env var
TRTC_HOOK_DEBUG_LOG=/path/to/file.log; see _dbg() below. The default is
silent (no log file written) so production installs don't accumulate logs.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ADAPTER_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = ADAPTER_DIR.parent  # plugin install root


# Optional debug logging — only writes when TRTC_HOOK_DEBUG_LOG is set to a
# path. Useful for diagnosing "why didn't my hook fire" without modifying
# the script.
def _dbg(msg: str) -> None:
    log_path = os.environ.get("TRTC_HOOK_DEBUG_LOG")
    if not log_path:
        return
    try:
        import datetime as _dt
        with open(log_path, "a") as f:
            f.write(f"[{_dt.datetime.now().isoformat(timespec='milliseconds')}] {msg}\n")
    except Exception:
        pass


# Dispatch table: dispatch_key -> relative script path under PLUGIN_ROOT.
DISPATCH = {
    "trtc-prepare-ui":      "skills/trtc/room-builder/guardrails/trtc_prepare_ui.py",
    "gate-slice-read":      "skills/trtc-topic/guardrails/gate_slice_read.py",
    "gate-slice-write":     "skills/trtc-topic/guardrails/gate_slice_write.py",
    "verify-ui-post-write": "skills/trtc/room-builder/guardrails/verify_ui_post_write.sh",
    "verify-slice-must":    "skills/trtc-apply/guardrails/verify_slice_must_rules.py",
    "stop-apply-evidence":  "skills/trtc-topic/guardrails/stop_require_apply_evidence.py",
    "trtc-verify-ui":       "skills/trtc/room-builder/guardrails/trtc_verify_ui.py",
    "verify-apply-project": "skills/trtc-apply/guardrails/verify_apply_project.py",
}

# Dispatch keys whose underlying scripts read JSON from stdin.
# Other keys are CLI-only and will receive empty stdin.
STDIN_KEYS = {
    "gate-slice-read",
    "gate-slice-write",
    "verify-ui-post-write",
    "verify-slice-must",
}


def _silent_allow() -> None:
    """Fail-open: never block the user because the adapter itself failed."""
    _dbg("  EXIT=0 (silent allow)")
    sys.exit(0)


def _read_cursor_payload() -> dict:
    raw = sys.stdin.read()
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (ValueError, TypeError):
        return {}


def _translate_payload(key: str, cursor: dict) -> dict:
    """Map Cursor's per-event payload to the {tool_name, tool_input} envelope
    the existing guardrails expect.

    The existing scripts read either:
      - {"tool_name": "Read",       "tool_input": {"file_path": "..."}}
      - {"tool_name": "Write|Edit", "tool_input": {"file_path": "..."}}
    """
    if key == "gate-slice-read":
        # Cursor's beforeReadFile payload: {file_path, content, attachments, ...}
        file_path = cursor.get("file_path") or cursor.get("filePath")
        return {"tool_name": "Read", "tool_input": {"file_path": file_path}}

    if key == "gate-slice-write":
        # Cursor's preToolUse payload: {tool_name, tool_input, tool_use_id, cwd, ...}
        # Cursor only emits "Write" (no separate "Edit"); existing script
        # accepts both. Pass through unchanged when tool_name is Write/Edit;
        # silent allow for unrelated tools.
        tool_name = cursor.get("tool_name") or cursor.get("toolName")
        if tool_name not in ("Write", "Edit"):
            return {}  # caller will silent-allow
        tool_input = cursor.get("tool_input") or cursor.get("toolInput") or {}
        return {"tool_name": tool_name, "tool_input": tool_input}

    if key in ("verify-ui-post-write", "verify-slice-must"):
        # Cursor's afterFileEdit payload: {file_path, edits}
        file_path = cursor.get("file_path") or cursor.get("filePath")
        return {"tool_name": "Edit", "tool_input": {"file_path": file_path}}

    # CLI-only events (sessionStart, afterAgentResponse) get empty stdin —
    # they read state from session files and env vars, not stdin.
    return {}


def _emit_cursor_deny(message: str) -> None:
    """Cursor deny protocol: JSON on stdout + exit 2.

    Fields populated:
      - permission: "deny" — tells Cursor this action should be blocked.
      - user_message: surfaced in Cursor's UI when the platform supports it
        on the current event. Verified to be ignored on afterAgentResponse
        (Cursor only logs the block in the Output panel there); honored on
        preToolUse / beforeReadFile.
      - agent_message: shown to the agent so it can self-correct on hooks
        that run before the agent's loop ends (preToolUse, beforeReadFile).

    Note: `followup_message` was tested and is NOT honored on
    afterAgentResponse (Cursor 3.4.20). Per Cursor docs it's only meaningful
    on the `stop` event, which itself does not fire in current Cursor
    versions — so there's no reliable channel to make Cursor auto-submit a
    correction message back to the agent after it has already responded.
    """
    _dbg(f"  EXIT=2 (deny) message={message[:160]!r}")
    msg = message or "Blocked by TRTC guardrail."
    payload = {
        "permission": "deny",
        "user_message": msg,
        "agent_message": msg,
    }
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()
    sys.exit(2)


def main(argv: list[str]) -> None:
    key = argv[1] if len(argv) >= 2 else None
    _dbg(
        f"ENTER key={key!r} "
        f"cursor_project_dir={os.environ.get('CURSOR_PROJECT_DIR', '?')!r}"
    )
    if not key:
        _silent_allow()

    # Read stdin first so debug logs see Cursor's hook_event_name even when
    # the dispatch key is unknown or the script is missing.
    cursor_payload = _read_cursor_payload()
    _dbg(
        f"  hook_event_name={cursor_payload.get('hook_event_name', '?')!r} "
        f"keys={sorted(cursor_payload.keys()) if cursor_payload else []}"
    )

    rel_script = DISPATCH.get(key)
    if not rel_script:
        # Unknown dispatch key — never block on adapter misconfiguration.
        _silent_allow()

    script = PLUGIN_ROOT / rel_script
    if not script.exists():
        # Script missing (e.g., skill not installed). Same convention the
        # existing hooks.json uses ("[ ! -f X ] || python3 X").
        _silent_allow()

    claude_payload = _translate_payload(key, cursor_payload)

    # gate-slice-write returns {} when tool isn't Write/Edit -> silent allow.
    if key == "gate-slice-write" and not claude_payload:
        _silent_allow()

    # Build env: surface Cursor's project dir as CLAUDE_PROJECT_DIR so
    # existing scripts that key off CLAUDE_PROJECT_DIR keep working.
    env = dict(os.environ)
    cursor_project_dir = env.get("CURSOR_PROJECT_DIR") or cursor_payload.get("cwd")
    if cursor_project_dir and not env.get("CLAUDE_PROJECT_DIR"):
        env["CLAUDE_PROJECT_DIR"] = cursor_project_dir
    env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN_ROOT)

    runner = ["bash", str(script)] if script.suffix == ".sh" else ["python3", str(script)]
    stdin_data = json.dumps(claude_payload) if key in STDIN_KEYS else ""

    try:
        proc = subprocess.run(
            runner,
            input=stdin_data,
            text=True,
            env=env,
            capture_output=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, OSError):
        _silent_allow()

    # Forward whatever the inner script wrote.
    if proc.stdout:
        sys.stderr.write(proc.stdout)  # inner stdout -> stderr so we don't
                                       # corrupt our Cursor JSON channel
    if proc.stderr:
        sys.stderr.write(proc.stderr)

    rc = proc.returncode
    _dbg(f"  inner_rc={rc}")
    if rc == 0:
        sys.exit(0)
    if rc in (1, 2):
        # Translate fail/block into Cursor's deny envelope. Use stderr
        # content as the agent-facing message so the existing scripts'
        # human-readable explanations reach the user.
        msg = (proc.stderr or proc.stdout or "").strip()
        _emit_cursor_deny(msg)

    # Unknown exit code — fail open to mimic Claude Code's permissive default.
    _silent_allow()


if __name__ == "__main__":
    main(sys.argv)
