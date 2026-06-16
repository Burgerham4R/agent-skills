"""Execution-step state machine for the topic skill.

The state machine is the enforcement mechanism for topic execution. It stores a
single ``execution_queue`` in ``.trtc-session.yaml``. Each execution step has a
uniform shape:

    {id, type: "slice" | "unit", status, slices: [...]}

Slices remain the knowledge and rule source. Execution steps define how many
slices are delivered in one read/write/apply loop.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import yaml


_TRANSITIONS = {
    ("not_started", "mark_slice_read"): "slice_read",
    ("slice_read", "mark_code_written"): "code_written",
    ("code_written", "mark_apply_passed"): "apply_passed",
    ("code_written", "mark_apply_failed"): "apply_failed",
    ("apply_failed", "mark_code_written"): "code_written",
    ("apply_passed", "mark_user_confirmed"): "ADVANCE_INDEX",
}

_KNOWN_TRANSITIONS = {t for (_state, t) in _TRANSITIONS.keys()}
_TOPIC_ROOT = Path(__file__).resolve().parents[2]
_EXECUTION_UNITS_PATH = _TOPIC_ROOT / "references" / "execution-units.yaml"


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text()) or {}


def _save(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def _step_id_from_slices(slice_ids: list[str]) -> str:
    if len(slice_ids) == 1:
        return slice_ids[0]
    return "__".join(s.split("/", 1)[1] for s in slice_ids)


def _step_type(slice_ids: list[str]) -> str:
    return "unit" if len(slice_ids) > 1 else "slice"


def _make_step(step_id: str, title: str, slice_ids: list[str], *, status: str = "pending") -> dict:
    return {
        "id": step_id,
        "type": _step_type(slice_ids),
        "title": title,
        "status": status,
        "slices": slice_ids,
    }


def _build_declared_unit_steps(raw_units, plan: list[str]) -> list[dict]:
    """Group only slices already present in confirmed_plan."""
    configured = [
        sid
        for raw in raw_units or []
        for sid in (raw.get("slices") or [])
    ]
    duplicates = sorted({sid for sid in configured if configured.count(sid) > 1})
    if duplicates:
        raise RuntimeError("delivery unit config contains duplicate slices: " + ", ".join(duplicates))

    remaining = list(plan)
    steps: list[dict] = []

    for raw in raw_units or []:
        group = raw.get("slices") or []
        slice_ids = [sid for sid in group if sid in remaining]
        if len(slice_ids) < 2:
            continue
        step_id = raw.get("id") or _step_id_from_slices(slice_ids)
        steps.append(_make_step(step_id, raw.get("title") or step_id, slice_ids))
        for sid in slice_ids:
            remaining.remove(sid)

    for sid in remaining:
        steps.append(_make_step(sid, sid, [sid]))

    order = {sid: i for i, sid in enumerate(plan)}
    steps.sort(key=lambda step: min(order[sid] for sid in step["slices"]))
    return steps


def _scenario_delivery_units(data: dict) -> list[dict]:
    scenario = data.get("scenario")
    if not scenario or not _EXECUTION_UNITS_PATH.exists():
        return []
    config = yaml.safe_load(_EXECUTION_UNITS_PATH.read_text()) or {}
    return (
        (config.get("scenarios") or {})
        .get(scenario, {})
        .get("delivery_units")
        or []
    )


def _build_slice_steps(plan: list[str]) -> list[dict]:
    return [_make_step(sid, sid, [sid]) for sid in plan]


def _flatten_slices(queue: list[dict]) -> list[str]:
    return [sid for step in queue for sid in step.get("slices", [])]


def _execution_queue_from_legacy(data: dict) -> list[dict] | None:
    """Best-effort read compatibility for old sessions."""
    if data.get("execution_queue"):
        return data["execution_queue"]
    if data.get("delivery_unit_queue"):
        return [
            _make_step(
                entry.get("id") or _step_id_from_slices(entry.get("slices", [])),
                entry.get("title") or entry.get("id") or "",
                entry.get("slices", []),
                status=entry.get("status", "pending"),
            )
            for entry in data["delivery_unit_queue"]
        ]
    if data.get("slice_queue"):
        return [
            _make_step(entry.get("id"), entry.get("id"), [entry.get("id")], status=entry.get("status", "pending"))
            for entry in data["slice_queue"]
            if entry.get("id")
        ]
    return None


def _current_index_state(data: dict) -> tuple[int, str]:
    if "current_execution_index" in data or "current_execution_state" in data:
        return data.get("current_execution_index", 0), data.get("current_execution_state") or "not_started"
    if data.get("execution_granularity") in {"unit", "delivery_unit"}:
        return data.get("current_unit_index", 0), data.get("current_unit_state") or "not_started"
    return data.get("current_slice_index", 0), data.get("current_slice_state") or "not_started"


def init_queue(session_path) -> None:
    """Materialise ``confirmed_plan`` into ``execution_queue``.

    Idempotent when the queue already covers the same confirmed_plan. Refuses
    re-init if the plan changed after topic took ownership.
    """
    path = Path(session_path)
    data = _load(path)
    plan = data.get("confirmed_plan")
    if not plan:
        raise RuntimeError(
            "confirmed_plan is missing or empty in session — onboarding A2 "
            "should have populated it before topic ran init_queue."
        )

    expected_ids = list(plan)
    existing_queue = data.get("execution_queue")
    if existing_queue is not None:
        if _flatten_slices(existing_queue) != expected_ids:
            raise RuntimeError(
                "execution_queue is frozen and differs from confirmed_plan — "
                "remove execution_queue / current_execution_index / "
                "current_execution_state from the session file and run init again."
            )
        return

    if data.get("execution_granularity") in {"unit", "delivery_unit"}:
        raw_units = data.get("delivery_units") or _scenario_delivery_units(data)
        queue = _build_declared_unit_steps(raw_units, expected_ids)
    else:
        queue = _build_slice_steps(expected_ids)

    data["execution_queue"] = queue
    data["current_execution_index"] = 0
    data["current_execution_state"] = "not_started"
    _save(path, data)


def current_scope(session_path) -> dict:
    """Return the active execution step."""
    path = Path(session_path)
    if not path.exists():
        return {"initialised": False, "reason": "session file missing"}

    data = _load(path)
    queue = _execution_queue_from_legacy(data)
    if not queue:
        return {"initialised": False, "reason": "execution_queue not set"}

    idx, state = _current_index_state(data)
    if state == "all_done":
        return {
            "initialised": True,
            "kind": "execution",
            "index": idx,
            "state": "all_done",
            "total": len(queue),
            "id": None,
            "title": None,
            "type": None,
            "slice_ids": [],
            "queue": queue,
        }
    if idx is None or idx < 0 or idx >= len(queue):
        return {"initialised": False, "reason": "execution cursor out of range"}

    step = queue[idx]
    slice_ids = step.get("slices") or [step.get("id")]
    return {
        "initialised": True,
        "kind": step.get("type", _step_type(slice_ids)),
        "index": idx,
        "state": state,
        "total": len(queue),
        "id": step.get("id"),
        "title": step.get("title") or step.get("id"),
        "type": step.get("type", _step_type(slice_ids)),
        "slice_ids": slice_ids,
        "queue": queue,
    }


def current_slice(session_path) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    """Compatibility helper returning the first slice in the current step."""
    scope = current_scope(session_path)
    if not scope.get("initialised"):
        return (None, None, None)
    if scope.get("state") == "all_done":
        return (scope.get("index"), None, "all_done")
    slice_ids = scope.get("slice_ids") or []
    return (scope.get("index"), slice_ids[0] if slice_ids else None, scope.get("state"))


def advance(session_path, transition: str) -> str:
    if transition not in _KNOWN_TRANSITIONS:
        raise RuntimeError(
            f"unknown transition '{transition}'. Known transitions: "
            f"{sorted(_KNOWN_TRANSITIONS)}"
        )

    path = Path(session_path)
    data = _load(path)
    queue = data.get("execution_queue")
    if not queue:
        legacy = _execution_queue_from_legacy(data)
        if legacy:
            queue = legacy
            data["execution_queue"] = queue
        else:
            raise RuntimeError("execution_queue not initialised — call init_queue() before advance().")

    state = data.get("current_execution_state")
    idx = data.get("current_execution_index", 0)
    if state is None:
        legacy_idx, legacy_state = _current_index_state(data)
        idx = legacy_idx
        state = legacy_state
        data["current_execution_index"] = idx
        data["current_execution_state"] = state

    if state == "all_done":
        raise RuntimeError(
            "all_done — the execution queue is finished; no further transitions "
            "are allowed. Start a new scenario or reset the session."
        )

    next_state = _TRANSITIONS.get((state, transition))
    if next_state is None:
        raise RuntimeError(
            f"illegal transition '{transition}' from state '{state}'. "
            f"Allowed from '{state}': "
            f"{sorted(t for (s, t) in _TRANSITIONS.keys() if s == state)}"
        )

    if next_state == "ADVANCE_INDEX":
        step = queue[idx]
        step["status"] = "done"
        evidence_ids = [step.get("id"), *step.get("slices", [])]
        for evidence_id in [eid for eid in evidence_ids if eid]:
            ev_path = path.parent / ".trtc-apply-evidence" / (evidence_id.replace("/", "__") + ".json")
            try:
                ev_path.unlink()
            except FileNotFoundError:
                pass

        new_idx = idx + 1
        data["execution_queue"] = queue
        data["current_execution_index"] = new_idx
        data["current_execution_state"] = "all_done" if new_idx >= len(queue) else "not_started"
        _save(path, data)
        return data["current_execution_state"]

    data["execution_queue"] = queue
    data["current_execution_state"] = next_state
    _save(path, data)
    return next_state


def status(session_path) -> dict:
    path = Path(session_path)
    if not path.exists():
        return {"initialised": False, "reason": "session file missing"}
    data = _load(path)
    queue = _execution_queue_from_legacy(data)
    if not queue:
        return {"initialised": False, "reason": "execution_queue not set"}

    idx, state = _current_index_state(data)
    current = queue[idx] if idx < len(queue) else None
    slice_ids = (current.get("slices") if current else None) or []
    step_type = current.get("type", _step_type(slice_ids)) if current else None
    return {
        "initialised": True,
        "kind": step_type or "execution",
        "index": idx,
        "state": state,
        "total": len(queue),
        "current_slice_id": slice_ids[0] if slice_ids else None,
        "current_unit_id": current.get("id") if current and step_type == "unit" else None,
        "current_id": current.get("id") if current else None,
        "slice_ids": slice_ids,
        "queue": queue,
    }
