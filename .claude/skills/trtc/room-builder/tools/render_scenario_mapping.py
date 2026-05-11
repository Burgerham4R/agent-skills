#!/usr/bin/env python3
"""render_scenario_mapping.py — Render scenarios.yaml → scenario-mapping.md.

scenarios.yaml is the single source of truth for scenario → UI template/theme
mapping. The .md file is human-readable derivation: topic SKILL.md Step 3.5
reads it for the `reference HTML` column.

CLI:
    python3 scripts/render_scenario_mapping.py            # render
    python3 scripts/render_scenario_mapping.py --check    # exit 2 if stale

Render rules (pinned by tests):
- Header has a DO-NOT-EDIT warning naming the source yaml + this script.
- Column order: scenario | path | template | reference HTML | notes
- Order = yaml document order (NOT alphabetical — humans control order).
- `theme: ~` / `template: ~` / `reference_html: ~` rows show "(TODO)" in
  template + reference_html columns; empty notes shows empty string.
- File ends with a trailing newline (POSIX).

bootstrap.sh runs this every setup. CI runs `--check` to catch
"edited yaml, forgot to re-render".
"""
import argparse
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[5]
YAML_REL = ".claude/skills/trtc/room-builder/references/scenarios.yaml"
MD_REL = ".claude/skills/trtc/room-builder/references/scenario-mapping.md"


_HEADER = (
    "<!-- DO NOT EDIT — generated from scenarios.yaml by "
    ".claude/skills/trtc/room-builder/tools/render_scenario_mapping.py. "
    "Edit the source yaml and re-run the renderer instead. -->\n"
    "<!-- See MAINTAINING-SCENARIOS.md for how to add scenarios. -->\n"
    "\n"
    "# Scenario → UI Template / Theme\n"
    "\n"
)
_TABLE_HEADER = (
    "| scenario | path | template | reference HTML | notes |\n"
    "|---|---|---|---|---|\n"
)


def _todo_or(value):
    """Render a yaml value as a markdown cell.

    None / null → "(TODO)" so humans see "this needs filling in".
    Empty string → empty string (used for notes column).
    """
    if value is None:
        return "(TODO)"
    return str(value)


def _render_md(yaml_path):
    """Pure function: yaml file → rendered .md content (str).

    Separated from file IO so tests can ask "does this yaml render to that
    md?" without disk roundtrips.
    """
    raw = yaml.safe_load(yaml_path.read_text())
    rows = []
    for entry in raw["scenarios"]:
        scenario_id = entry["id"]
        path = entry.get("path") or ""
        template = _todo_or(entry.get("template"))
        ref_html = _todo_or(entry.get("reference_html"))
        notes = entry.get("notes") or ""
        rows.append(
            f"| {scenario_id} | {path} | {template} | {ref_html} | {notes} |"
        )
    return _HEADER + _TABLE_HEADER + "\n".join(rows) + "\n"


def _render_to_disk(repo_root):
    """Read yaml, write md."""
    yaml_path = repo_root / YAML_REL
    md_path = repo_root / MD_REL
    md_path.write_text(_render_md(yaml_path))


def _check(repo_root):
    """Compare on-disk md to a fresh render. Returns list of stale paths."""
    yaml_path = repo_root / YAML_REL
    md_path = repo_root / MD_REL
    expected = _render_md(yaml_path)
    actual = md_path.read_text() if md_path.exists() else None
    if actual != expected:
        return [str(md_path.relative_to(repo_root))]
    return []


def main():
    parser = argparse.ArgumentParser(description="Render scenarios.yaml → scenario-mapping.md")
    parser.add_argument("--check", action="store_true",
                        help="Exit 2 if scenario-mapping.md is stale; no writes.")
    args = parser.parse_args()

    if args.check:
        stale = _check(REPO_ROOT)
        if stale:
            print("render_scenario_mapping: stale targets:", file=sys.stderr)
            for s in stale:
                print(f"  {s}", file=sys.stderr)
            print("Re-run `python3 scripts/render_scenario_mapping.py` and commit the diff.",
                  file=sys.stderr)
            return 2
        return 0

    _render_to_disk(REPO_ROOT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
