#!/usr/bin/env python3
"""apply.py — Executable structural gate.

This is a STRUCTURAL GATE, not a correctness/compile verifier. It exists to
stop the AI from declaring a slice "done" and ending the turn before a
deterministic check has run — a forcing function on the state machine, paired
with the Stop hook (``guardrails/stop_require_apply_evidence.py``). The check
itself is intentionally minimal; it does NOT verify types, compilation, or
runtime behavior. Correctness comes from the slice's MUST/MUST NOT constraints
at generation time and the user running the code in their real project.

Usage:
    python3 apply.py --slice conference/login-auth
    python3 apply.py --unit foundation
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
2. Requires the project to contain real source (``code non-empty``): if
   ``<project_root>/src/`` has no ``.vue``/``.ts`` files the run is
   static-only and fails — there is nothing to gate.
3. For each slice, checks that the slice's **entry symbol** (its composable /
   component, e.g. ``useDeviceState`` for device-control) appears as a real
   code identifier in some source file — **with comments and string literals
   stripped first** so the entry can't be faked from a ``// comment`` or
   ``"string"``. Slices with no registered entry symbol are skipped (we can't
   check them mechanically; never a false-positive). This is a coarse
   "did you wire up this capability's entry" check, deliberately NOT a proof
   of correctness.
4. Runs a NARROW compile-safety check for composable-destructuring name
   collisions (e.g. the same symbol destructured from two ``use*()`` calls,
   or destructured and then re-declared as a function). It is NOT a general
   linter.
5. Writes evidence JSON to ``<session_dir>/.trtc-apply-evidence/<slug>.json``.
6. Advances the state machine: pass → apply_passed (exit 0); fail →
   apply_failed (exit 1).

Exit codes: 0 pass / 1 fail / 2 usage error

Why an entry-symbol check and not a per-API grep: an earlier version greped
each MUST rule's backtick-quoted patterns. That was unreliable in both
directions — any-pattern-hit produced false positives, and stripping string
literals (needed for anti-cheat) produced false negatives whenever a symbol
legitimately lived inside a string (e.g. an error-code constant). The gate's
real value is the forcing function (you cannot self-certify and stop), not the
judge's precision, so the judge was reduced to the honest minimum: code exists
+ the slice's entry was wired up. Correctness is delegated to the slice's
MUST/MUST NOT constraints and the customer's own build.

Why not a compiler: apply runs inside the customer's heterogeneous existing
project, where a build can fail for reasons unrelated to generated code
(missing deps, private registries, monorepo config) and is slow per slice —
so compilation is intentionally out of scope. The comment/string stripping is
kept because the demo-test-2 bug showed symbols can be stuffed into comments
or strings; entry symbols are code identifiers so this never false-negatives
on correct code.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

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
from apply_lib.rule_parser import entry_symbols_for_slice  # noqa: E402
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


_IDENT = r"[A-Za-z_$][\w$]*"
# `const|let|var X =` / `function X` / `async function X` / `class X`
_SIMPLE_DECL_RE = re.compile(
    r"\b(?:const|let|var)\s+(" + _IDENT + r")\s*[=:]"
    r"|\b(?:async\s+)?function\s*\*?\s*(" + _IDENT + r")"
    r"|\bclass\s+(" + _IDENT + r")"
)
# `const { a, b: c } = useXxx(...)` — destructuring whose RHS is a call.
_DESTRUCTURE_RE = re.compile(
    r"\b(?:const|let|var)\s*\{([^{}]*)\}\s*=\s*([^\n;]*)"
)


def _destructured_binding_names(brace_body: str) -> list[str]:
    """Extract the locally-bound identifiers from a `{ ... }` destructure body.

    Handles ``a``, ``a: b`` (binds ``b``), ``a = default``, ``...rest``.
    Skips nested destructuring parts (containing ``{``) — rare for composable
    destructuring and not worth mis-parsing.
    """
    names: list[str] = []
    for part in brace_body.split(","):
        part = part.strip()
        if not part or "{" in part:
            continue
        if part.startswith("..."):
            part = part[3:].strip()
        if ":" in part:  # rename: key:binding
            part = part.split(":", 1)[1]
        part = part.split("=", 1)[0].strip()  # drop default value
        if re.fullmatch(_IDENT, part):
            names.append(part)
    return names


def _check_duplicate_declarations(
    files: list[tuple[Path, str]], project_root: Path
) -> list[dict]:
    """Detect composable-destructuring name collisions that will not compile.

    This is a deliberately NARROW, high-precision check — NOT a general
    redeclaration linter. It only flags the failure mode that apply's own
    MUST-symbol grep can induce: the AI adds a destructured symbol (or a
    wrapper function) to satisfy the grep, colliding with a name that was
    already destructured from another composable. Two real demo bugs:

      * ``const { getCameraList } = useDeviceState()`` + a later
        ``function getCameraList()`` in the same file.
      * ``const { subscribeEvent } = useRoomParticipantState()`` +
        ``const { subscribeEvent } = useRoomState()`` in the same file.

    We flag a name only when it is bound by destructuring at least twice, OR
    bound by destructuring AND also declared as a simple const/function/class.
    Pure simple-vs-simple duplicates are NOT flagged (those may be legal
    locals in different scopes — we can't tell without a real parser).
    """
    issues: list[dict] = []
    for path, content in files:
        destructured: list[str] = []
        for m in _DESTRUCTURE_RE.finditer(content):
            brace_body, rhs = m.group(1), m.group(2)
            if "(" not in rhs:  # only RHS that is a call (composable / hook)
                continue
            destructured.extend(_destructured_binding_names(brace_body))
        simple: list[str] = []
        for m in _SIMPLE_DECL_RE.finditer(content):
            name = m.group(1) or m.group(2) or m.group(3)
            if name:
                simple.append(name)
        try:
            rel = str(path.resolve().relative_to(project_root.resolve()))
        except (ValueError, OSError):
            rel = str(path)
        for name in sorted(set(destructured)):
            d = destructured.count(name)
            s = simple.count(name)
            if d >= 2 or (d >= 1 and s >= 1):
                issues.append(
                    {
                        "category": "duplicate-declaration",
                        "type": "critical",
                        "symbol": name,
                        "file": rel,
                        "rule_text": (
                            f"Duplicate declaration of '{name}' in {rel}: it is "
                            f"destructured from a composable and re-declared "
                            f"({d}x destructure, {s}x const/function) in the same "
                            f"file. This will not compile — alias one of them."
                        ),
                        "slice_id": None,
                    }
                )
    return issues


def _check_slice_entry(
    slice_id: str, files: list[tuple[Path, str]]
) -> tuple[str, list[str]]:
    """Check that a slice's entry symbol appears as real code.

    Returns ``(result, entry_symbols)`` where ``result`` is one of:

      * ``"pass"``    — at least one entry symbol appears as an identifier in
                        some file's real-code text (comments/strings stripped).
      * ``"fail"``    — entry symbols are known but none appear.
      * ``"skipped"`` — the slice has no registered entry symbol; it cannot be
                        checked mechanically and is treated as pass (we never
                        false-positive on slices we don't know how to check).

    Entry symbols are stable code identifiers (composables / components), never
    string literals, so unlike the old MUST-symbol grep this is immune to the
    comment/string-stripping false-negative — yet the stripping is still run so
    an entry mentioned only in a ``// comment`` or ``"string"`` does not count.
    """
    entry_symbols = entry_symbols_for_slice(slice_id)
    if not entry_symbols:
        return "skipped", entry_symbols
    for sym in entry_symbols:
        word_re = re.compile(r"\b" + re.escape(sym) + r"\b")
        for _, content in files:
            if word_re.search(content):
                return "pass", entry_symbols
    return "fail", entry_symbols


def _write_evidence(
    session_path: Path,
    evidence_id: str,
    payload: dict,
) -> Path:
    ev_dir = session_path.parent / ".trtc-apply-evidence"
    ev_dir.mkdir(parents=True, exist_ok=True)
    out = ev_dir / f"{_slice_id_to_slug(evidence_id)}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--slice", dest="slice_id", default=None)
    p.add_argument(
        "--unit",
        dest="unit_id",
        default=None,
        help="current delivery unit id",
    )
    p.add_argument(
        "--session",
        type=Path,
        default=None,
        help="explicit path to .trtc-session.yaml (overrides env-based resolver)",
    )
    p.add_argument("--project", type=Path, default=None)
    args = p.parse_args(argv)

    if not args.slice_id and not args.unit_id:
        _eprint("error: provide --slice <slice_id> or --unit <unit_id>.")
        return 2

    session_path = args.session if args.session is not None else _resolve_session_path()

    if not session_path.exists():
        _eprint(
            f"error: session file not found: {session_path}\n"
            f"  hint: cd to the user project root, or set $CLAUDE_PROJECT_DIR / "
            f"$TRTC_SESSION_PATH before running this script."
        )
        return 2

    # State machine gate.
    scope = state_machine.current_scope(session_path)
    if not scope.get("initialised"):
        _eprint("error: queue not initialised; run init_slice_queue.py first.")
        return 2
    idx = scope["index"]
    current_id = scope["id"]
    state = scope["state"]
    slice_ids = scope["slice_ids"]
    kind = scope["kind"]
    if args.slice_id != current_id:
        if kind == "unit":
            if args.unit_id:
                if args.unit_id != current_id:
                    _eprint(
                        f"error: --unit '{args.unit_id}' does not match current unit "
                        f"[{idx}] '{current_id}'."
                    )
                    return 2
            elif args.slice_id not in slice_ids:
                _eprint(
                    f"error: --slice '{args.slice_id}' is not part of current unit "
                    f"[{idx}] '{current_id}' ({', '.join(slice_ids)})."
                )
                return 2
        else:
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

    mode, project_files = _scan_project_src(project_root)

    issues: list[dict] = []
    per_slice: dict[str, dict] = {}
    entries_checked = 0
    for slice_id in slice_ids:
        result, entry_symbols = _check_slice_entry(slice_id, project_files)
        rec = {
            "slice_id": slice_id,
            "entry_checked": result != "skipped",
            "entry_result": result,
            "issues": [],
        }
        per_slice[slice_id] = rec
        if result == "skipped":
            continue
        entries_checked += 1
        if result == "fail":
            # Naming the entry composable is safe and helpful: it is the
            # slice's documented import (see its "代码生成约束 → 额外导入"
            # section), not a hidden API pattern an LLM could comment-stuff.
            issue = {
                "rule_text": (
                    f"slice '{slice_id}': entry not wired up — none of its "
                    f"entry symbols ({', '.join(entry_symbols)}) appear in the "
                    f"generated code. Import and use the slice's documented "
                    f"entry (see its '额外导入' section)."
                )[:200],
                "type": "entry",
                "slice_id": slice_id,
            }
            issues.append(issue)
            rec["issues"].append(issue)

    # Narrow compile-safety check: composable-destructuring name collisions.
    # These are real compile errors, so they fail the gate. It is NOT a
    # general redeclaration linter.
    dup_issues = _check_duplicate_declarations(project_files, project_root)
    for dup in dup_issues:
        dup["slice_id"] = current_id
        issues.append(dup)
        per_slice.setdefault(
            current_id,
            {
                "slice_id": current_id,
                "entry_checked": False,
                "entry_result": "skipped",
                "issues": [],
            },
        )
        per_slice[current_id]["issues"].append(dup)

    status = "fail" if issues or mode == "static-only" else "pass"
    evidence_id = current_id if kind == "unit" else slice_ids[0]
    payload = {
        "id": evidence_id,
        "kind": kind,
        "slice_id": slice_ids[0] if len(slice_ids) == 1 else None,
        "unit_id": current_id if kind == "unit" else None,
        "slice_ids": slice_ids,
        "status": status,
        "mode": mode,
        "entries_checked": entries_checked,
        "issues": issues,
        "slices_checked": list(per_slice.values()),
        "project_root": str(project_root),
        "files_scanned": len(project_files),
    }
    _write_evidence(session_path, evidence_id, payload)

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
                f"apply pass: {entries_checked} slice entr"
                f"{'y' if entries_checked == 1 else 'ies'} wired up for "
                f"{evidence_id} — auto-advanced ({policy}); next state: {new_state}"
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
        print(
            f"apply pass: {entries_checked} slice entr"
            f"{'y' if entries_checked == 1 else 'ies'} wired up for {evidence_id}"
        )
        return 0

    entry_failed = [i for i in issues if i.get("category") != "duplicate-declaration"]
    dup_failed = [i for i in issues if i.get("category") == "duplicate-declaration"]
    parts = []
    if entry_failed:
        parts.append(f"{len(entry_failed)} slice entr"
                     f"{'y' if len(entry_failed) == 1 else 'ies'} not wired up")
    if dup_failed:
        parts.append(f"{len(dup_failed)} duplicate-declaration issue(s)")
    if mode == "static-only" and not parts:
        parts.append("no source files found under src/")
    summary = ", ".join(parts) if parts else "gate failed"
    print(f"apply fail: {summary} for {evidence_id} (mode={mode})")
    for issue in issues[:5]:
        print(f"  - {issue.get('rule_text', '')[:160]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
