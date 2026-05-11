"""Unit tests for .claude/skills/trtc/room-builder/tools/render_scenario_mapping.py.

The renderer turns scenarios.yaml → scenario-mapping.md. Tests pin the
output format because topic SKILL.md Step 3.5 reads the .md as a
human-style table — column order matters, TODO marker matters.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / ".claude/skills/trtc/room-builder/guardrails"))

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / ".claude/skills/trtc/room-builder/tools" / "render_scenario_mapping.py"


def _make_kb(tmp_path, yaml_text):
    """Build a minimal tmp KB with scenarios.yaml only.

    The renderer reads via REPO_ROOT (computed from __file__), so the
    test has to copy scripts/ into the tmp KB the same way prepare/verify
    multi-theme tests do.
    """
    import shutil as _sh
    kb = tmp_path / "tmp-kb"
    yaml_dir = kb / ".claude/skills/trtc/room-builder/references"
    yaml_dir.mkdir(parents=True)
    (yaml_dir / "scenarios.yaml").write_text(yaml_text)
    _sh.copytree(REPO_ROOT / ".claude/skills/trtc/room-builder/guardrails", kb / ".claude/skills/trtc/room-builder/guardrails")
    _sh.copytree(REPO_ROOT / ".claude/skills/trtc/room-builder/tools", kb / ".claude/skills/trtc/room-builder/tools")
    return kb


def _md_path(kb):
    return kb / ".claude/skills/trtc/room-builder/references/scenario-mapping.md"


def _run_render(kb, *args):
    return subprocess.run(
        ["python3", str(kb / ".claude/skills/trtc/room-builder/tools" / "render_scenario_mapping.py"), *args],
        capture_output=True, text=True, cwd=str(kb),
    )


# ---------------------------------------------------------------------------
# Test 1: AUTO-GENERATED warning header at top of output
# ---------------------------------------------------------------------------


def test_render_writes_header_and_doc_warning(tmp_path):
    """First lines of output warn the reader 'don't edit me'.

    Without this, a contributor opens scenario-mapping.md, edits it,
    runs bootstrap.sh, and is confused why their edit reverted. The
    warning must name the source yaml AND the renderer command so the
    fix path is obvious.
    """
    kb = _make_kb(tmp_path,
        "version: 1\n"
        "scenarios:\n"
        "  - id: x\n"
        "    path: x/\n"
        "    template: y\n"
        "    reference_html: y/index.html\n"
        '    notes: ""\n'
        "    theme: ~\n"
    )
    result = _run_render(kb)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    content = _md_path(kb).read_text()
    head = content[:600]
    assert "DO NOT EDIT" in head.upper(), f"header must warn DO NOT EDIT; got:\n{head}"
    assert "scenarios.yaml" in head, f"header must name source yaml; got:\n{head}"
    assert "render_scenario_mapping.py" in head, (
        f"header must name renderer; got:\n{head}"
    )


# ---------------------------------------------------------------------------
# Test 2: yaml-document order preserved (NOT alphabetical)
# ---------------------------------------------------------------------------


def test_render_includes_all_scenarios_in_yaml_order(tmp_path):
    """Yaml [c, a, b] → md rows in c, a, b order.

    Humans control the order in yaml (e.g. listing high-priority
    scenarios first). Alphabetising would steal that knob.
    """
    kb = _make_kb(tmp_path,
        "version: 1\n"
        "scenarios:\n"
        "  - id: c-id\n    path: c/\n    template: ~\n    reference_html: ~\n    notes: ''\n    theme: ~\n"
        "  - id: a-id\n    path: a/\n    template: ~\n    reference_html: ~\n    notes: ''\n    theme: ~\n"
        "  - id: b-id\n    path: b/\n    template: ~\n    reference_html: ~\n    notes: ''\n    theme: ~\n"
    )
    result = _run_render(kb)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    content = _md_path(kb).read_text()
    pos_c = content.index("c-id")
    pos_a = content.index("a-id")
    pos_b = content.index("b-id")
    assert pos_c < pos_a < pos_b, (
        f"rows must be in yaml order; got c={pos_c}, a={pos_a}, b={pos_b}"
    )


# ---------------------------------------------------------------------------
# Test 3: theme: ~ row → (TODO) markers in template & reference HTML cols
# ---------------------------------------------------------------------------


def test_render_writes_todo_for_missing_template_and_reference(tmp_path):
    """A scenario with `theme: ~` and `template: ~` shows up as (TODO).

    Pins that humans reading the .md immediately see which scenarios
    still need a theme. Empty cells would look like editor accidents.
    """
    kb = _make_kb(tmp_path,
        "version: 1\n"
        "scenarios:\n"
        "  - id: telemed\n"
        "    path: telemed/\n"
        "    template: ~\n"
        "    reference_html: ~\n"
        "    notes: 'TODO: add theme.'\n"
        "    theme: ~\n"
    )
    result = _run_render(kb)
    assert result.returncode == 0
    row = next(
        line for line in _md_path(kb).read_text().splitlines()
        if "telemed" in line and line.startswith("|")
    )
    assert "(TODO)" in row, f"TODO marker must appear in row; got: {row!r}"


# ---------------------------------------------------------------------------
# Test 4: column header in canonical order (downstream contract)
# ---------------------------------------------------------------------------


def test_render_columns_in_canonical_order(tmp_path):
    """Column header is `scenario | path | template | reference HTML | notes`.

    topic SKILL.md Step 3.5 reads this table to find each scenario's
    reference HTML. If we reorder columns, that read breaks. Pinning
    here keeps the contract explicit.
    """
    kb = _make_kb(tmp_path,
        "version: 1\n"
        "scenarios:\n"
        "  - id: x\n    path: x/\n    template: ~\n    reference_html: ~\n    notes: ''\n    theme: ~\n"
    )
    _run_render(kb)
    content = _md_path(kb).read_text()
    # Locate the markdown header line.
    header = next(l for l in content.splitlines() if "scenario" in l and "path" in l and l.startswith("|"))
    assert header == "| scenario | path | template | reference HTML | notes |", (
        f"column order must be exact; got: {header!r}"
    )


# ---------------------------------------------------------------------------
# Test 5: trailing newline (POSIX; prevents --check git-diff false positives)
# ---------------------------------------------------------------------------


def test_render_emits_trailing_newline(tmp_path):
    kb = _make_kb(tmp_path,
        "version: 1\n"
        "scenarios:\n"
        "  - id: x\n    path: x/\n    template: ~\n    reference_html: ~\n    notes: ''\n    theme: ~\n"
    )
    _run_render(kb)
    content = _md_path(kb).read_text()
    assert content.endswith("\n"), f"output must end with newline; got: ...{content[-30:]!r}"


# ---------------------------------------------------------------------------
# Test 6: --check passes when md matches yaml
# ---------------------------------------------------------------------------


def test_check_mode_passes_when_md_matches_yaml(tmp_path):
    """Render then --check → exit 0. The CI guard's happy path."""
    kb = _make_kb(tmp_path,
        "version: 1\n"
        "scenarios:\n"
        "  - id: x\n    path: x/\n    template: ~\n    reference_html: ~\n    notes: ''\n    theme: ~\n"
    )
    assert _run_render(kb).returncode == 0
    check = _run_render(kb, "--check")
    assert check.returncode == 0, f"check must pass; stderr: {check.stderr}"


