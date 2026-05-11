#!/usr/bin/env python3
"""trtc_verify_ui.py — Verify the user project meets ui_mode=full-ui contract.

This script is grown TDD-style; each commit adds the minimum logic for one
test. See tests/unit/test_trtc_verify_ui.py.

# Hook design lesson — THREE gates protect this script

Hooks (especially Stop / SessionStart) are powerful: their stderr is read
by the model and rewrites the model's understanding of "what's wrong."
That power becomes a footgun if the hook fires when it shouldn't. We
learned this the hard way: an early version of this script (with only the
ui_mode check) yelled V2/V3/V4 while the model was still in onboarding
asking "which platform?" — the model assumed those errors were the user's
real problem, dropped onboarding, and started scaffolding.

Three orthogonal gates now protect against premature/wrong firing:

    LIFECYCLE GATE (lib/session_state.scaffold_complete)
      "is onboarding done?"
        session.current_step ends with "-complete"
      → Closed: hook exits 0 silently. User owns the code from this point;
        any further UI tweaks are out of scope.

    SCOPE GATE (lib/session_state.in_scope)
      "is this our session?"
        ui_mode == full-ui  AND
        product  == conference  AND
        intent   == integrate-scenario  AND
        session.scenario maps to a registered theme
      → Closed: hook exits 0 silently. The session is some other workflow.

    READINESS GATE (_vue_app_started)
      "has the user started the Vue app?"
        index.html exists  OR
        src/main.ts|main.js exists  OR
        any *.vue under src/
      → Closed: hook exits 0 silently. User is still in pre-Vue phase.

All three open → V1-V4 enforce.

# Generalisation for future hooks

When you add a hook, classify it:
  - Always-fire   (compile errors, lint violations)        — never gate
  - Phase-aware   (only inside one workflow phase)         — readiness gate
  - Scope-gated   (only for specific product/intent/etc.)  — scope gate
  - Lifecycle-gated (closes after a milestone)             — lifecycle gate
Most "Always-fire" hooks turn out to be at least Phase-aware on closer look.
"""
import argparse
import re
import sys
from pathlib import Path

# Prefer the shared helper so prepare/verify can't drift on session parsing.
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


def _vue_app_started(project_root):
    """Has the user begun scaffolding the Vue app at all?

    Returns True if any of these signals exists:
      - index.html at project root
      - src/main.ts or src/main.js
      - any *.vue file under src/

    Returns False for "barren" projects — including the immediate post-
    `trtc_prepare_ui.py` state where only src/themes/ exists. In that
    state the verifier must NOT fire: the user/model is still in
    onboarding and full-ui contract isn't applicable yet.
    """
    if (project_root / "index.html").exists():
        return True
    if (project_root / "src" / "main.ts").exists():
        return True
    if (project_root / "src" / "main.js").exists():
        return True
    src = project_root / "src"
    if src.exists() and any(src.rglob("*.vue")):
        return True
    return False


def _check_themes_dir(project_root, theme):
    """V1: src/<theme.target_dir>/index.css must exist.

    Returns an error message (str) if the check fails, or None on pass.
    """
    expected = project_root / theme.target_dir / "index.css"
    if expected.exists():
        return None
    return (
        f"V1: missing {expected} — "
        f"run `python3 .claude/skills/trtc/room-builder/guardrails/trtc_prepare_ui.py` "
        f"to copy the {theme.slug} theme into {project_root}/src/themes/."
    )


def _find_entrypoint(project_root):
    """Return the first existing of src/main.ts, src/main.js, or None."""
    for name in ("main.ts", "main.js"):
        p = project_root / "src" / name
        if p.exists():
            return p
    return None


def _check_main_import(project_root, theme):
    """V2: src/main.ts (or .js) must import the theme's index.css.

    Returns an error message (str) if the check fails, or None on pass.
    """
    entry = _find_entrypoint(project_root)
    if entry is None:
        return (
            f"V2: missing entrypoint — expected {project_root}/src/main.ts or main.js."
        )
    body = entry.read_text()
    if theme.import_path in body:
        return None
    return (
        f"V2: {entry} is missing the theme import — "
        f"add `import '{theme.import_path}'` near the top, "
        f"or run `python3 .claude/skills/trtc/room-builder/guardrails/trtc_prepare_ui.py` to do it automatically."
    )


_HTML_TAG_RE = re.compile(r"<html\b([^>]*)>", re.IGNORECASE)


