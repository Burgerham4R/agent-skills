"""selfcheck.py — Quality self-check script (§7).

Phases:
  pre-run     Environment + source hygiene checks (before eval)
  post-run    Three-gate validation (after eval)
  cases-lint  Eval set schema validation

Any failure → exit non-zero. Main Agent MUST abort on failure.
"""
import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _grep_in_scripts(pattern: str) -> list[str]:
    """Grep scripts/ for a pattern. Returns matching filenames."""
    try:
        proc = subprocess.run(
            ["rg", "-l", pattern, "scripts/"],
            capture_output=True, text=True, check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip().splitlines()
    except (FileNotFoundError, PermissionError):
        # rg not available, fallback to Python grep
        hits = []
        for py_file in Path("scripts").rglob("*.py"):
            if "selfcheck" in py_file.name:
                continue  # don't flag ourselves
            content = py_file.read_text(errors="replace")
            if re.search(pattern, content, re.IGNORECASE):
                hits.append(str(py_file))
        return hits
    return []


def _ast_check_imports(scripts_dir: Path) -> list[str]:
    """AST scan: production scripts must not import from tests.*"""
    violations = []
    for py_file in scripts_dir.rglob("*.py"):
        try:
            tree = ast.parse(py_file.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("tests"):
                        violations.append(f"{py_file}:{node.lineno} import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("tests"):
                    violations.append(f"{py_file}:{node.lineno} from {node.module}")
    return violations


def phase_pre_run() -> dict:
    """Pre-run environment and source hygiene checks."""
    results = {"phase": "pre-run", "checks": [], "passed": True}

    def check(name: str, ok: bool, detail: str = ""):
        results["checks"].append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            results["passed"] = False

    # CLI available
    cli_ok = False
    for cli in ["claude", "codebuddy"]:
        try:
            proc = subprocess.run([cli, "--version"], capture_output=True, check=False)
            if proc.returncode == 0:
                cli_ok = True
                break
        except (FileNotFoundError, PermissionError):
            continue
    check("cli_available", cli_ok, "claude or codebuddy CLI must be installed")

    # Test account env vars
    for var in ["TRTC_TEST_SDKAPPID", "TRTC_TEST_USERID", "TRTC_TEST_USERSIG"]:
        import os
        val = os.environ.get(var, "")
        check(f"env_{var}", len(val) > 0, f"${var} must be non-empty")

    # cases.json exists and is valid JSON
    cases_path = Path("tests/benchmark/cases.json")
    if cases_path.exists():
        try:
            data = json.loads(cases_path.read_text())
            check("cases_json_valid", isinstance(data, list) and len(data) > 0)
        except json.JSONDecodeError as e:
            check("cases_json_valid", False, str(e))
    else:
        check("cases_json_exists", False, "tests/benchmark/cases.json not found")

    # Source hygiene: grep for mock/fake/stub keywords
    mock_pattern = r"MOCK|mock_|fake_|stub_|hardcoded_log|return_sample|read_fixture|FIXTURE_PATH|sample_logcat|sample_syslog"
    hits = _grep_in_scripts(mock_pattern)
    # Exclude selfcheck.py itself from this check
    hits = [h for h in hits if "selfcheck.py" not in h]
    check("source_no_mock_keywords", len(hits) == 0,
          f"Found mock keywords in: {hits}" if hits else "")

    # Source hygiene: no tests/unit references in production scripts
    path_hits = _grep_in_scripts(r"tests/unit|tests/benchmark/fixtures")
    path_hits = [h for h in path_hits if "selfcheck.py" not in h]
    check("source_no_fixture_paths", len(path_hits) == 0,
          f"Found fixture paths in: {path_hits}" if path_hits else "")

    # AST scan: no import tests
    import_violations = _ast_check_imports(Path("scripts"))
    check("ast_no_test_imports", len(import_violations) == 0,
          f"Violations: {import_violations}" if import_violations else "")

    return results


def phase_post_run(run_dir: Path) -> dict:
    """Post-run three-gate validation."""
    results = {"phase": "post-run", "checks": [], "passed": True, "verdict": "OK"}

    def check(gate: str, name: str, ok: bool, detail: str = ""):
        results["checks"].append({"gate": gate, "name": name, "ok": ok, "detail": detail})
        if not ok:
            results["passed"] = False
            results["verdict"] = "TAINTED"

    cases_dir = run_dir / "cases"
    if not cases_dir.exists():
        check("A", "cases_dir_exists", False, f"{cases_dir} not found")
        return results

    fixture_dir = Path("tests/unit/fixtures")

    for case_path in sorted(cases_dir.iterdir()):
        if not case_path.is_dir():
            continue
        tid = case_path.name

        # Gate A: Artifact existence
        ai_output = case_path / "ai_raw_output.md"
        check("A", f"{tid}/ai_raw_output.md_exists",
              ai_output.exists() and ai_output.stat().st_size >= 200)

        compile_log = case_path / "compile.log"
        check("A", f"{tid}/compile.log_exists", compile_log.exists())

        runtime_log = case_path / "runtime.log"
        check("A", f"{tid}/runtime.log_exists", runtime_log.exists())

        summary = case_path / "summary.json"
        check("A", f"{tid}/summary.json_exists", summary.exists())

        # Gate B: Data authenticity (only if runtime.log exists and non-empty)
        if runtime_log.exists() and runtime_log.stat().st_size > 0:
            # Size > 100B
            check("B", f"{tid}/runtime_log_size", runtime_log.stat().st_size > 100)

            # SHA256 not equal to any fixture
            log_hash = hashlib.sha256(runtime_log.read_bytes()).hexdigest()
            if fixture_dir.exists():
                for fixture in fixture_dir.iterdir():
                    if fixture.is_file():
                        fix_hash = hashlib.sha256(fixture.read_bytes()).hexdigest()
                        check("B", f"{tid}/not_fixture_{fixture.name}",
                              log_hash != fix_hash,
                              "runtime.log SHA256 matches a fixture!")

            # Nonce check (Gate B strong Harness)
            trace_path = case_path / "trace.jsonl"
            if trace_path.exists():
                first_line = trace_path.read_text().splitlines()[0]
                meta = json.loads(first_line)
                nonce = meta.get("nonce", "")
                if nonce:
                    marker = f"TRTC_EVAL_NONCE={nonce}"
                    log_content = runtime_log.read_text(errors="replace")
                    check("B", f"{tid}/nonce_present", marker in log_content,
                          "EVAL_RUN_NONCE not found in runtime.log")

        # Gate C: Flow completeness
        trace_path = case_path / "trace.jsonl"
        if trace_path.exists():
            lines = trace_path.read_text().strip().splitlines()
            steps = []
            for line in lines:
                step_data = json.loads(line)
                steps.append(step_data["step"])

            check("C", f"{tid}/trace_has_meta", steps[0] == "_meta" if steps else False)

            expected_order = [
                "run_ai", "evaluator", "demo_build",
                "log_stream_start", "demo_run", "log_stream_stop", "runtime_monitor",
            ]
            actual_main_steps = [s for s in steps if s != "_meta"]
            check("C", f"{tid}/trace_7_steps",
                  len(actual_main_steps) == 7,
                  f"Expected 7 steps, got {len(actual_main_steps)}")
            check("C", f"{tid}/trace_order",
                  actual_main_steps == expected_order,
                  f"Order mismatch: {actual_main_steps}")

            # Nonce in _meta is 32-char hex
            if steps and steps[0] == "_meta":
                meta = json.loads(lines[0])
                nonce_val = meta.get("nonce", "")
                check("C", f"{tid}/nonce_format",
                      len(nonce_val) == 32 and all(c in "0123456789abcdef" for c in nonce_val))
        else:
            check("C", f"{tid}/trace_exists", False, "trace.jsonl missing")

    # Scoreboard row count
    scoreboard = run_dir / "scoreboard.csv"
    if scoreboard.exists():
        with open(scoreboard) as f:
            row_count = sum(1 for _ in f) - 1  # minus header
        case_count = sum(1 for p in cases_dir.iterdir() if p.is_dir())
        check("C", "scoreboard_row_count", row_count == case_count,
              f"scoreboard has {row_count} rows but {case_count} cases")

    return results


def phase_cases_lint() -> dict:
    """Validate cases.json schema and consistency."""
    results = {"phase": "cases-lint", "checks": [], "passed": True}

    def check(name: str, ok: bool, detail: str = ""):
        results["checks"].append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            results["passed"] = False

    cases_path = Path("tests/benchmark/cases.json")
    if not cases_path.exists():
        check("file_exists", False)
        return results

    try:
        data = json.loads(cases_path.read_text())
    except json.JSONDecodeError as e:
        check("json_valid", False, str(e))
        return results

    check("is_list", isinstance(data, list))

    # Unique test_ids
    ids = [c.get("test_id", "") for c in data]
    check("unique_ids", len(ids) == len(set(ids)),
          f"Duplicate IDs: {[x for x in ids if ids.count(x) > 1]}")

    for case in data:
        tid = case.get("test_id", "unknown")
        # must_include and must_not_include no intersection
        mi = set(case.get("constraints", {}).get("must_include", []))
        mni = set(case.get("constraints", {}).get("must_not_include", []))
        intersection = mi & mni
        check(f"{tid}/no_constraint_overlap", len(intersection) == 0,
              f"Overlap: {intersection}" if intersection else "")

    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="Quality self-check")
    ap.add_argument("--phase", required=True,
                    choices=["pre-run", "post-run", "cases-lint"])
    ap.add_argument("--run-dir", default=None, help="Required for post-run")
    args = ap.parse_args()

    if args.phase == "pre-run":
        result = phase_pre_run()
    elif args.phase == "post-run":
        if not args.run_dir:
            print("ERROR: --run-dir required for post-run", file=sys.stderr)
            return 1
        result = phase_post_run(Path(args.run_dir).resolve())
    elif args.phase == "cases-lint":
        result = phase_cases_lint()
    else:
        return 1

    # Write result
    output_path = None
    if args.run_dir:
        output_path = Path(args.run_dir).resolve() / "selfcheck.json"
    elif args.phase == "pre-run":
        output_path = Path(".claude/eval-runs/selfcheck_prerun.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

    output = json.dumps(result, indent=2, ensure_ascii=False)
    if output_path:
        output_path.write_text(output)

    # Print summary
    print(output, file=sys.stderr)

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