# ---------------------------------------------------------------------------
# Test 7: --check fails when yaml mutated without re-rendering
# ---------------------------------------------------------------------------


def test_check_mode_fails_when_yaml_changed(tmp_path):
    """Mutate yaml, run --check → exit 2 with stale path in stderr."""
    kb = _make_kb(tmp_path,
        "version: 1\n"
        "scenarios:\n"
        "  - id: x\n    path: x/\n    template: ~\n    reference_html: ~\n    notes: ''\n    theme: ~\n"
    )
    assert _run_render(kb).returncode == 0
    yaml_path = kb / ".claude/skills/trtc/room-builder/references/scenarios.yaml"
    yaml_path.write_text(yaml_path.read_text() +
        "  - id: y\n    path: y/\n    template: ~\n    reference_html: ~\n    notes: ''\n    theme: ~\n"
    )
    check = _run_render(kb, "--check")
    assert check.returncode == 2, f"check must fail; got {check.returncode}"
    assert "scenario-mapping.md" in check.stderr, (
        f"stderr must name stale path; got: {check.stderr!r}"
    )


# ---------------------------------------------------------------------------
# Test 8: --check fails when md is hand-edited
# ---------------------------------------------------------------------------


def test_check_mode_fails_when_md_hand_edited(tmp_path):
    """Render then mutate the md → --check exit 2.

    Pins the symmetric case to test 7. If only "yaml changed" failed we
    could regress and not notice when someone edits the md directly.
    """
    kb = _make_kb(tmp_path,
        "version: 1\n"
        "scenarios:\n"
        "  - id: x\n    path: x/\n    template: ~\n    reference_html: ~\n    notes: ''\n    theme: ~\n"
    )
    assert _run_render(kb).returncode == 0
    md = _md_path(kb)
    md.write_text(md.read_text() + "\n## A handwritten section\n")
    check = _run_render(kb, "--check")
    assert check.returncode == 2, f"check must fail; got {check.returncode}"


# ---------------------------------------------------------------------------
# Test 9: regression — real yaml renders to byte-equal committed md
# ---------------------------------------------------------------------------


def test_render_against_real_scenarios_yaml_matches_committed_md():
    """Real repo: yaml → render in memory → byte-compare with committed md.

    This is the catch-all: every commit that bumps yaml must also bump md.
    Without this regression guard, someone edits yaml, forgets re-render,
    and topic SKILL.md serves stale content.
    """
    result = subprocess.run(
        ["python3", str(SCRIPT), "--check"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"committed scenario-mapping.md must match yaml; "
        f"re-run `python3 .claude/skills/trtc/room-builder/tools/render_scenario_mapping.py` and commit. "
        f"Stderr: {result.stderr}"
    )
