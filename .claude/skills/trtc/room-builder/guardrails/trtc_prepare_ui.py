#!/usr/bin/env python3
"""trtc_prepare_ui.py — Idempotently wire up ui_mode=full-ui artifacts.

Three operations against `project_state.project_root`:
  P1: Copy the scenario's theme into src/themes/<theme-slug>/
  P2: Add `import '@/themes/<theme-slug>/index.css'` to src/main.{ts,js}
  P3: Add `data-theme="<theme-data-attr>"` to <html> in index.html

All three are idempotent — re-running is safe.

Theme parameters come from the registry (`guardrails/lib/theme_registry.py`)
keyed by `session.scenario`. To add a new theme, edit
`.claude/skills/trtc/room-builder/references/scenarios.yaml`; no code change
in this file. See MAINTAINING-SCENARIOS.md.

Two gates protect this script (see lib/session_state.py for definitions):
  1. Lifecycle gate (scaffold_complete): once onboarding's `current_step`
     ends with `-complete`, the user owns the code. Hooks exit 0 silently.
  2. Scope gate (in_scope): ui_mode + product + intent + scenario-has-theme
     all must hold. Otherwise this isn't our session to govern.

Grown TDD-style; see tests/unit/test_trtc_prepare_ui.py.
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.session_state import (
    load_session,
    project_root as _session_project_root,
    in_scope as _session_in_scope,
    scaffold_complete as _session_scaffold_complete,
    scenario as _session_scenario,
)
from lib.theme_registry import load_registry, theme_for_scenario


REPO_ROOT = Path(__file__).resolve().parents[5]


def _load_session(session_path):
    return load_session(session_path)


def _project_root(session):
    return _session_project_root(session)


def _copy_theme(project_root, theme, *, dry_run):
    """P1: Copy theme.source_dir into project_root/<theme.target_dir>/.

    Returns a human-readable summary line.
    """
    dest = project_root / theme.target_dir
    if dry_run:
        return f"P1 (dry-run): would copy {theme.source_dir} → {dest}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    # dirs_exist_ok=True so re-running is safe. Follows template_fetcher.py
    # convention but without ignore_patterns (themes have no build artifacts).
    shutil.copytree(theme.source_dir, dest, dirs_exist_ok=True)
    return f"P1: copied {theme.slug} theme → {dest}"


def _import_line(theme):
    """The literal source-code line written into main.ts / main.js for P2."""
    return f"import '{theme.import_path}'"


def _find_entrypoint(project_root):
    """Return the first existing of src/main.ts, src/main.js, or None."""
    for name in ("main.ts", "main.js"):
        p = project_root / "src" / name
        if p.exists():
            return p
    return None


def _patch_entrypoint(project_root, theme, *, dry_run):
    """P2: Ensure the entrypoint imports the theme's index.css.

    Idempotent: if `theme.import_path` already appears anywhere in the file,
    do nothing. Otherwise prepend the import line.
    """
    entry = _find_entrypoint(project_root)
    if entry is None:
        return f"P2: skipped — no src/main.ts or src/main.js found in {project_root}"
    body = entry.read_text()
    if theme.import_path in body:
        return f"P2: {entry.name} already imports theme (no-op)"
    line = _import_line(theme)
    if dry_run:
        return f"P2 (dry-run): would prepend `{line}` to {entry}"
    entry.write_text(line + "\n" + body)
    return f"P2: added theme import to {entry}"


_HTML_TAG_RE = re.compile(r"<html\b([^>]*)>", re.IGNORECASE)


def _patch_index_html(project_root, theme, *, dry_run):
    """P3: Ensure <html> has data-theme="<theme.data_theme>".

    Idempotent: if already present, no-op. Otherwise inject the attribute
    while preserving existing attributes (lang, etc.).
    """
    html_path = project_root / "index.html"
    if not html_path.exists():
        return f"P3: skipped — {html_path} not found"
    body = html_path.read_text()
    m = _HTML_TAG_RE.search(body)
    if m is None:
        return f"P3: skipped — no <html> tag in {html_path}"
    expected_attr = f'data-theme="{theme.data_theme}"'
    if expected_attr in m.group(0):
        return f"P3: index.html already has {expected_attr} (no-op)"
    if dry_run:
        return f"P3 (dry-run): would add {expected_attr} to <html> in {html_path}"
    # Preserve existing attributes. group(1) is whatever came after "html".
    existing_attrs = m.group(1)
    new_tag = f'<html{existing_attrs} {expected_attr}>'
    new_body = body[:m.start()] + new_tag + body[m.end():]
    html_path.write_text(new_body)
    return f"P3: added {expected_attr} to <html> in {html_path}"


def main():
    parser = argparse.ArgumentParser(description="Prepare ui_mode=full-ui artifacts.")
    parser.add_argument("--session-path", default=".trtc-session.yaml")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would change, don't write.")
    args = parser.parse_args()

    session = _load_session(Path(args.session_path))
    if session is None:
        return 0

    # Lifecycle gate FIRST (cheaper than registry load): once onboarding has
    # marked the workflow complete, the user owns the code — this script
    # must not touch the project. Subsequent UI tweaks are out of scope.
    if _session_scaffold_complete(session):
        return 0

    # Scope gate: ui_mode + product + intent + scenario-has-theme.
    # The meeting-classic-style themes are conference-specific; copying any
    # of them into a non-conference product would corrupt unrelated work.
    if not _session_in_scope(session, REPO_ROOT):
        return 0

    project_root = _project_root(session)
    if project_root is None:
        print("trtc_prepare_ui: session has ui_mode=full-ui but no project_state.project_root",
              file=sys.stderr)
        return 1
    if not project_root.exists():
        print(
            f"trtc_prepare_ui: project_root does not exist: {project_root}\n"
            f"  Fix project_state.project_root in .trtc-session.yaml.",
            file=sys.stderr,
        )
        return 1

    # Resolve the theme for this scenario. in_scope() above already
    # verified theme is non-None; this lookup is to fetch the params.
    reg = load_registry(REPO_ROOT)
    theme = theme_for_scenario(reg, _session_scenario(session))

    summary = []
    summary.append(_copy_theme(project_root, theme, dry_run=args.dry_run))
    summary.append(_patch_entrypoint(project_root, theme, dry_run=args.dry_run))
    summary.append(_patch_index_html(project_root, theme, dry_run=args.dry_run))
    for line in summary:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
