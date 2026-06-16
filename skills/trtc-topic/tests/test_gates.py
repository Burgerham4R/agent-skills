"""Tests for the PreToolUse gates that enforce the slice loop.

Both gates read a JSON object on stdin (Claude Code's PreToolUse contract):
    {
      "tool_name": "Read" | "Write" | "Edit" | ...,
      "tool_input": { "file_path": "...", ... }
    }

They exit:
    0 — allow the tool call (out of scope, or in-bounds)
    2 — block the tool call; stderr explains why
    other — treated as configuration error; AI sees stderr but Claude Code
            does not block (we never produce these intentionally).

Out-of-scope cases that MUST exit 0:
    - session file missing
    - execution_queue not initialised (topic flow not active)
    - tool_name doesn't match what the gate guards
    - file_path falls outside the gate's domain
      (slice-read gate: only guards knowledge-base/slices/*.md)
      (slice-write gate: only guards user-project source files)
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

GUARDRAILS_DIR = Path(__file__).resolve().parents[1] / "guardrails"
GATE_READ = GUARDRAILS_DIR / "gate_slice_read.py"
GATE_WRITE = GUARDRAILS_DIR / "gate_slice_write.py"

# state_machine helper for advancing test sessions to a specific state
STATE_MACHINE_DIR = Path(__file__).resolve().parents[1] / "scripts" / "lib"
sys.path.insert(0, str(STATE_MACHINE_DIR))
import state_machine  # noqa: E402
sys.path.pop(0)


def _run_gate(script: Path, payload: dict, session_path: Path) -> subprocess.CompletedProcess:
    """Invoke a gate script with the given JSON stdin payload.

    The session path is passed via TRTC_SESSION_PATH env var so the gate
    doesn't have to walk the filesystem looking for one. Real hooks use the
    project's repo root via $CLAUDE_PROJECT_DIR; tests use a tmp_path session.
    """
    return subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env={"TRTC_SESSION_PATH": str(session_path), "PATH": "/usr/bin:/bin"},
    )


# ---------- gate_slice_read ------------------------------------------------

class TestGateSliceRead:
    def test_allows_when_session_missing(self, tmp_path):
        """No session file → not in topic flow → must allow."""
        payload = {
            "tool_name": "Read",
            "tool_input": {"file_path": str(tmp_path / "knowledge-base/slices/conference/web/room-chat.md")},
        }
        result = _run_gate(GATE_READ, payload, tmp_path / "missing.yaml")
        assert result.returncode == 0, result.stderr

    def test_allows_when_queue_not_initialised(self, session_factory):
        """Session exists but no execution_queue -> topic flow not active."""
        path = session_factory()
        payload = {
            "tool_name": "Read",
            "tool_input": {"file_path": "knowledge-base/slices/conference/web/room-chat.md"},
        }
        result = _run_gate(GATE_READ, payload, path)
        assert result.returncode == 0, result.stderr

    def test_allows_non_read_tool(self, session_factory):
        """Gate only guards Read; Write should pass through."""
        path = session_factory()
        state_machine.init_queue(path)
        payload = {
            "tool_name": "Write",
            "tool_input": {"file_path": "knowledge-base/slices/conference/web/room-chat.md"},
        }
        result = _run_gate(GATE_READ, payload, path)
        assert result.returncode == 0

    def test_allows_non_slice_file(self, session_factory):
        """Reading a non-slice file (e.g., README) is none of the gate's business."""
        path = session_factory()
        state_machine.init_queue(path)
        payload = {
            "tool_name": "Read",
            "tool_input": {"file_path": "README.md"},
        }
        result = _run_gate(GATE_READ, payload, path)
        assert result.returncode == 0

    def test_allows_current_slice_overview(self, session_factory):
        """Product-level overview for the current slice is allowed."""
        path = session_factory()
        state_machine.init_queue(path)
        payload = {
            "tool_name": "Read",
            "tool_input": {"file_path": "knowledge-base/slices/conference/login-auth.md"},
        }
        result = _run_gate(GATE_READ, payload, path)
        assert result.returncode == 0, result.stderr

    def test_allows_current_slice_platform_file(self, session_factory):
        """Platform-specific file for the current slice is allowed."""
        path = session_factory()
        state_machine.init_queue(path)
        payload = {
            "tool_name": "Read",
            "tool_input": {"file_path": "knowledge-base/slices/conference/web/login-auth.md"},
        }
        result = _run_gate(GATE_READ, payload, path)
        assert result.returncode == 0, result.stderr

    def test_blocks_next_slice_read(self, session_factory):
        """Reading the SECOND slice while cursor is on the first → exit 2."""
        path = session_factory()
        state_machine.init_queue(path)
        payload = {
            "tool_name": "Read",
            "tool_input": {"file_path": "knowledge-base/slices/conference/web/room-lifecycle.md"},
        }
        result = _run_gate(GATE_READ, payload, path)
        assert result.returncode == 2
        assert "current slice" in result.stderr.lower() or "login-auth" in result.stderr

    def test_blocks_unrelated_slice(self, session_factory):
        """Reading a slice not even in the queue → exit 2."""
        path = session_factory()
        state_machine.init_queue(path)
        payload = {
            "tool_name": "Read",
            "tool_input": {"file_path": "knowledge-base/slices/live/coguest-apply.md"},
        }
        result = _run_gate(GATE_READ, payload, path)
        assert result.returncode == 2

    def test_unit_mode_allows_any_slice_in_current_unit(self, session_factory):
        path = session_factory(
            execution_granularity="unit",
            confirmed_plan=[
                "conference/login-auth",
                "conference/room-lifecycle",
                "conference/room-chat",
            ],
        )
        state_machine.init_queue(path)
        payload = {
            "tool_name": "Read",
            "tool_input": {"file_path": "knowledge-base/slices/conference/web/room-lifecycle.md"},
        }
        result = _run_gate(GATE_READ, payload, path)
        assert result.returncode == 0, result.stderr

    def test_unit_mode_blocks_slice_outside_current_unit(self, session_factory):
        path = session_factory(
            execution_granularity="unit",
            confirmed_plan=[
                "conference/login-auth",
                "conference/room-lifecycle",
                "conference/room-chat",
            ],
        )
        state_machine.init_queue(path)
        payload = {
            "tool_name": "Read",
            "tool_input": {"file_path": "knowledge-base/slices/conference/web/room-chat.md"},
        }
        result = _run_gate(GATE_READ, payload, path)
        assert result.returncode == 2
        assert "current unit" in result.stderr or "foundation" in result.stderr

    def test_allows_absolute_path_to_current_slice(self, session_factory, tmp_path):
        """Absolute paths must also be matched, not just relative ones."""
        path = session_factory()
        state_machine.init_queue(path)
        abs_path = tmp_path / "anywhere/knowledge-base/slices/conference/web/login-auth.md"
        payload = {"tool_name": "Read", "tool_input": {"file_path": str(abs_path)}}
        result = _run_gate(GATE_READ, payload, path)
        assert result.returncode == 0, result.stderr

    def test_advances_to_next_slice_after_confirm(self, session_factory):
        """After full cycle, the second slice should be readable."""
        path = session_factory()
        state_machine.init_queue(path)
        for transition in [
            "mark_slice_read",
            "mark_code_written",
            "mark_apply_passed",
            "mark_user_confirmed",
        ]:
            state_machine.advance(path, transition)
        # Now cursor is on conference/room-lifecycle.
        payload = {
            "tool_name": "Read",
            "tool_input": {"file_path": "knowledge-base/slices/conference/web/room-lifecycle.md"},
        }
        result = _run_gate(GATE_READ, payload, path)
        assert result.returncode == 0, result.stderr

        # And login-auth (the previous slice) is now blocked, since we've moved on.
        payload2 = {
            "tool_name": "Read",
            "tool_input": {"file_path": "knowledge-base/slices/conference/web/login-auth.md"},
        }
        result2 = _run_gate(GATE_READ, payload2, path)
        assert result2.returncode == 2


