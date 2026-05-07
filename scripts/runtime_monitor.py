"""runtime_monitor.py — Parse runtime.log and produce dynamic evaluation.

Does NOT write trace.jsonl (orchestrator only).
Does NOT generate nonce (only reads EVAL_RUN_NONCE from env to verify presence in log).
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.lib.schemas import Case, DynamicResult
from scripts.lib.log_parsers.syslog_parser import parse_syslog
from scripts.lib.log_parsers.logcat_parser import parse_logcat
from scripts.lib.log_parsers.puppeteer_parser import parse_puppeteer_console


def _get_parser(platform: str):
    parsers = {
        "ios": parse_syslog,
        "android": parse_logcat,
        "web": parse_puppeteer_console,
    }
    return parsers.get(platform, parse_syslog)


def main() -> int:
    ap = argparse.ArgumentParser(description="Dynamic evaluation: parse runtime.log")
    ap.add_argument("--case-id", required=True)
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()

    nonce = os.environ.get("EVAL_RUN_NONCE")
    if not nonce:
        print("ERROR: EVAL_RUN_NONCE not in env", file=sys.stderr)
        return 1

    run_dir = Path(args.run_dir).resolve()
    case_dir = run_dir / "cases" / args.case_id

    # Load case
    cases_data = json.loads(Path("tests/benchmark/cases.json").read_text())
    case_raw = next((c for c in cases_data if c["test_id"] == args.case_id), None)
    if case_raw is None:
        print(f"ERROR: case '{args.case_id}' not found", file=sys.stderr)
        return 1
    case = Case(**case_raw)

    runtime_log = case_dir / "runtime.log"
    compile_log = case_dir / "compile.log"

    # Check compile status
    compile_ok = True
    compile_exit_code = 0
    if compile_log.exists():
        # If compile.log has ERROR indicators or static_result indicates compile_fail
        content = compile_log.read_text(errors="replace")
        if "BUILD FAILED" in content or "error:" in content.lower():
            compile_ok = False
            compile_exit_code = 1

    # If no runtime.log, dynamic score is 0
    if not runtime_log.exists() or runtime_log.stat().st_size == 0:
        result = DynamicResult(
            test_id=case.test_id,
            compile_ok=compile_ok,
            compile_exit_code=compile_exit_code,
            events_captured=[],
            events_missing=case.expected_events[:],
            events_hit_ratio=0.0,
            nonce_seen=False,
            score=0.0,
        )
        (case_dir / "dynamic_result.json").write_text(
            json.dumps(result.model_dump(), indent=2, ensure_ascii=False)
        )
        return 0

    # Parse log
    parser = _get_parser(case.platform)
    events = parser(str(runtime_log))
    captured_event_names = {e["event"] for e in events}

    # Check nonce presence in runtime.log
    log_content = runtime_log.read_text(errors="replace")
    nonce_marker = f"TRTC_EVAL_NONCE={nonce}"
    nonce_seen = nonce_marker in log_content

    # Compare with expected events
    events_captured = [e for e in case.expected_events if e in captured_event_names]
    events_missing = [e for e in case.expected_events if e not in captured_event_names]

    total_expected = len(case.expected_events)
    events_hit_ratio = len(events_captured) / total_expected if total_expected > 0 else 1.0

    # Score
    if not compile_ok:
        dynamic_score = 0.0
    else:
        dynamic_score = (
            events_hit_ratio * case.weights.w_events
            + (1.0 if compile_ok else 0.0) * case.weights.w_compile_bonus
        )

    result = DynamicResult(
        test_id=case.test_id,
        compile_ok=compile_ok,
        compile_exit_code=compile_exit_code,
        events_captured=events_captured,
        events_missing=events_missing,
        events_hit_ratio=round(events_hit_ratio, 4),
        nonce_seen=nonce_seen,
        score=round(dynamic_score, 4),
    )
    (case_dir / "dynamic_result.json").write_text(
        json.dumps(result.model_dump(), indent=2, ensure_ascii=False)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
