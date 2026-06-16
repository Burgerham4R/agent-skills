"""Tests for finalize_session.py session normalization."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml


FINALIZE_SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "finalize_session.py"
)


def test_finalize_session_normalizes_completed_topic_session(session_factory):
    path = session_factory(
        status="active",
        current_step="topic-handoff",
        completed_steps=[
            "conference/login-auth",
            "conference/room-lifecycle",
            "conference/room-lifecycle",
        ],
        execution_queue=[
            {"id": "conference/login-auth", "type": "slice", "slices": ["conference/login-auth"], "status": "done"},
            {"id": "foundation", "type": "unit", "slices": ["conference/room-lifecycle", "conference/video-layout"], "status": "pending"},
        ],
        current_execution_index=2,
        current_execution_state="all_done",
    )

    result = subprocess.run(
        [sys.executable, str(FINALIZE_SCRIPT), "--session", str(path)],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    data = yaml.safe_load(path.read_text())
    assert data["status"] == "completed"
    assert data["current_step"] == "completed"
    assert data["current_execution_index"] == 2
    assert data["current_execution_state"] == "all_done"
    assert data["completed_steps"] == [
        "conference/login-auth",
        "conference/room-lifecycle",
        "conference/video-layout",
    ]
    assert [entry["status"] for entry in data["execution_queue"]] == ["done", "done"]
    assert "last_recap" in data
