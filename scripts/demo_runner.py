"""demo_runner.py — Thin orchestration: parse --phase and dispatch.

Does NOT write trace.jsonl (orchestrator only).
Does NOT generate EVAL_RUN_NONCE (reads from env, exits 3 if missing).
Does NOT capture logs (that's log_streamer.py's job).
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.lib import template_fetcher, code_injector, builder, device_picker, launcher, dep_installer
from scripts.lib.platforms import get_adapter
from scripts.lib.schemas import Case


def _load_case(case_id: str) -> Case:
    cases = json.loads(Path("tests/benchmark/cases.json").read_text())
    raw = next((c for c in cases if c["test_id"] == case_id), None)
    if raw is None:
        raise ValueError(f"case-id '{case_id}' not found")
    return Case(**raw)


def main() -> int:
    ap = argparse.ArgumentParser(description="Demo build/run dispatcher")
    ap.add_argument("--case-id", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--phase", required=True, choices=["build", "run"])
    args = ap.parse_args()

    if "EVAL_RUN_NONCE" not in os.environ:
        print(json.dumps({"error": "EVAL_RUN_NONCE missing in env"}), file=sys.stderr)
        return 3

    case = _load_case(args.case_id)
    case_dir = Path(args.run_dir).resolve() / "cases" / case.test_id
    case_dir.mkdir(parents=True, exist_ok=True)
    workspace = case_dir / "workspace"
    adapter = get_adapter(case.platform)

    if args.phase == "build":
        template_fetcher.copy_template(case.platform, case_dir, Path("templates"))
        code_injector.inject(
            workspace=workspace,
            ai_code_dir=case_dir / "ai_extracted_code",
            injection_map=case.demo_injection_map,
            platform=case.platform,
        )
        # Install dependencies declared by AI (e.g., CocoaPods)
        dep_file = case_dir / "dependencies.json"
        if dep_file.exists():
            dep_rc = dep_installer.install(
                platform=case.platform,
                workspace=workspace,
                dep_file=dep_file,
                log_dir=case_dir,
            )
            if dep_rc != 0:
                print(json.dumps({"phase": "build", "exit_code": dep_rc, "error": "dep_install_failed"}))
                return dep_rc
        rc = builder.build(adapter, workspace, compile_log=case_dir / "compile.log")
        print(json.dumps({"phase": "build", "exit_code": rc, "compile_log": "compile.log"}))
        return rc

    if args.phase == "run":
        device = device_picker.pick(
            case.platform,
            os.environ.get("EVAL_DEVICE_POLICY", "prefer-simulator"),
        )
        if device is None:
            print(json.dumps({"error": "no device available"}), file=sys.stderr)
            return 4
        # Ensure simulator is booted before install/launch
        boot_rc = adapter.ensure_booted(device)
        if boot_rc != 0:
            print(json.dumps({"error": "failed to boot device", "exit_code": boot_rc}), file=sys.stderr)
            return 5
        rc = launcher.run(
            adapter=adapter,
            workspace=workspace,
            device=device,
            nonce=os.environ["EVAL_RUN_NONCE"],
            duration_sec=int(os.environ.get("EVAL_RUN_DURATION_SEC", "60")),
        )
        print(json.dumps({
            "phase": "run", "exit_code": rc,
            "device_kind": device.kind, "device_id": device.id,
        }))
        return rc

    return 1


if __name__ == "__main__":
    sys.exit(main())
