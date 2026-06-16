"""Tests for the slice-loop state machine.

Contract:
    init_queue(session_path) -> None
        Reads `confirmed_plan` from session, writes:
            execution_queue: [{id, type, slices, status}, ...]
            current_execution_index: 0
            current_execution_state: not_started
        Raises RuntimeError if confirmed_plan missing/empty.
        Idempotent: repeat calls with same plan are no-ops; calls with a
        different plan raise RuntimeError (the queue is frozen once set).

    current_slice(session_path) -> (index, slice_id, state)
        Returns the cursor. (None, None, None) if queue not initialised
        (PreToolUse hooks rely on this to detect "not in topic flow").

    advance(session_path, transition) -> new_state
        Allowed transitions:
            not_started   --mark_slice_read-->     slice_read
            slice_read    --mark_code_written-->   code_written
            code_written  --mark_apply_passed-->   apply_passed
            code_written  --mark_apply_failed-->   apply_failed
            apply_failed  --mark_code_written-->   code_written
            apply_passed  --mark_user_confirmed--> not_started (index += 1)

        At the end of the queue, advancing user_confirmed sets state to
        all_done. Further transitions raise RuntimeError.

        Any other (state, transition) pair raises RuntimeError.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

# state_machine lives in topic/scripts/lib/
STATE_MACHINE_DIR = Path(__file__).resolve().parents[1] / "scripts" / "lib"
sys.path.insert(0, str(STATE_MACHINE_DIR))
import state_machine  # noqa: E402
sys.path.pop(0)


# ---------- init_queue ----------

class TestInitQueue:
    def test_writes_queue_index_and_state(self, session_factory):
        path = session_factory()
        state_machine.init_queue(path)
        data = yaml.safe_load(path.read_text())
        assert data["execution_queue"] == [
            {"id": "conference/login-auth", "type": "slice", "title": "conference/login-auth", "status": "pending", "slices": ["conference/login-auth"]},
            {"id": "conference/room-lifecycle", "type": "slice", "title": "conference/room-lifecycle", "status": "pending", "slices": ["conference/room-lifecycle"]},
            {"id": "conference/participant-list", "type": "slice", "title": "conference/participant-list", "status": "pending", "slices": ["conference/participant-list"]},
            {"id": "conference/video-layout", "type": "slice", "title": "conference/video-layout", "status": "pending", "slices": ["conference/video-layout"]},
            {"id": "conference/device-control", "type": "slice", "title": "conference/device-control", "status": "pending", "slices": ["conference/device-control"]},
            {"id": "conference/network-quality", "type": "slice", "title": "conference/network-quality", "status": "pending", "slices": ["conference/network-quality"]},
        ]
        assert data["current_execution_index"] == 0
        assert data["current_execution_state"] == "not_started"

    def test_raises_when_confirmed_plan_missing(self, session_factory):
        path = session_factory(confirmed_plan=None)
        with pytest.raises(RuntimeError, match="confirmed_plan"):
            state_machine.init_queue(path)

    def test_raises_when_confirmed_plan_empty(self, session_factory):
        path = session_factory(confirmed_plan=[])
        with pytest.raises(RuntimeError, match="confirmed_plan"):
            state_machine.init_queue(path)

    def test_idempotent_when_plan_unchanged(self, session_factory):
        path = session_factory()
        state_machine.init_queue(path)
        # Advance once, so the cursor moves
        state_machine.advance(path, "mark_slice_read")
        # Calling init_queue again should NOT reset the cursor —
        # the same plan is already installed.
        state_machine.init_queue(path)
        data = yaml.safe_load(path.read_text())
        assert data["current_execution_state"] == "slice_read"
        assert data["current_execution_index"] == 0

    def test_raises_when_replan_differs(self, session_factory):
        path = session_factory()
        state_machine.init_queue(path)
        # Mutate confirmed_plan and try to re-init — must refuse.
        data = yaml.safe_load(path.read_text())
        data["confirmed_plan"] = ["conference/login-auth"]
        path.write_text(yaml.safe_dump(data, sort_keys=False))
        with pytest.raises(RuntimeError, match="frozen|differs"):
            state_machine.init_queue(path)


class TestInitDeliveryUnitQueue:
    def test_unit_mode_groups_confirmed_plan_without_adding_slices(self, session_factory):
        path = session_factory(
            execution_granularity="unit",
            confirmed_plan=[
                "conference/login-auth",
                "conference/room-lifecycle",
                "conference/video-layout",
                "conference/device-control",
                "conference/room-chat",
            ],
        )
        state_machine.init_queue(path)
        data = yaml.safe_load(path.read_text())

        assert [step["slices"] for step in data["execution_queue"]] == [
            ["conference/login-auth", "conference/room-lifecycle"],
            ["conference/video-layout"],
            ["conference/device-control"],
            ["conference/room-chat"],
        ]
        flattened = [
            sid
            for step in data["execution_queue"]
            for sid in step["slices"]
        ]
        assert flattened == data["confirmed_plan"]
        assert data["current_execution_index"] == 0
        assert data["current_execution_state"] == "not_started"

    def test_unit_mode_respects_declared_units_and_fills_missing_singletons(self, session_factory):
        path = session_factory(
            execution_granularity="unit",
            confirmed_plan=[
                "conference/login-auth",
                "conference/room-lifecycle",
                "conference/screen-share",
            ],
            delivery_units=[
                {
                    "id": "foundation",
                    "title": "基础链路",
                    "slices": ["conference/login-auth", "conference/room-lifecycle"],
                }
            ],
        )
        state_machine.init_queue(path)
        data = yaml.safe_load(path.read_text())
        assert [step["id"] for step in data["execution_queue"]] == [
            "foundation",
            "conference/screen-share",
        ]
        assert data["execution_queue"][1]["slices"] == ["conference/screen-share"]

    def test_unit_mode_without_scenario_config_uses_singletons(self, session_factory):
        path = session_factory(
            scenario="custom-scenario-without-unit-config",
            execution_granularity="unit",
            confirmed_plan=[
                "conference/login-auth",
                "conference/room-lifecycle",
            ],
        )
        state_machine.init_queue(path)
        data = yaml.safe_load(path.read_text())
        assert [step["type"] for step in data["execution_queue"]] == ["slice", "slice"]
        assert [step["slices"] for step in data["execution_queue"]] == [
            ["conference/login-auth"],
            ["conference/room-lifecycle"],
        ]


# ---------- current_slice ----------

class TestCurrentSlice:
    def test_returns_none_tuple_before_init(self, session_factory):
        path = session_factory()
        assert state_machine.current_slice(path) == (None, None, None)

    def test_returns_first_slice_after_init(self, session_factory):
        path = session_factory()
        state_machine.init_queue(path)
        assert state_machine.current_slice(path) == (
            0,
            "conference/login-auth",
            "not_started",
        )

    def test_returns_none_when_session_missing(self, tmp_path):
        path = tmp_path / "missing.yaml"
        assert state_machine.current_slice(path) == (None, None, None)

    def test_current_scope_reports_unit_slice_ids(self, session_factory):
        path = session_factory(
            execution_granularity="unit",
            confirmed_plan=["conference/login-auth", "conference/room-lifecycle"],
        )
        state_machine.init_queue(path)
        scope = state_machine.current_scope(path)
        assert scope["kind"] == "unit"
        assert scope["id"] == "foundation"
        assert scope["slice_ids"] == [
            "conference/login-auth",
            "conference/room-lifecycle",
        ]


# ---------- advance ----------

class TestAdvanceHappyPath:
    def test_full_cycle_advances_index(self, session_factory):
        path = session_factory()
        state_machine.init_queue(path)

        assert state_machine.advance(path, "mark_slice_read") == "slice_read"
        assert state_machine.advance(path, "mark_code_written") == "code_written"
        assert state_machine.advance(path, "mark_apply_passed") == "apply_passed"
        assert state_machine.advance(path, "mark_user_confirmed") == "not_started"

        idx, sid, st = state_machine.current_slice(path)
        assert idx == 1
        assert sid == "conference/room-lifecycle"
        assert st == "not_started"

    def test_apply_failed_then_retry(self, session_factory):
        path = session_factory()
        state_machine.init_queue(path)
        state_machine.advance(path, "mark_slice_read")
        state_machine.advance(path, "mark_code_written")
        assert state_machine.advance(path, "mark_apply_failed") == "apply_failed"
        # Retry: regenerate code, mark code_written again
        assert state_machine.advance(path, "mark_code_written") == "code_written"
        assert state_machine.advance(path, "mark_apply_passed") == "apply_passed"

    def test_reaches_all_done_on_last_confirm(self, session_factory):
        path = session_factory(confirmed_plan=["conference/login-auth"])
        state_machine.init_queue(path)
        state_machine.advance(path, "mark_slice_read")
        state_machine.advance(path, "mark_code_written")
        state_machine.advance(path, "mark_apply_passed")
        # Last slice — confirming should reach all_done, not advance index.
        assert state_machine.advance(path, "mark_user_confirmed") == "all_done"

    def test_marks_completed_slices_in_queue(self, session_factory):
        """execution_queue[i].status flips pending → done as we confirm each."""
        path = session_factory()
        state_machine.init_queue(path)
        state_machine.advance(path, "mark_slice_read")
        state_machine.advance(path, "mark_code_written")
        state_machine.advance(path, "mark_apply_passed")
        state_machine.advance(path, "mark_user_confirmed")
        data = yaml.safe_load(path.read_text())
        assert data["execution_queue"][0]["status"] == "done"
        assert data["execution_queue"][1]["status"] == "pending"

    def test_unit_cycle_marks_all_slices_in_unit_done(self, session_factory):
        path = session_factory(
            execution_granularity="unit",
            confirmed_plan=[
                "conference/login-auth",
                "conference/room-lifecycle",
                "conference/room-chat",
            ],
        )
        state_machine.init_queue(path)
        state_machine.advance(path, "mark_slice_read")
        state_machine.advance(path, "mark_code_written")
        state_machine.advance(path, "mark_apply_passed")
        assert state_machine.advance(path, "mark_user_confirmed") == "not_started"

        data = yaml.safe_load(path.read_text())
        assert data["execution_queue"][0]["status"] == "done"
        assert data["execution_queue"][1]["status"] == "pending"


class TestAdvanceIllegalTransitions:
    @pytest.mark.parametrize("bad_transition", [
        # From not_started: only mark_slice_read is legal.
        "mark_code_written",
        "mark_apply_passed",
        "mark_apply_failed",
        "mark_user_confirmed",
    ])
    def test_not_started_rejects(self, session_factory, bad_transition):
        path = session_factory()
        state_machine.init_queue(path)
        with pytest.raises(RuntimeError):
            state_machine.advance(path, bad_transition)

    def test_slice_read_rejects_apply(self, session_factory):
        path = session_factory()
        state_machine.init_queue(path)
        state_machine.advance(path, "mark_slice_read")
        with pytest.raises(RuntimeError):
            state_machine.advance(path, "mark_apply_passed")

    def test_apply_passed_rejects_repeat_apply(self, session_factory):
        path = session_factory()
        state_machine.init_queue(path)
        state_machine.advance(path, "mark_slice_read")
        state_machine.advance(path, "mark_code_written")
        state_machine.advance(path, "mark_apply_passed")
        with pytest.raises(RuntimeError):
            state_machine.advance(path, "mark_apply_passed")

    def test_unknown_transition_name(self, session_factory):
        path = session_factory()
        state_machine.init_queue(path)
        with pytest.raises(RuntimeError, match="unknown"):
            state_machine.advance(path, "mark_lunch_break")

    def test_advance_before_init_raises(self, session_factory):
        path = session_factory()
        with pytest.raises(RuntimeError, match="not initialised|init_queue"):
            state_machine.advance(path, "mark_slice_read")

    def test_advance_after_all_done_raises(self, session_factory):
        path = session_factory(confirmed_plan=["conference/login-auth"])
        state_machine.init_queue(path)
        state_machine.advance(path, "mark_slice_read")
        state_machine.advance(path, "mark_code_written")
        state_machine.advance(path, "mark_apply_passed")
        state_machine.advance(path, "mark_user_confirmed")  # all_done
        with pytest.raises(RuntimeError, match="all_done|finished|complete"):
            state_machine.advance(path, "mark_slice_read")


# ---------- Evidence auto-delete on user confirm ----------
#
# Successful slices' evidence JSON is deleted by mark_user_confirmed so the
# .trtc-apply-evidence/ directory ends a clean integration empty. Failed
# evidence is preserved (the slice still needs work; the next apply.py call
# will overwrite it).

import json


class TestEvidenceCleanup:
    def _evidence_path(self, session_path, slice_id):
        return session_path.parent / ".trtc-apply-evidence" / (
            slice_id.replace("/", "__") + ".json"
        )

    def _seed_evidence(self, session_path, slice_id, status="pass"):
        ev = self._evidence_path(session_path, slice_id)
        ev.parent.mkdir(parents=True, exist_ok=True)
        ev.write_text(json.dumps({"slice_id": slice_id, "status": status}))
        return ev

    def test_mark_user_confirmed_deletes_evidence(self, session_factory):
        path = session_factory()
        state_machine.init_queue(path)
        state_machine.advance(path, "mark_slice_read")
        state_machine.advance(path, "mark_code_written")
        state_machine.advance(path, "mark_apply_passed")

        ev = self._seed_evidence(path, "conference/login-auth")
        assert ev.exists()

        state_machine.advance(path, "mark_user_confirmed")
        assert not ev.exists(), "evidence should be deleted on confirm"

    def test_mark_user_confirmed_handles_missing_evidence(self, session_factory):
        """No evidence file → confirm still succeeds (no exception)."""
        path = session_factory()
        state_machine.init_queue(path)
        state_machine.advance(path, "mark_slice_read")
        state_machine.advance(path, "mark_code_written")
        state_machine.advance(path, "mark_apply_passed")

        # Don't seed an evidence file.
        ev = self._evidence_path(path, "conference/login-auth")
        assert not ev.exists()

        new_state = state_machine.advance(path, "mark_user_confirmed")
        assert new_state == "not_started"

    def test_apply_failed_evidence_not_deleted(self, session_factory):
        """apply_failed → mark_code_written retry → next apply overwrites.

        We don't get to mark_user_confirmed in this path, so evidence stays.
        Confirms the cleanup is bound to confirm, not to advance-in-general.
        """
        path = session_factory()
        state_machine.init_queue(path)
        state_machine.advance(path, "mark_slice_read")
        state_machine.advance(path, "mark_code_written")
        state_machine.advance(path, "mark_apply_failed")

        ev = self._seed_evidence(path, "conference/login-auth", status="fail")
        assert ev.exists()

        # Retry: regenerate code → mark_code_written. Evidence still there.
        state_machine.advance(path, "mark_code_written")
        assert ev.exists(), "fail-evidence must persist across retries"

    def test_evidence_deleted_for_each_slice_in_sequence(self, session_factory):
        """Two slices, both confirmed → both evidence files gone."""
        path = session_factory(
            confirmed_plan=["conference/login-auth", "conference/room-lifecycle"]
        )
        state_machine.init_queue(path)

        # Slice 0
        state_machine.advance(path, "mark_slice_read")
        state_machine.advance(path, "mark_code_written")
        state_machine.advance(path, "mark_apply_passed")
        ev0 = self._seed_evidence(path, "conference/login-auth")
        state_machine.advance(path, "mark_user_confirmed")
        assert not ev0.exists()

        # Slice 1
        state_machine.advance(path, "mark_slice_read")
        state_machine.advance(path, "mark_code_written")
        state_machine.advance(path, "mark_apply_passed")
        ev1 = self._seed_evidence(path, "conference/room-lifecycle")
        state_machine.advance(path, "mark_user_confirmed")
        assert not ev1.exists()
