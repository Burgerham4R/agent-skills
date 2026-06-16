"""End-to-end test: run the full slice loop through every component.

Simulates one full slice's lifecycle by exercising the actual CLI scripts
and gate scripts, not the in-process state_machine module. This catches
regressions where the moving parts agree on the field shape in unit tests
but disagree in integration.

Flow:

    init_slice_queue -> next_slice status (cursor at execution step 0)
        → gate_slice_read (current slice OK, next slice BLOCKED)
        → next_slice advance mark_slice_read
        → gate_slice_write (project file ALLOWED)
        → write code
        → next_slice advance mark_code_written
        → stop hook (BLOCKED — apply hasn't run)
        → apply.py (PASS → state = apply_passed)
        → stop hook (ALLOWED)
        → gate_slice_write (BLOCKED — must wait for confirm)
        → next_slice advance mark_user_confirmed
        → next_slice status (cursor at slice 1)
        → gate_slice_read (slice 1 OK, slice 0 BLOCKED)
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "scripts" / "init_slice_queue.py"
NEXT = ROOT / "scripts" / "next_slice.py"
APPLY = ROOT / "scripts" / "apply.py"
GATE_READ = ROOT / "guardrails" / "gate_slice_read.py"
GATE_WRITE = ROOT / "guardrails" / "gate_slice_write.py"
STOP = ROOT / "guardrails" / "stop_require_apply_evidence.py"


def _run_cmd(*args, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *map(str, args)],
        text=True,
        capture_output=True,
        **kwargs,
    )


def _gate(script: Path, payload: dict, session_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env={"TRTC_SESSION_PATH": str(session_path), "PATH": "/usr/bin:/bin"},
    )


def _stop(session_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(STOP)],
        text=True,
        capture_output=True,
        env={"TRTC_SESSION_PATH": str(session_path), "PATH": "/usr/bin:/bin"},
    )


# Same VUE we used in test_apply_cli.py — wires up the login-auth entry
# (useLoginState), so the entry-symbol gate passes.
_PASSING_LOGIN_VUE = '''<template><div /></template>
<script setup lang="ts">
import { useLoginState, LoginEvent } from "@trtc/tuikit-atomicx-vue3";
const { login, setSelfInfo, subscribeEvent } = useLoginState();
await login({ sdkAppId: 0, userId: "u", userSig: "x", scene: 5001 });
setSelfInfo({ nickName: "Alice" });
subscribeEvent(LoginEvent.onLoginExpired, () => {});
subscribeEvent(LoginEvent.onKickedOffline, () => {});
</script>
'''


def test_full_slice_loop_through_real_scripts(session_factory, project_factory):
    session = session_factory(
        confirmed_plan=["conference/login-auth", "conference/room-lifecycle"]
    )
    proj = project_factory()
    target = proj / "src" / "views" / "MeetingRoom.vue"

    # 1. init queue.
    r = _run_cmd(INIT, "--session", session)
    assert r.returncode == 0, r.stderr
    data = yaml.safe_load(session.read_text())
    assert data["current_execution_index"] == 0
    assert data["current_execution_state"] == "not_started"

    # 2. status.
    r = _run_cmd(NEXT, "--session", session, "--json", "status")
    assert r.returncode == 0
    st = json.loads(r.stdout)
    assert st["current_slice_id"] == "conference/login-auth"
    assert st["state"] == "not_started"

    # 3. read gate: current slice OK.
    r = _gate(GATE_READ, {
        "tool_name": "Read",
        "tool_input": {"file_path": "knowledge-base/slices/conference/web/login-auth.md"},
    }, session)
    assert r.returncode == 0, r.stderr

    # 3b. read gate: next slice BLOCKED.
    r = _gate(GATE_READ, {
        "tool_name": "Read",
        "tool_input": {"file_path": "knowledge-base/slices/conference/web/room-lifecycle.md"},
    }, session)
    assert r.returncode == 2
    assert "current slice" in r.stderr.lower() or "login-auth" in r.stderr

    # 4. write gate: not_started → BLOCKED for project files.
    r = _gate(GATE_WRITE, {
        "tool_name": "Write",
        "tool_input": {"file_path": str(target)},
    }, session)
    assert r.returncode == 2

    # 5. advance mark_slice_read.
    r = _run_cmd(NEXT, "--session", session, "advance", "mark_slice_read")
    assert r.returncode == 0, r.stderr

    # 6. write gate: now ALLOWED.
    r = _gate(GATE_WRITE, {
        "tool_name": "Write",
        "tool_input": {"file_path": str(target)},
    }, session)
    assert r.returncode == 0, r.stderr

    # Actually write the file.
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_PASSING_LOGIN_VUE)

    # 7. advance mark_code_written.
    r = _run_cmd(NEXT, "--session", session, "advance", "mark_code_written")
    assert r.returncode == 0, r.stderr

    # 8. stop hook: BLOCKED, apply hasn't run.
    r = _stop(session)
    assert r.returncode == 2
    assert "apply" in r.stderr.lower()

    # 9. apply.py: pass.
    r = _run_cmd(APPLY, "--slice", "conference/login-auth", "--session", session, "--project", proj)
    assert r.returncode == 0, f"stdout={r.stdout}\nstderr={r.stderr}"

    # State must be apply_passed.
    data = yaml.safe_load(session.read_text())
    assert data["current_execution_state"] == "apply_passed"

    # 10. stop hook: ALLOWED now.
    r = _stop(session)
    assert r.returncode == 0

    # 11. write gate: apply_passed → BLOCKED (must confirm first).
    r = _gate(GATE_WRITE, {
        "tool_name": "Write",
        "tool_input": {"file_path": str(target)},
    }, session)
    assert r.returncode == 2
    assert "apply_passed" in r.stderr or "confirm" in r.stderr.lower()

    # 11b. evidence file is present BEFORE confirmation (apply.py wrote it).
    ev_dir = session.parent / ".trtc-apply-evidence"
    ev_files = list(ev_dir.glob("*.json"))
    assert len(ev_files) == 1
    ev = json.loads(ev_files[0].read_text())
    assert ev["status"] == "pass"
    assert ev["slice_id"] == "conference/login-auth"

    # 12. user confirms.
    r = _run_cmd(NEXT, "--session", session, "advance", "mark_user_confirmed")
    assert r.returncode == 0, r.stderr

    # 13. status: cursor advanced to slice 1.
    r = _run_cmd(NEXT, "--session", session, "--json", "status")
    st = json.loads(r.stdout)
    assert st["current_slice_id"] == "conference/room-lifecycle"
    assert st["state"] == "not_started"

    # 14. read gate: slice 1 now OK, slice 0 now BLOCKED.
    r = _gate(GATE_READ, {
        "tool_name": "Read",
        "tool_input": {"file_path": "knowledge-base/slices/conference/web/room-lifecycle.md"},
    }, session)
    assert r.returncode == 0, r.stderr

    r = _gate(GATE_READ, {
        "tool_name": "Read",
        "tool_input": {"file_path": "knowledge-base/slices/conference/web/login-auth.md"},
    }, session)
    assert r.returncode == 2

    # 15. evidence file was cleaned up by mark_user_confirmed.
    ev_files = list((session.parent / ".trtc-apply-evidence").glob("*.json"))
    assert ev_files == [], (
        "evidence directory should be empty after a clean confirm; "
        f"found {[f.name for f in ev_files]}"
    )


def test_apply_failure_path(session_factory, project_factory):
    """Code that never wires up the slice entry → apply_failed → Stop blocked → Edit allowed."""
    session = session_factory(confirmed_plan=["conference/login-auth"])
    proj = project_factory()
    target = proj / "src" / "views" / "MeetingRoom.vue"

    _run_cmd(INIT, "--session", session)
    _run_cmd(NEXT, "--session", session, "advance", "mark_slice_read")

    # Write real code that never references the login-auth entry (useLoginState).
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        '<template><div /></template>\n<script setup lang="ts">\n'
        'import { ref } from "vue";\nconst ready = ref(true);\n</script>'
    )

    _run_cmd(NEXT, "--session", session, "advance", "mark_code_written")

    r = _run_cmd(APPLY, "--slice", "conference/login-auth", "--session", session, "--project", proj)
    assert r.returncode == 1
    data = yaml.safe_load(session.read_text())
    assert data["current_execution_state"] == "apply_failed"

    # Stop blocked.
    r = _stop(session)
    assert r.returncode == 2

    # Edit gate ALLOWED in apply_failed (V1 walk-back: no slice-reread gate).
    r = _gate(GATE_WRITE, {
        "tool_name": "Edit",
        "tool_input": {"file_path": str(target)},
    }, session)
    assert r.returncode == 0


def test_auto_advance_loop_skips_user_confirm(session_factory, project_factory):
    """With pause_on_failure, apply pass auto-advances cursor to the next slice.

    The AI never has to call mark_user_confirmed for clean slices — apply.py
    does it. The state machine, gates and evidence file all still operate.
    """
    session = session_factory(
        confirmed_plan=["conference/login-auth", "conference/room-lifecycle"]
    )
    proj = project_factory()
    target = proj / "src" / "views" / "MeetingRoom.vue"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_PASSING_LOGIN_VUE)

    # Set policy on the session.
    data = yaml.safe_load(session.read_text())
    data["auto_advance_policy"] = "pause_on_failure"
    session.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

    # init + read + code_written + apply (pass).
    assert _run_cmd(INIT, "--session", session).returncode == 0
    assert _run_cmd(NEXT, "--session", session, "advance", "mark_slice_read").returncode == 0
    assert _run_cmd(NEXT, "--session", session, "advance", "mark_code_written").returncode == 0

    r = _run_cmd(APPLY, "--slice", "conference/login-auth", "--session", session, "--project", proj)
    assert r.returncode == 0, f"stdout={r.stdout}\nstderr={r.stderr}"
    assert "auto-advanced" in r.stdout

    # Cursor should be on slice 1, not_started — no user confirm needed.
    data = yaml.safe_load(session.read_text())
    assert data["current_execution_index"] == 1
    assert data["current_execution_state"] == "not_started"

    # Read gate now allows slice 1's file (and blocks slice 0's).
    r = _gate(GATE_READ, {
        "tool_name": "Read",
        "tool_input": {"file_path": "knowledge-base/slices/conference/web/room-lifecycle.md"},
    }, session)
    assert r.returncode == 0

    r = _gate(GATE_READ, {
        "tool_name": "Read",
        "tool_input": {"file_path": "knowledge-base/slices/conference/web/login-auth.md"},
    }, session)
    assert r.returncode == 2

    # Stop hook: in not_started → allowed.
    assert _stop(session).returncode == 0

    # Slice 1: write code that never wires up the room-lifecycle entry
    # (useRoomState); apply must still pause on failure even with auto-advance.
    target.write_text("<template><div /></template>\n<script setup>\n// no room APIs\n</script>")
    assert _run_cmd(NEXT, "--session", session, "advance", "mark_slice_read").returncode == 0
    assert _run_cmd(NEXT, "--session", session, "advance", "mark_code_written").returncode == 0
    r = _run_cmd(APPLY, "--slice", "conference/room-lifecycle", "--session", session, "--project", proj)
    assert r.returncode == 1
    data = yaml.safe_load(session.read_text())
    assert data["current_execution_state"] == "apply_failed"
    # Stop is still blocked on apply_failed — the safety net survives.
    assert _stop(session).returncode == 2
