#!/usr/bin/env python3
"""apply.py — Executable apply gate.

Replaces the AI-driven "I'll call apply skill" with a deterministic command
the topic skill must run between writing code and asking the user to confirm.

Usage:
    python3 apply.py --slice conference/login-auth
                     [--session PATH]
                     [--project PATH]

Session path resolution (when --session not given):
    1. $TRTC_SESSION_PATH env var
    2. $CLAUDE_PROJECT_DIR/.trtc-session.yaml (Claude Code sets this to the
       user project root)
    3. ./.trtc-session.yaml (cwd fallback)

What it does:

1. Confirms the state machine is in ``code_written`` for the slice the
   caller named. Anything else is a usage error (exit 2).
2. Loads MUST rules for the slice via ``apply_lib.rule_parser`` (extracts
   backtick-quoted code patterns from each rule).
3. For each rule, checks whether ANY of its patterns appears in any
   ``.vue``/``.ts`` file under ``<project_root>/src/`` — **with comments and
   string literals stripped first** so AI cannot stuff patterns into
   ``// comments`` or ``"strings"`` to pass the check.
4. Writes evidence JSON to ``<session_dir>/.trtc-apply-evidence/<slug>.json``.
5. Advances the state machine: pass → apply_passed (exit 0); fail →
   apply_failed (exit 1).

Exit codes: 0 pass / 1 fail / 2 usage error

Why minimal: the prior V2 yaml-driven engine was walked back because the
verify-yaml maintenance burden did not match the actual bug surface
(see docs/apply-skill-long-term-design.md). Two real bugs from
demo-test-2 are kept fixed here:

  * Comment / string-literal stuffing — patterns must be in real code
  * AI shouldn't see literal patterns in fail messages — fail output
    describes the rule semantically, never names the missing pattern
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Iterable

import yaml

HERE = Path(__file__).resolve().parent
LIB_DIR = HERE / "lib"

sys.path.insert(0, str(LIB_DIR))
import state_machine  # noqa: E402
sys.path.pop(0)

# rule_parser lives under trtc-apply/guardrails/apply_lib (sibling skill).
# HERE = skills/trtc-topic/scripts → parent.parent = skills/
_APPLY_GUARDRAILS = HERE.parent.parent / "trtc-apply" / "guardrails"
sys.path.insert(0, str(_APPLY_GUARDRAILS))
from apply_lib.rule_parser import extract_rules_from_slice  # noqa: E402
sys.path.pop(0)


def _resolve_session_path() -> Path:
    """Match the resolver used by guardrails/gate_*.py:
    env var → $CLAUDE_PROJECT_DIR → cwd. The session file lives in the
    user project, never in the skill repo.
    """
    explicit = os.environ.get("TRTC_SESSION_PATH")
    if explicit:
        return Path(explicit)
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        return Path(project_dir) / ".trtc-session.yaml"
    return Path.cwd() / ".trtc-session.yaml"


def _eprint(msg: str) -> None:
    sys.stderr.write(msg.rstrip("\n") + "\n")


def _slice_id_to_slug(slice_id: str) -> str:
    return slice_id.replace("/", "__")


def _load_session(session_path: Path) -> dict:
    return yaml.safe_load(session_path.read_text()) or {}


def _slice_files(repo_root: Path, slice_id: str, platform: str) -> list[Path]:
    """Return product overview + platform file for the slice (existing files only)."""
    product, ability = slice_id.split("/", 1)
    candidates = [
        repo_root / "knowledge-base" / "slices" / product / f"{ability}.md",
        repo_root / "knowledge-base" / "slices" / product / platform / f"{ability}.md",
    ]
    return [p for p in candidates if p.exists()]


def _gather_must_rules(slice_files: Iterable[Path]) -> list[dict]:
    rules: list[dict] = []
    for sf in slice_files:
        rules.extend(extract_rules_from_slice(sf))
    return [r for r in rules if r.get("type") == "MUST"]


def _strip_comments_and_strings(content: str) -> str:
    """Replace JS/TS comments and string literals with whitespace.

    Why: the demo-test-2 root cause was AI stuffing the literal pattern
    (e.g. ``Math.floor(Date.now() / 1000)``) into a ``//`` comment to pass
    substring grep. After stripping, only real code is searched. Whitespace
    is used (not deletion) so byte offsets are preserved if anyone ever
    needs to surface code locations from the stripped buffer.

    Strips:
      * ``// single-line``
      * ``/* block */`` (multi-line)
      * ``"double-quoted"`` strings
      * ``'single-quoted'`` strings
      * `` `template literals` ``
    """
    out: list[str] = []
    i = 0
    n = len(content)
    while i < n:
        # // single-line comment — skip to next newline
        if content[i:i + 2] == "//":
            end = content.find("\n", i)
            if end == -1:
                end = n
            out.append(" " * (end - i))
            i = end
        # /* block comment */ — skip to */
        elif content[i:i + 2] == "/*":
            end = content.find("*/", i + 2)
            if end == -1:
                end = n
            else:
                end += 2
            replaced = content[i:end]
            # Preserve newlines inside the block; replace other chars with space.
            out.append(re.sub(r"[^\n]", " ", replaced))
            i = end
        # double-quoted string
        elif content[i] == '"':
            j = i + 1
            while j < n:
                if content[j] == "\\" and j + 1 < n:
                    j += 2
                elif content[j] == '"':
                    j += 1
                    break
                else:
                    j += 1
            out.append('""' + " " * max(0, j - i - 2))
            i = j
        # single-quoted string
        elif content[i] == "'":
            j = i + 1
            while j < n:
                if content[j] == "\\" and j + 1 < n:
                    j += 2
                elif content[j] == "'":
                    j += 1
                    break
                else:
                    j += 1
            out.append("''" + " " * max(0, j - i - 2))
            i = j
        # template literal — note: doesn't fully parse ${...} interpolation,
        # treats whole thing as a string. That's fine for our pattern matching.
        elif content[i] == "`":
            j = i + 1
            while j < n:
                if content[j] == "\\" and j + 1 < n:
                    j += 2
                elif content[j] == "`":
                    j += 1
                    break
                else:
                    j += 1
            out.append("``" + " " * max(0, j - i - 2))
            i = j
        else:
            out.append(content[i])
            i += 1
    return "".join(out)


def _scan_project_src(project_root: Path) -> tuple[str, list[tuple[Path, str]]]:
    """Return (mode, [(path, stripped_content), ...]).

    Each file's content is stripped of comments and string literals before
    being returned, so the substring matcher only ever sees real code.

    mode is either 'full' or 'static-only'. static-only means src/ doesn't
    exist or has no source files.
    """
    src = project_root / "src"
    if not src.exists():
        return "static-only", []
    files: list[tuple[Path, str]] = []
    for ext in ("*.vue", "*.ts"):
        for f in src.rglob(ext):
            try:
                raw = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            files.append((f, _strip_comments_and_strings(raw)))
    return ("full" if files else "static-only", files)


def _check_rule(rule: dict, files: list[tuple[Path, str]]) -> bool:
    """A MUST rule passes if any pattern from it appears in any file's
    real-code text (comments and string literals already stripped).

    Returns True (pass) / False (fail). We deliberately do NOT return the
    list of matched patterns — exposing pattern strings in fail output is
    what let AI learn to comment-stuff in demo-test-2.
    """
    patterns = [p for p in rule.get("patterns", []) if isinstance(p, str) and len(p) >= 4]
    if not patterns:
        # Rule had no extractable code patterns — we can't check it
        # mechanically. Treat as pass (don't false-positive on text-only rules).
        return True
    for _, content in files:
        for pat in patterns:
            if pat in content:
                return True
    return False


def _write_evidence(
    session_path: Path,
    slice_id: str,
    payload: dict,
) -> Path:
    ev_dir = session_path.parent / ".trtc-apply-evidence"
    ev_dir.mkdir(parents=True, exist_ok=True)
    out = ev_dir / f"{_slice_id_to_slug(slice_id)}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--slice", dest="slice_id", required=True)
    p.add_argument(
        "--session",
        type=Path,
        default=None,
        help="explicit path to .trtc-session.yaml (overrides env-based resolver)",
    )
    p.add_argument("--project", type=Path, default=None)
    args = p.parse_args(argv)

    session_path = args.session if args.session is not None else _resolve_session_path()

    if not session_path.exists():
        _eprint(
            f"error: session file not found: {session_path}\n"
            f"  hint: cd to the user project root, or set $CLAUDE_PROJECT_DIR / "
            f"$TRTC_SESSION_PATH before running this script."
        )
        return 2

    # State machine gate.
    idx, current_id, state = state_machine.current_slice(session_path)
    if current_id is None:
        _eprint("error: slice_queue not initialised; run init_slice_queue.py first.")
        return 2
    if args.slice_id != current_id:
        _eprint(
            f"error: --slice '{args.slice_id}' does not match current slice "
            f"[{idx}] '{current_id}'."
        )
        return 2
    if state != "code_written":
        _eprint(
            f"error: state must be 'code_written' to run apply; current state is '{state}'.\n"
            f"hint: write the slice's code first, then run "
            f"`next_slice.py advance mark_code_written` before calling apply.py."
        )
        return 2

    # Resolve repo root for slice file lookup. We use the worktree containing
    # this script as the source of slice files (knowledge-base lives there).
    repo_root = HERE.parents[3]

    # Resolve project root.
    session_data = _load_session(session_path)
    if args.project is not None:
        project_root = args.project
    else:
        pr = (session_data.get("project_state") or {}).get("project_root")
        project_root = Path(pr) if pr else None
    if project_root is None:
        _eprint("error: project root not provided and not in session.")
        return 2

    platform = session_data.get("platform", "web")

    files_to_load = _slice_files(repo_root, args.slice_id, platform)
    if not files_to_load:
        _eprint(
            f"warning: no slice file found for {args.slice_id} on platform "
            f"{platform}; rule check will be empty."
        )

    must_rules = _gather_must_rules(files_to_load)
    mode, project_files = _scan_project_src(project_root)

    issues: list[dict] = []
    rules_checked = 0
    for rule in must_rules:
        rules_checked += 1
        if not _check_rule(rule, project_files):
            # Note: we record the rule's human-readable text only.
            # We do NOT include `patterns` — surfacing literal patterns in
            # the evidence JSON / fail output is what let AI learn to
            # comment-stuff. The rule_text is enough for AI to find the
            # offending behaviour by re-reading the slice file.
            issues.append({
                "rule_text": rule.get("text", "")[:200],
                "type": rule.get("type"),
                "slice_id": rule.get("slice_id", args.slice_id),
            })

    status = "fail" if issues or mode == "static-only" else "pass"
    payload = {
        "slice_id": args.slice_id,
        "status": status,
        "mode": mode,
        "rules_checked": rules_checked,
        "issues": issues,
        "project_root": str(project_root),
        "files_scanned": len(project_files),
    }
    _write_evidence(session_path, args.slice_id, payload)

    transition = "mark_apply_passed" if status == "pass" else "mark_apply_failed"
    try:
        state_machine.advance(session_path, transition)
    except RuntimeError as exc:
        _eprint(f"error: failed to advance state machine: {exc}")
        return 2

    if status == "pass":
        # auto-advance policy: pause_on_failure / pause_at_end skip the
        # explicit "ask user 继续?" pause when apply itself confirms success.
        # pause_each (default) preserves the original per-slice prompt.
        # Unknown / unset values fall back to pause_each — fail closed.
        policy = session_data.get("auto_advance_policy")
        if policy in {"pause_on_failure", "pause_at_end"}:
            try:
                new_state = state_machine.advance(session_path, "mark_user_confirmed")
            except RuntimeError as exc:
                _eprint(f"error: failed to auto-advance state machine: {exc}")
                return 2
            print(
                f"apply pass: {rules_checked} MUST rules satisfied for "
                f"{args.slice_id} — auto-advanced ({policy}); next state: {new_state}"
            )
            # POST-LOOP CHECKLIST: when all slices are done, remind the AI
            # to execute Step 4 and Step 4.5 from topic/SKILL.md.
            if new_state == "all_done":
                print("")
                print("=" * 60)
                print("ALL SLICES COMPLETE — POST-LOOP CHECKLIST (mandatory)")
                print("=" * 60)
                print("The slice loop is finished, but the topic flow is NOT done.")
                print("You MUST now execute these steps from topic/SKILL.md:")
                print("")
                print("  □ Step 4: Present the verification checklist to the user")
                print("  □ Step 4.5: Offer runtime verification & telemetry")
                print("             (ask consent if telemetry.opted_in is null)")
                print("")
                print("Do NOT output a final summary and stop. Read topic/SKILL.md")
                print("Step 4 and Step 4.5 sections and execute them now.")
                print("=" * 60)
            return 0
        print(f"apply pass: {rules_checked} MUST rules satisfied for {args.slice_id}")
        return 0

    print(
        f"apply fail: {len(issues)} of {rules_checked} MUST rules failed for "
        f"{args.slice_id} (mode={mode})"
    )
    # Print the rule text only — never the literal patterns.
    for issue in issues[:5]:
        print(f"  - {issue['rule_text'][:120]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
