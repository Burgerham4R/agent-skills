"""Unit tests for .claude/skills/trtc/room-builder/guardrails/lib/session_state.py.

Tests grown TDD-style. Each pins one observable behavior of the helpers.

Why a dedicated test file (instead of testing only through prepare/verify):
- session_state is now a real module with multiple public functions.
- Catches contract bugs (e.g. ui_mode = "Full-UI" misnormalised) one layer
  closer to source.
- Lifecycle gate (scaffold_complete) is shared by both scripts; testing it
  in only one would leave the other surface untested.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / ".claude/skills/trtc/room-builder/guardrails"))

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

from lib import session_state


def _session(**fields):
    """Build a session dict inline. Lets each test be self-describing."""
    base = {
        "ui_mode": "full-ui",
        "product": "conference",
        "intent": "integrate-scenario",
        "scenario": "general-meeting",
        "project_state": {"project_root": "/tmp/whatever"},
    }
    base.update(fields)
    return base


# ---------------------------------------------------------------------------
# Test 1: scenario() returns the value when present
# ---------------------------------------------------------------------------


def test_scenario_returns_value_when_present():
    assert session_state.scenario(_session(scenario="webinar-large")) == "webinar-large"


# ---------------------------------------------------------------------------
# Test 2: scenario() returns None when missing
# ---------------------------------------------------------------------------


def test_scenario_returns_none_when_missing():
    s = _session()
    del s["scenario"]
    assert session_state.scenario(s) is None


# ---------------------------------------------------------------------------
# Test 3: in_scope False when scenario missing
# ---------------------------------------------------------------------------


def test_in_scope_false_when_scenario_missing():
    """Even with full-ui + valid project_root, no scenario → no scope."""
    s = _session()
    del s["scenario"]
    assert session_state.in_scope(s, REPO_ROOT) is False


# ---------------------------------------------------------------------------
# Test 4: in_scope False when scenario maps to TODO row
# ---------------------------------------------------------------------------


def test_in_scope_false_when_scenario_has_no_theme():
    """Telemedicine is in registry but has theme: ~. Scope must be False —
    a "registered TODO" is the same as "unknown" for hook purposes.
    """
    assert session_state.in_scope(_session(scenario="telemedicine"), REPO_ROOT) is False


# ---------------------------------------------------------------------------
# Test 5: in_scope True when scenario has a theme
# ---------------------------------------------------------------------------


def test_in_scope_true_when_scenario_has_theme():
    """The happy path: full-ui + general-meeting (themed) → in scope."""
    assert session_state.in_scope(_session(scenario="general-meeting"), REPO_ROOT) is True


# ---------------------------------------------------------------------------
# Test 6: in_scope False when scenario is unknown to registry
# ---------------------------------------------------------------------------


def test_in_scope_false_when_scenario_unknown():
    """Unknown scenario id → False (forgiving lookup, see registry test 4)."""
    assert session_state.in_scope(_session(scenario="never-heard-of"), REPO_ROOT) is False


# ===========================================================================
# Lifecycle gate: scaffold_complete()
# ===========================================================================
#
# These tests pin the signal "user has finished onboarding; hooks must close."
# Without this, the hook fires on every Claude Code turn forever — including
# while the user is editing their own UI code post-handoff. That's noise at
# best, actively wrong at worst (verifier flags legitimate user refactors).


# ---------------------------------------------------------------------------
# Test 7: -complete suffix → True (the live signal)
# ---------------------------------------------------------------------------


def test_scaffold_complete_true_when_step_ends_with_complete():
    """The actual production signal: A2.4-complete in onboarding."""
    s = _session()
    s["current_step"] = "A2.4-complete"
    assert session_state.scaffold_complete(s) is True


# ---------------------------------------------------------------------------
# Test 8: in-progress step → False
# ---------------------------------------------------------------------------


def test_scaffold_complete_false_when_step_does_not_end_with_complete():
    """While onboarding is mid-flight (A2.4 / A2.4-Q1 / etc.) hooks stay open."""
    s = _session()
    s["current_step"] = "A2.4"
    assert session_state.scaffold_complete(s) is False


# ---------------------------------------------------------------------------
# Test 9: missing field → False (gate stays open by default)
# ---------------------------------------------------------------------------


def test_scaffold_complete_false_when_field_missing():
    """Absent current_step (e.g. fresh session) → gate open. Anything else
    would mean a brand-new project's first hook would silently no-op."""
    s = _session()
    assert "current_step" not in s
    assert session_state.scaffold_complete(s) is False


# ---------------------------------------------------------------------------
# Test 10: explicit None → False
# ---------------------------------------------------------------------------


def test_scaffold_complete_false_when_step_is_none():
    """yaml `current_step: ~` parses to None. Must not crash on .endswith()."""
    s = _session()
    s["current_step"] = None
    assert session_state.scaffold_complete(s) is False


# ---------------------------------------------------------------------------
# Test 11: non-string defensive
# ---------------------------------------------------------------------------


def test_scaffold_complete_false_when_step_is_int():
    """Defensive: yaml-coerced int (e.g. someone wrote `current_step: 4`).
    Must not raise AttributeError on .endswith()."""
    s = _session()
    s["current_step"] = 4
    assert session_state.scaffold_complete(s) is False
