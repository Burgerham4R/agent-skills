# Quality Self-Check

This document describes the three-gate quality self-check mechanism that ensures the eval tool produces trustworthy results.

## Gate A: Artifact Existence
Every case must produce:
- `ai_raw_output.md` (≥200B)
- `compile.log` (exists regardless of success/failure)
- `runtime.log` (exists; may be empty if compile failed)
- `summary.json` with valid `artifacts_dir`

## Gate B: Data Authenticity
- `runtime.log` must not be a copy of any fixture file (SHA256 check)
- `runtime.log` must contain the EVAL_RUN_NONCE marker (challenge-response)
- Timestamps must be consistent with demo_runner execution time

## Gate C: Flow Completeness
- `trace.jsonl` must have exactly 1 `_meta` + 7 main steps
- Steps must be in strict order: run_ai → evaluator → demo_build → log_stream_start → demo_run → log_stream_stop → runtime_monitor
- No extra commands allowed in trace

## Running Self-Check

```bash
# Before eval
python scripts/selfcheck.py --phase=pre-run

# After eval
python scripts/selfcheck.py --phase=post-run --run-dir=.codebuddy/eval-runs/{timestamp}

# Validate cases.json
python scripts/selfcheck.py --phase=cases-lint
```