# ---------- gate_slice_write ------------------------------------------------

class TestGateSliceWrite:
    def _project_file(self, session_factory) -> tuple[Path, Path]:
        """Return (session_path, file_path-inside-project-src)."""
        session_path = session_factory()
        data = yaml.safe_load(session_path.read_text())
        proj_root = Path(data["project_state"]["project_root"])
        proj_root.mkdir(parents=True, exist_ok=True)
        return session_path, proj_root / "src" / "views" / "MeetingRoom.vue"

    def test_allows_when_session_missing(self, tmp_path):
        payload = {
            "tool_name": "Write",
            "tool_input": {"file_path": str(tmp_path / "user-project/src/foo.vue")},
        }
        result = _run_gate(GATE_WRITE, payload, tmp_path / "missing.yaml")
        assert result.returncode == 0

    def test_allows_when_queue_not_initialised(self, session_factory):
        path, target = self._project_file(session_factory)
        payload = {"tool_name": "Write", "tool_input": {"file_path": str(target)}}
        result = _run_gate(GATE_WRITE, payload, path)
        assert result.returncode == 0

    def test_allows_non_write_tool(self, session_factory):
        path, target = self._project_file(session_factory)
        state_machine.init_queue(path)
        payload = {"tool_name": "Read", "tool_input": {"file_path": str(target)}}
        result = _run_gate(GATE_WRITE, payload, path)
        assert result.returncode == 0

    def test_allows_writes_outside_user_project(self, session_factory, tmp_path):
        """Writing to .claude/, knowledge-base/, /tmp etc. is not the gate's domain."""
        path, _target = self._project_file(session_factory)
        state_machine.init_queue(path)
        # current_execution_state == not_started would block a project write,
        # but this write is OUTSIDE the project root.
        outside = tmp_path / "elsewhere" / "scratch.md"
        payload = {"tool_name": "Write", "tool_input": {"file_path": str(outside)}}
        result = _run_gate(GATE_WRITE, payload, path)
        assert result.returncode == 0, result.stderr

    def test_blocks_write_when_state_not_started(self, session_factory):
        """Cursor sits on not_started → AI hasn't read the slice yet → block."""
        path, target = self._project_file(session_factory)
        state_machine.init_queue(path)
        payload = {"tool_name": "Write", "tool_input": {"file_path": str(target)}}
        result = _run_gate(GATE_WRITE, payload, path)
        assert result.returncode == 2
        assert "not_started" in result.stderr or "read" in result.stderr.lower()

    def test_allows_write_when_state_slice_read(self, session_factory):
        path, target = self._project_file(session_factory)
        state_machine.init_queue(path)
        state_machine.advance(path, "mark_slice_read")
        payload = {"tool_name": "Write", "tool_input": {"file_path": str(target)}}
        result = _run_gate(GATE_WRITE, payload, path)
        assert result.returncode == 0, result.stderr

    def test_allows_edit_when_state_code_written(self, session_factory):
        """Edit (during apply retry) is allowed in code_written state."""
        path, target = self._project_file(session_factory)
        state_machine.init_queue(path)
        state_machine.advance(path, "mark_slice_read")
        state_machine.advance(path, "mark_code_written")
        payload = {"tool_name": "Edit", "tool_input": {"file_path": str(target)}}
        result = _run_gate(GATE_WRITE, payload, path)
        assert result.returncode == 0, result.stderr

    def test_allows_edit_in_apply_failed(self, session_factory):
        """apply_failed → Edit is ALLOWED so the AI can retry after a fail.

        We deliberately do NOT enforce a "must re-read the slice first" rule
        here — the V1 walk-back removed that conditional gate (see
        docs/apply-skill-long-term-design.md §6.4 'walked back' list).
        """
        path, target = self._project_file(session_factory)
        state_machine.init_queue(path)
        state_machine.advance(path, "mark_slice_read")
        state_machine.advance(path, "mark_code_written")
        state_machine.advance(path, "mark_apply_failed")
        payload = {"tool_name": "Edit", "tool_input": {"file_path": str(target)}}
        result = _run_gate(GATE_WRITE, payload, path)
        assert result.returncode == 0, result.stderr

    def test_blocks_write_in_apply_passed(self, session_factory):
        """apply_passed → AI must wait for user confirmation, not keep editing."""
        path, target = self._project_file(session_factory)
        state_machine.init_queue(path)
        state_machine.advance(path, "mark_slice_read")
        state_machine.advance(path, "mark_code_written")
        state_machine.advance(path, "mark_apply_passed")
        payload = {"tool_name": "Write", "tool_input": {"file_path": str(target)}}
        result = _run_gate(GATE_WRITE, payload, path)
        assert result.returncode == 2
        assert "apply_passed" in result.stderr or "confirm" in result.stderr.lower()