def _check_data_theme(project_root, theme):
    """V3: index.html's <html> tag must carry data-theme="<theme.data_theme>".

    Returns an error message (str) if the check fails, or None on pass.
    """
    html_path = project_root / "index.html"
    if not html_path.exists():
        return f"V3: missing {html_path}."
    body = html_path.read_text()
    m = _HTML_TAG_RE.search(body)
    if m is None:
        return f"V3: {html_path} has no <html> tag."
    expected_attr = f'data-theme="{theme.data_theme}"'
    if expected_attr in m.group(0):
        return None
    return (
        f"V3: {html_path} <html> tag is missing {expected_attr} — "
        f"add it (e.g. `<html lang=\"zh-CN\" {expected_attr}>`) "
        f"or run `python3 .claude/skills/trtc/room-builder/guardrails/trtc_prepare_ui.py`."
    )


# Match `class="...ui-..."` (the visible-attribute form). Both
#   class="ui-stage"
#   class="ui-stage ui-tile"
# count once per `ui-foo` token.
_UI_CLASS_ANY_RE = re.compile(r'\bui-[a-zA-Z0-9_-]+')


def _count_ui_classes_in_vue(vue_path):
    """Count distinct `ui-*` class occurrences inside `class="..."` attributes.

    A multi-class attribute like `class="ui-stage ui-tile"` counts as 2.
    """
    body = vue_path.read_text()
    count = 0
    for m in re.finditer(r'class="([^"]*)"', body):
        attr = m.group(1)
        count += len(_UI_CLASS_ANY_RE.findall(attr))
    return count


def _check_aggregate_ui_classes(project_root, total_min):
    """V4 (aggregate): sum of ui-* classes across all src/**/*.vue must reach total_min.

    Returns (error_message_or_None, total_count). Theme-agnostic — V4 just
    counts the convention.
    """
    src = project_root / "src"
    total = 0
    files = sorted(src.rglob("*.vue")) if src.exists() else []
    for f in files:
        total += _count_ui_classes_in_vue(f)
    if total >= total_min:
        return (None, total)
    return (
        f"V4: project has {total} ui-* class(es) across {len(files)} .vue file(s) "
        f"(need ≥{total_min}). The theme requires uikit classes "
        f"from .claude/skills/trtc/room-builder/uikit/references/component-catalog.md "
        f"on every interactive element.",
        total,
    )


def main():
    parser = argparse.ArgumentParser(description="Verify ui_mode=full-ui contract.")
    parser.add_argument("--session-path", default=".trtc-session.yaml",
                        help="Path to .trtc-session.yaml (defaults to CWD)")
    parser.add_argument("--file", default=None,
                        help="Verify only this single .vue file (PostToolUse mode)")
    parser.add_argument("--per-file-min", type=int, default=3,
                        help="Minimum ui-* classes required per .vue file (default 3)")
    parser.add_argument("--total-min", type=int, default=30,
                        help="Minimum total ui-* classes across project (default 30)")
    args = parser.parse_args()

    session = _load_session(Path(args.session_path))
    if session is None:
        return 0

    # Lifecycle gate FIRST. Once onboarding is complete, the user owns the
    # code; verifier must close — even in --file mode (a hook firing per
    # keystroke after handoff is exactly the noise the gate eliminates).
    if _session_scaffold_complete(session):
        return 0

    # Scope gate: ui_mode + product + intent + scenario-has-theme.
    if not _session_in_scope(session, REPO_ROOT):
        return 0

    project_root = _project_root(session)
    if project_root is None:
        return 0

    # Resolve theme params for this scenario (in_scope verified non-None).
    reg = load_registry(REPO_ROOT)
    theme = theme_for_scenario(reg, _session_scenario(session))

    # Single-file mode: check only V4 on the named file.
    if args.file:
        vue_path = Path(args.file)
        if not vue_path.exists() or vue_path.suffix != ".vue":
            return 0  # not a .vue file — silently skip (Write hook fires on every file)
        count = _count_ui_classes_in_vue(vue_path)
        if count < args.per_file_min:
            print(
                f"V4: {vue_path} has only {count} ui-* class(es) (need ≥{args.per_file_min}). "
                f"See .claude/skills/trtc/room-builder/uikit/references/component-catalog.md "
                f"for the catalog of ui-* classes to use.",
                file=sys.stderr,
            )
            return 2
        return 0

    # Project-readiness gate: don't fire on a project that hasn't started yet.
    if not _vue_app_started(project_root):
        return 0

    errors = []
    err = _check_themes_dir(project_root, theme)
    if err:
        errors.append(err)
    err = _check_main_import(project_root, theme)
    if err:
        errors.append(err)
    err = _check_data_theme(project_root, theme)
    if err:
        errors.append(err)
    err, _total = _check_aggregate_ui_classes(project_root, args.total_min)
    if err:
        errors.append(err)

    if errors:
        for line in errors:
            print(line, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
