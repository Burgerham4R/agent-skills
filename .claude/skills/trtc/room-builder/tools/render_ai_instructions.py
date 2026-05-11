#!/usr/bin/env python3
"""render_ai_instructions.py — Render ai-instructions/*.md to tool-specific entry files.

Sources: ai-instructions/*.md  (single source of truth, human-edited)
Targets:
  - AGENTS.md                    (for Codex / Aider / Cline / CodeBuddy)
  - CLAUDE.md                    (between AI-INSTRUCTIONS markers)
  - .cursor/rules/{name}.mdc     (one per source file; with Cursor frontmatter)

Grown TDD-style; see tests/unit/test_render_ai_instructions.py.
"""
import argparse
import sys
from pathlib import Path


def _sources(project_root):
    """Return sorted list of .md source files under ai-instructions/."""
    src_dir = project_root / "ai-instructions"
    if not src_dir.exists():
        return []
    return sorted(src_dir.glob("*.md"))


# Single source-of-truth banner. Reused across all derived targets so the
# message stays identical and contributors can grep for "DO NOT EDIT" to
# find every generated file.
_BANNER = (
    "<!-- DO NOT EDIT — generated from ai-instructions/ by "
    ".claude/skills/trtc/room-builder/tools/render_ai_instructions.py. "
    "Edit the source markdown and re-run the renderer instead. -->"
)


def _render_agents_md(project_root):
    """Regenerate AGENTS.md by concatenating all sources with H1 per file."""
    sources = _sources(project_root)
    parts = [_BANNER + "\n"]
    for src in sources:
        parts.append(f"# {src.stem}\n\n{src.read_text().rstrip()}\n")
    (project_root / "AGENTS.md").write_text("\n".join(parts) if sources else _BANNER + "\n")


BEGIN_MARKER = "<!-- AI-INSTRUCTIONS:BEGIN -->"
END_MARKER = "<!-- AI-INSTRUCTIONS:END -->"


def _demote_headings(body):
    """Add one '#' to every ATX heading line.

    `## Foo` → `### Foo`, `### Foo` → `#### Foo`, etc. Lines that aren't
    headings are returned unchanged. Used in CLAUDE.md so body sections
    nest under the renderer-prepended `## {name}` parent.
    """
    out = []
    for line in body.splitlines():
        # Match an ATX heading: 1-6 '#' followed by a space.
        stripped = line.lstrip()
        if stripped.startswith("#"):
            hashes = len(stripped) - len(stripped.lstrip("#"))
            if 1 <= hashes <= 5 and stripped[hashes:hashes + 1] == " ":
                # Preserve leading whitespace (rare in markdown but safe).
                lead = line[:len(line) - len(stripped)]
                out.append(f"{lead}#{stripped}")
                continue
        out.append(line)
    return "\n".join(out)


def _rendered_block(project_root):
    """The string content placed between markers in CLAUDE.md.

    Section headers are H2 (`## {name}`). Body headings are demoted by one
    level so they nest as children of the section header instead of
    appearing as adjacent siblings. Banner placed first so a casual reader
    sees the warning before any rendered content.
    """
    sources = _sources(project_root)
    parts = [_BANNER + "\n"]
    for src in sources:
        body = _demote_headings(src.read_text().rstrip())
        parts.append(f"## {src.stem}\n\n{body}\n")
    return "\n".join(parts)


def _render_claude_md(project_root):
    """Update CLAUDE.md in place between AI-INSTRUCTIONS markers.

    If markers exist: replace content strictly between them.
    If markers don't exist: append markers + rendered block at EOF.
    Content outside the markers is never touched.
    """
    claude_path = project_root / "CLAUDE.md"
    existing = claude_path.read_text() if claude_path.exists() else ""
    block = _rendered_block(project_root)
    marker_block = f"{BEGIN_MARKER}\n{block}\n{END_MARKER}\n"

    if BEGIN_MARKER in existing and END_MARKER in existing:
        begin = existing.index(BEGIN_MARKER)
        end = existing.index(END_MARKER) + len(END_MARKER)
        # Preserve trailing newline behavior from the original end-marker position.
        trailing_nl = "\n" if end < len(existing) and existing[end] == "\n" else ""
        new = existing[:begin] + marker_block.rstrip("\n") + trailing_nl + existing[end + len(trailing_nl):]
        claude_path.write_text(new)
    else:
        # Append block at EOF (with a blank line separator).
        sep = "" if existing.endswith("\n\n") or not existing else ("\n" if existing.endswith("\n") else "\n\n")
        claude_path.write_text(existing + sep + marker_block)


def _render_cursor_rules(project_root):
    """One .cursor/rules/{name}.mdc per source file, with Cursor frontmatter.

    Banner placed AFTER the frontmatter so Cursor's YAML parser still works.
    """
    rules_dir = project_root / ".cursor" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    for src in _sources(project_root):
        target = rules_dir / f"{src.stem}.mdc"
        body = src.read_text().rstrip()
        target.write_text(
            "---\n"
            "alwaysApply: true\n"
            "---\n"
            "\n"
            f"{_BANNER}\n"
            "\n"
            f"{body}\n"
        )


def _check_targets_up_to_date(project_root):
    """Compare current target contents to what would be rendered.

    Returns a list of stale target paths (relative to project_root). Empty
    list = everything in sync.

    Implementation: render to a temporary in-memory representation and diff
    against current file contents. The cleanest way is to capture what
    each render function would write before it writes; rather than
    refactoring all three to return strings, we copy the current targets
    out, run the renderers, diff, then restore on mismatch (so --check
    has no side effect on the working tree).
    """
    targets = ["AGENTS.md", "CLAUDE.md"]
    rules_dir = project_root / ".cursor" / "rules"
    for src in _sources(project_root):
        targets.append(f".cursor/rules/{src.stem}.mdc")

    # Snapshot current contents.
    snapshot = {}
    for rel in targets:
        p = project_root / rel
        snapshot[rel] = p.read_bytes() if p.exists() else None

    # Run render to compute new contents.
    _render_agents_md(project_root)
    _render_claude_md(project_root)
    _render_cursor_rules(project_root)

    stale = []
    for rel in targets:
        p = project_root / rel
        new = p.read_bytes() if p.exists() else None
        if new != snapshot[rel]:
            stale.append(rel)

    # Restore original contents so --check has no side effect.
    for rel, original in snapshot.items():
        p = project_root / rel
        if original is None:
            if p.exists():
                p.unlink()
        else:
            p.write_bytes(original)
    return stale


def main():
    parser = argparse.ArgumentParser(description="Render ai-instructions/*.md to tool files.")
    parser.add_argument("--project-root", default=".",
                        help="Repo root (defaults to CWD)")
    parser.add_argument("--check", action="store_true",
                        help="Exit 2 if any target is stale (CI mode); no writes.")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()

    if args.check:
        stale = _check_targets_up_to_date(root)
        if stale:
            print("render_ai_instructions: stale targets:", file=sys.stderr)
            for s in stale:
                print(f"  {s}", file=sys.stderr)
            print("Re-run `python3 .claude/skills/trtc/room-builder/tools/render_ai_instructions.py` and commit the diff.",
                  file=sys.stderr)
            return 2
        return 0

    _render_agents_md(root)
    _render_claude_md(root)
    _render_cursor_rules(root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
