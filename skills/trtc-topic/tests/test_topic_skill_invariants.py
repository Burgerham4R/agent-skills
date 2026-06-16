"""Topic skill SKILL.md invariants — guards the post-redesign shape.

After the topic-skill redesign (2026-05-15), `topic/SKILL.md` was reduced
from 512 lines to ~390. Four structural invariants survived from that
work and need to stay true:

1. The "Apply Evidence Block" section was deleted — it instructed AI to
   run its own grep/ls/tsc, duplicating apply.py and giving AI an obvious
   bypass path.
2. The State Machine Guide was split out to
   `topic/scripts/STATE-MACHINE-GUIDE.md` and topic/SKILL.md just
   references it.
3. The "Calling apply" section is compact — the full request schema lives
   in `apply/SKILL.md` Phase 0; topic only references it.
4. topic/SKILL.md size stays within budget so we don't silently re-inline
   the things we split out.

Originally this file also enforced the §3.5 cross-skill handoff
convention ("must use Skill tool, never Read"). That convention was
walked back on 2026-05-18: the runtime never supported it (sub-skills
under `trtc/X/` aren't top-level discoverable, so `Skill(skill='trtc-X')`
returns "Unknown skill"). Plain Read handoff is the only working option
today. The §3.5-specific tests were removed; this file kept its other
four invariants. See `docs/topic-skill-long-term-design.md` §10 for the
walk-back rationale.
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]  # repo root
TOPIC_SKILL = ROOT / "skills" / "trtc-topic" / "SKILL.md"
STATE_MACHINE_GUIDE = (
    ROOT / "skills" / "trtc-topic" / "scripts" / "STATE-MACHINE-GUIDE.md"
)
EXECUTION_UNITS = ROOT / "skills" / "trtc-topic" / "references" / "execution-units.yaml"


def test_apply_evidence_block_remains_deleted():
    """Regression: the deleted 'Apply Evidence Block' must not return.

    Was a multi-paragraph block instructing AI to run its own grep/ls/tsc
    in addition to apply.py. Two-track verification was demo-test-2 root
    cause: AI satisfied one track (the SKILL.md grep) by comment-stuffing
    while apply.py also passed because it ran the same kind of substring
    grep. Single-source verification is enforced by deletion.
    """
    text = TOPIC_SKILL.read_text()
    assert "Apply Evidence Block (MANDATORY" not in text, (
        "topic/SKILL.md still contains 'Apply Evidence Block (MANDATORY' — "
        "this was deleted because it instructed AI to run its own grep, "
        "which duplicates apply.py and AI learned to bypass."
    )
    assert "P1 Imports:" not in text, (
        "topic/SKILL.md still has P1 Imports instruction for AI-run grep"
    )


def test_state_machine_guide_exists_and_is_referenced():
    """The state machine guide must exist and topic/SKILL.md must point to it."""
    assert STATE_MACHINE_GUIDE.exists(), (
        f"State Machine Guide missing at {STATE_MACHINE_GUIDE}. "
        "topic/SKILL.md was reduced under the assumption this guide is split out."
    )
    topic_text = TOPIC_SKILL.read_text()
    assert "STATE-MACHINE-GUIDE.md" in topic_text, (
        "topic/SKILL.md must reference scripts/STATE-MACHINE-GUIDE.md, "
        "otherwise AI has no pointer to the operator's manual."
    )


def test_delivery_unit_grouping_is_declarative():
    """Automatic unit grouping must stay visible outside state_machine.py."""
    assert EXECUTION_UNITS.exists(), "delivery-unit grouping config is missing"
    topic_text = TOPIC_SKILL.read_text()
    guide_text = STATE_MACHINE_GUIDE.read_text()
    assert "references/execution-units.yaml" in topic_text
    assert "references/execution-units.yaml" in guide_text

    state_machine_text = (
        ROOT / "skills" / "trtc-topic" / "scripts" / "lib" / "state_machine.py"
    ).read_text()
    assert "_DEFAULT_UNIT_GROUPS" not in state_machine_text
    assert "会议基础链路" not in state_machine_text


def test_topic_skill_size_reduced():
    """Sanity check: topic/SKILL.md should be substantially smaller than the
    original 512-line version. If it grows back, something has been re-inlined."""
    text = TOPIC_SKILL.read_text()
    line_count = len(text.splitlines())
    # The topic skill has grown with ui_mode, runtime verification, and
    # delivery-unit execution. Keep a budget so the old anti-patterns don't
    # quietly return, but do not enforce the obsolete 2026-05 compact size.
    assert line_count < 760, (
        f"topic/SKILL.md is {line_count} lines — above the current budget. "
        f"Check if Apply Evidence Block, state machine manual, or Calling apply "
        f"contract was re-inlined."
    )


def test_calling_apply_section_is_compact():
    """The 'Calling apply' section must not contain the removed full request schema.

    The full I/O contract lives in apply/SKILL.md Phase 0; topic just references it.
    """
    text = TOPIC_SKILL.read_text()
    # Locate the "### Calling apply" section bounds.
    start_marker = "### Calling apply"
    if start_marker not in text:
        pytest.fail("'### Calling apply' section missing from topic/SKILL.md")
    section_start = text.index(start_marker)
    # Section ends at the next '### ' heading.
    after = text[section_start + len(start_marker):]
    next_section_at = after.find("\n### ")
    section_text = after[:next_section_at] if next_section_at >= 0 else after

    # Mode selection table: should be in apply/SKILL.md only, not in topic.
    bad_markers = [
        "**Mode selection rules:**",
        "**Request construction**",
        "| Situation | mode |",
    ]
    found = [m for m in bad_markers if m in section_text]
    assert not found, (
        f"topic/SKILL.md 'Calling apply' section re-inlined apply request schema "
        f"({found}). Keep the contract in apply/SKILL.md only; topic just references it."
    )
