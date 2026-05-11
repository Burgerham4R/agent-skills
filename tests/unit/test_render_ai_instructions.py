"""Unit tests for .claude/skills/trtc/room-builder/tools/render_ai_instructions.py.

Renders ai-instructions/*.md → tool-specific entry files. Tests pin the
rendering contract — they don't care what the content says, only how it
lands in each target format.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / ".claude/skills/trtc/room-builder/guardrails"))

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / ".claude/skills/trtc/room-builder/tools" / "render_ai_instructions.py"


def _run_render(project_root, *args):
    """Invoke renderer with --project-root pointing at a fake repo."""
    return subprocess.run(
        ["python3", str(SCRIPT), "--project-root", str(project_root), *args],
        capture_output=True,
        text=True,
    )


def _make_fake_repo(tmp_path):
    """Set up a minimal fake repo: ai-instructions/ + empty CLAUDE.md stub."""
    root = tmp_path / "fake-repo"
    (root / "ai-instructions").mkdir(parents=True)
    (root / "CLAUDE.md").write_text("# Existing human-authored content\n\nHello world.\n")
    return root


# ---------------------------------------------------------------------------
# Test 1: AGENTS.md is generated from a single source file
# ---------------------------------------------------------------------------


def test_generates_agents_md_from_single_source(tmp_path):
    """`ai-instructions/foo.md` → `AGENTS.md` contains `# foo` section + body.

    Codex / Aider / Cline all consume AGENTS.md; this pins the most basic
    shape: H1 section per source file, body beneath.
    """
    repo = _make_fake_repo(tmp_path)
    (repo / "ai-instructions" / "foo.md").write_text("Body of foo.\n\nAnother line.\n")
    result = _run_render(repo)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    agents = (repo / "AGENTS.md").read_text()
    assert "# foo" in agents, f"AGENTS.md must have `# foo` heading; got:\n{agents}"
    assert "Body of foo." in agents, f"AGENTS.md must contain body; got:\n{agents}"


# ---------------------------------------------------------------------------
# Test 2: CLAUDE.md — content above markers is preserved across renders
# ---------------------------------------------------------------------------


BEGIN = "<!-- AI-INSTRUCTIONS:BEGIN -->"
END = "<!-- AI-INSTRUCTIONS:END -->"


def test_claude_md_preserves_content_above_markers(tmp_path):
    """CLAUDE.md with existing content + markers → only between-markers swaps.

    Critical: CLAUDE.md is heavily hand-edited (routing policy, language rule,
    etc.). A renderer that nukes that content every run would be a disaster.
    This pins the safety property.
    """
    repo = _make_fake_repo(tmp_path)
    hand_written = "# Hand-authored\n\nImportant rules the human wrote.\n"
    (repo / "CLAUDE.md").write_text(
        hand_written
        + f"\n{BEGIN}\n"
        + "OLD GENERATED CONTENT\n"
        + f"{END}\n"
        + "\n# After the markers, also hand-authored\n"
    )
    (repo / "ai-instructions" / "foo.md").write_text("Body of foo.\n")

    result = _run_render(repo)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    body = (repo / "CLAUDE.md").read_text()

    # Hand-authored content above the marker region is untouched.
    assert hand_written.strip() in body, f"head content must survive; got:\n{body}"
    # Hand-authored content after the end marker is untouched.
    assert "After the markers, also hand-authored" in body
    # Generated content between markers is replaced.
    assert "OLD GENERATED CONTENT" not in body, f"old gen content must go; got:\n{body}"
    assert "Body of foo." in body, f"new gen content must appear; got:\n{body}"


# ---------------------------------------------------------------------------
# Test 3: CLAUDE.md without markers → markers + content appended at EOF
# ---------------------------------------------------------------------------


def test_claude_md_adds_markers_if_missing(tmp_path):
    """Virgin CLAUDE.md (no markers yet) → render appends markers + block.

    First-run migration: existing repos already have a CLAUDE.md with no
    marker region. We must graft the block on without dropping anything.
    """
    repo = _make_fake_repo(tmp_path)
    (repo / "ai-instructions" / "foo.md").write_text("Body of foo.\n")
    result = _run_render(repo)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    body = (repo / "CLAUDE.md").read_text()
    assert "# Existing human-authored content" in body, "original content must survive"
    assert BEGIN in body and END in body, f"markers must be added; got:\n{body}"
    assert body.index(BEGIN) > body.index("Existing human-authored"), (
        "markers must be appended AFTER existing content"
    )
    assert "Body of foo." in body


# ---------------------------------------------------------------------------
# Test 4: .cursor/rules/{name}.mdc has Cursor frontmatter
# ---------------------------------------------------------------------------


def test_cursor_mdc_has_frontmatter(tmp_path):
    """foo.md → .cursor/rules/foo.mdc starts with `--- alwaysApply: true ---`.

    Cursor only applies a rule unconditionally if `alwaysApply: true` is in
    the frontmatter. Without this, the rule sits dormant and the model
    ignores it.
    """
    repo = _make_fake_repo(tmp_path)
    (repo / "ai-instructions" / "foo.md").write_text("Body of foo.\n")
    result = _run_render(repo)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    mdc = repo / ".cursor" / "rules" / "foo.mdc"
    assert mdc.exists(), f".cursor/rules/foo.mdc must be created; tree:\n{list(repo.rglob('*'))}"
    body = mdc.read_text()
    assert "Body of foo." in body


# ---------------------------------------------------------------------------
# Test 5: multiple sources rendered in deterministic (alphabetical) order
# ---------------------------------------------------------------------------


def test_multiple_sources_rendered_in_deterministic_order(tmp_path):
    """`a.md` + `b.md` → AGENTS.md sections appear in alphabetical order.

    Stable diffs matter: if two contributors run render on the same sources
    and get different orderings, every commit looks like a renderer bug.
    Alphabetical order is the simplest stable choice.
    """
    repo = _make_fake_repo(tmp_path)
    (repo / "ai-instructions" / "b.md").write_text("Body B\n")
    (repo / "ai-instructions" / "a.md").write_text("Body A\n")
    (repo / "ai-instructions" / "c.md").write_text("Body C\n")
    result = _run_render(repo)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    agents = (repo / "AGENTS.md").read_text()
    a_pos = agents.index("# a")
    b_pos = agents.index("# b")
    c_pos = agents.index("# c")
    assert a_pos < b_pos < c_pos, (
        f"sections must be in alphabetical order; got positions a={a_pos}, b={b_pos}, c={c_pos}"
    )


# ---------------------------------------------------------------------------
# Test 6: --check passes when targets are up-to-date
# ---------------------------------------------------------------------------


def test_check_mode_passes_when_targets_match(tmp_path):
    """render then --check → exit 0 (no changes needed).

    --check is for CI: run after every PR to ensure derived files are
    in sync with sources. Pass means "nothing to regenerate".
    """
    repo = _make_fake_repo(tmp_path)
    (repo / "ai-instructions" / "foo.md").write_text("Body of foo.\n")
    assert _run_render(repo).returncode == 0
    check = _run_render(repo, "--check")
    assert check.returncode == 0, f"check must pass after render; stderr: {check.stderr}"


# ---------------------------------------------------------------------------
# Test 7: --check fails (exit 2) when source has been changed without re-render
# ---------------------------------------------------------------------------


def test_check_mode_fails_when_source_changed(tmp_path):
    """render → mutate source → --check → exit 2 with stale path in stderr.

    This is the CI guard: catches the contributor who edits ai-instructions/
    but forgets to re-run render.
    """
    repo = _make_fake_repo(tmp_path)
    (repo / "ai-instructions" / "foo.md").write_text("Original body.\n")
    assert _run_render(repo).returncode == 0
    # Mutate the source without re-rendering.
    (repo / "ai-instructions" / "foo.md").write_text("Mutated body.\n")
    check = _run_render(repo, "--check")
    assert check.returncode == 2, f"check must fail after source change; got {check.returncode}"
    assert "AGENTS.md" in check.stderr or "CLAUDE.md" in check.stderr or "foo.mdc" in check.stderr, (
        f"stderr must name the stale target; got: {check.stderr!r}"
    )


# ---------------------------------------------------------------------------
# Test 8: CLAUDE.md demotes body headings by one level inside the marker block
# ---------------------------------------------------------------------------


def test_claude_md_demotes_body_headings(tmp_path):
    """In CLAUDE.md, source body headings are demoted by one level so the
    renderer-prepended `## {name}` is the parent of the body's sections.

    Why: CLAUDE.md uses `## {name}` as the per-source section header. If
    the body keeps its own `## When …` headings, you get two adjacent
    H2s and the body sections are siblings of the section name instead
    of children of it. Demoting H2→H3 (and H3→H4 etc.) inside the
    marker block fixes the visual hierarchy.

    AGENTS.md is unaffected: it uses `# {name}` (H1) as the parent, so
    body H2s already nest correctly.
    """
    repo = _make_fake_repo(tmp_path)
    (repo / "ai-instructions" / "foo.md").write_text(
        "## Top-level body section\n\n"
        "Some content.\n\n"
        "### Nested\n\n"
        "More content.\n"
    )
    result = _run_render(repo)
    assert result.returncode == 0, f"stderr: {result.stderr}"

    claude = (repo / "CLAUDE.md").read_text()
    # Slice out the marker block.
    block = claude[claude.index(BEGIN):claude.index(END) + len(END)]

    # The renderer-prepended section header must remain H2.
    assert "## foo" in block, f"section header must be H2; got block:\n{block}"

    # Body H2 must be demoted to H3 inside the block.
    block_lines = block.splitlines()
    assert "### Top-level body section" in block_lines, (
        f"body H2 must be demoted to H3 in CLAUDE.md; got block:\n{block}"
    )
    assert "## Top-level body section" not in block_lines, (
        f"body H2 must not appear undemoted in CLAUDE.md; got block:\n{block}"
    )
    # And H3 must demote to H4.
    assert "#### Nested" in block_lines, f"body H3 must demote to H4; got block:\n{block}"

    # AGENTS.md (regression guard): body headings stay at original level
    # because the section parent there is H1.
    agents = (repo / "AGENTS.md").read_text().splitlines()
    assert "## Top-level body section" in agents, (
        f"AGENTS.md must keep body H2 (parent is H1); got: {agents}"
    )


# ---------------------------------------------------------------------------
# Test 9: derived files carry a DO-NOT-EDIT banner pointing at the source
# ---------------------------------------------------------------------------


def test_derived_files_have_do_not_edit_banner(tmp_path):
    """Every derived target must include a banner that:
      (a) names ai-instructions/ as the source of truth,
      (b) names render_ai_instructions.py as the regenerator,
      (c) includes the literal text 'DO NOT EDIT' (case-insensitive).

    Without this, a contributor opening AGENTS.md sees plain markdown and
    edits in place — their work gets overwritten on next bootstrap. The
    banner is the loudest possible signal that the file is generated.

    Three targets, three nuances:
      - AGENTS.md: HTML comment near the top (markdown ignores it visually).
      - .cursor/rules/*.mdc: HTML comment AFTER the frontmatter so Cursor's
        YAML parser still works.
      - CLAUDE.md: banner goes inside the AI-INSTRUCTIONS marker block.
    """
    repo = _make_fake_repo(tmp_path)
    (repo / "ai-instructions" / "foo.md").write_text("Body of foo.\n")
    result = _run_render(repo)
    assert result.returncode == 0, f"stderr: {result.stderr}"

    def _has_banner(text, *, source_label):
        """Single banner contract — same checks for every target."""
        return all((
            "DO NOT EDIT" in text.upper(),
            "ai-instructions/" in text,
            "render_ai_instructions.py" in text,
        )), source_label

    # AGENTS.md banner near the top (within first 500 bytes is plenty).
    agents = (repo / "AGENTS.md").read_text()
    ok, label = _has_banner(agents[:500], source_label="AGENTS.md head")
    assert ok, f"AGENTS.md must start with a DO-NOT-EDIT banner; got head:\n{agents[:500]}"

    # .cursor/rules/foo.mdc — banner must appear AFTER the frontmatter.
    mdc = (repo / ".cursor" / "rules" / "foo.mdc").read_text()
    # Find end of frontmatter (second '---').
    parts = mdc.split("---", 2)
    assert len(parts) >= 3, f"frontmatter must be intact; got:\n{mdc}"
    after_frontmatter = parts[2]
    ok, label = _has_banner(after_frontmatter[:500], source_label="foo.mdc body head")
    assert ok, (
        f"foo.mdc must have a DO-NOT-EDIT banner after the frontmatter; "
        f"got after-frontmatter head:\n{after_frontmatter[:500]}"
    )

    # CLAUDE.md banner inside the marker block.
    claude = (repo / "CLAUDE.md").read_text()
    block = claude[claude.index(BEGIN):claude.index(END) + len(END)]
    ok, label = _has_banner(block, source_label="CLAUDE.md marker block")
    assert ok, f"CLAUDE.md marker block must contain banner; got:\n{block}"
