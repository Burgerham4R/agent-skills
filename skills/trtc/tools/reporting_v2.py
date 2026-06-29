"""TRTC runtime reporting v2 — payload in, MCP out.

Unlike ``reporting.py``, this helper does **not** read session files, docs-query
state, or deduplicate prompts. Call sites (skill scripts / the agent) must
resolve ``product``, ``framework``, ``version``, ``sdkappid``, ``sessionid``,
``method``, ``text``, and optional ``answer`` / ``feedback`` themselves, then
pass them here for fire-and-forget delivery via ``tencent-rtc-skill-tool``.

Usage:
  python3 <trtc-skill-root>/tools/reporting_v2.py send \\
    --product chat --framework vue3 --version 1.0.0 \\
    --sdkappid 0 --sessionid sess_abc_123 \\
    --method event --text "skill_start|path=A"

  python3 <trtc-skill-root>/tools/reporting_v2.py send --json '<payload-object>'

The helper is intentionally quiet by default: no payload is printed to stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
from subprocess import DEVNULL, PIPE, Popen, TimeoutExpired
from typing import Any

MCP_PACKAGE = "@tencent-rtc/skill-tool@latest"

REQUIRED_KEYS = ("product", "framework", "version", "sdkappid", "sessionid", "method", "text")
OPTIONAL_KEYS = ("answer", "feedback")


def _normalize_sdkappid(value: Any) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return 0
        try:
            return int(stripped)
        except ValueError:
            return 0
    return 0


def _normalize_payload(data: dict[str, Any]) -> dict[str, Any]:
    missing = [key for key in REQUIRED_KEYS if key not in data]
    if missing:
        raise ValueError(f"missing required payload field(s): {', '.join(missing)}")

    payload: dict[str, Any] = {}
    for key in REQUIRED_KEYS:
        value = data[key]
        if key == "sdkappid":
            payload[key] = _normalize_sdkappid(value)
            continue
        if key in {"product", "framework", "version", "sessionid", "method", "text"}:
            payload[key] = "" if value is None else str(value)
            continue
        payload[key] = value

    for key in OPTIONAL_KEYS:
        if key not in data:
            continue
        value = data[key]
        if value is None:
            continue
        payload[key] = str(value)

    if not payload["method"].strip():
        raise ValueError("method must be non-empty")
    if not payload["text"].strip() and payload["method"] != "feedback":
        raise ValueError("text must be non-empty")

    return payload


def build_payload(data: dict[str, Any]) -> str:
    """Validate *data* and return a JSON string for ``skill_analysis``."""
    return json.dumps(_normalize_payload(data), ensure_ascii=False)


def prepare_send(data: dict[str, Any]) -> dict[str, Any]:
    """Validate payload and return an action dict for CLI/debug output."""
    normalized = _normalize_payload(data)
    return {
        "action": "report",
        "payload": build_payload(normalized),
        "method": normalized["method"],
    }


def payload_from_cli_args(args: argparse.Namespace) -> dict[str, Any]:
    data: dict[str, Any] = {
        "product": args.product,
        "framework": args.framework,
        "version": args.version,
        "sdkappid": args.sdkappid,
        "sessionid": args.sessionid,
        "method": args.method,
        "text": args.text,
    }
    if args.answer is not None:
        data["answer"] = args.answer
    if args.feedback is not None:
        data["feedback"] = args.feedback
    return data


def payload_from_json(raw: str) -> dict[str, Any]:
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("payload JSON must be an object")
    return parsed


def _fire_via_mcp_stdio(payload_str: str) -> None:
    """Call skill_analysis via the skill-tool MCP server's stdio protocol."""
    proc = None
    try:
        proc = Popen(
            ["npx", "--yes", MCP_PACKAGE],
            stdin=PIPE,
            stdout=PIPE,
            stderr=DEVNULL,
        )

        def send(msg: dict[str, Any]) -> None:
            line = json.dumps(msg, ensure_ascii=False) + "\n"
            proc.stdin.write(line.encode("utf-8"))  # type: ignore[union-attr]
            proc.stdin.flush()  # type: ignore[union-attr]

        def recv() -> dict[str, Any] | None:
            try:
                line = proc.stdout.readline()  # type: ignore[union-attr]
                return json.loads(line) if line.strip() else None
            except Exception:
                return None

        send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "trtc-reporting-v2", "version": "1.0"},
                },
            }
        )
        recv()
        send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        send(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "skill_analysis",
                    "arguments": {"payload": payload_str},
                },
            }
        )
        recv()
        proc.stdin.close()  # type: ignore[union-attr]
        proc.wait(timeout=5)
    except (TimeoutExpired, Exception):
        pass
    finally:
        if proc is not None:
            try:
                proc.kill()
            except Exception:
                pass


def _spawn_report(payload_str: str) -> None:
    try:
        Popen(
            [sys.executable, __file__, "--fire", payload_str],
            stdout=DEVNULL,
            stderr=DEVNULL,
            start_new_session=True,
        )
    except Exception:
        pass


def dispatch_send(data: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    result = prepare_send(data)
    if dry_run:
        result["action"] = "dry-run"
        return result
    _spawn_report(result["payload"])
    return {"action": "reported", "method": result["method"]}


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) == 2 and argv[0] == "--fire":
        _fire_via_mcp_stdio(argv[1])
        return 0

    parser = argparse.ArgumentParser(description="Fire-and-forget TRTC skill_analysis reporter (v2).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    send = sub.add_parser("send", help="Validate payload fields and report via MCP.")
    send.add_argument("--json", help="Full payload object as JSON string.")
    send.add_argument("--product")
    send.add_argument("--framework")
    send.add_argument("--version")
    send.add_argument("--sdkappid")
    send.add_argument("--sessionid")
    send.add_argument("--method")
    send.add_argument("--text", default="")
    send.add_argument("--answer")
    send.add_argument("--feedback")
    send.add_argument("--dry-run", action="store_true", help="Build payload only; do not call MCP.")
    send.add_argument("--debug", action="store_true", help="Print action JSON to stdout.")

    args = parser.parse_args(argv)

    if args.cmd != "send":
        return 2

    try:
        if args.json:
            data = payload_from_json(args.json)
        else:
            missing = [
                name
                for name in ("product", "framework", "version", "sdkappid", "sessionid", "method")
                if getattr(args, name) is None
            ]
            if missing:
                raise ValueError(
                    "either --json or all of "
                    "--product --framework --version --sdkappid --sessionid --method are required"
                )
            data = payload_from_cli_args(args)
        result = dispatch_send(data, dry_run=args.dry_run)
    except (ValueError, json.JSONDecodeError) as exc:
        if args.debug:
            print(json.dumps({"action": "error", "reason": str(exc)}, ensure_ascii=False))
        return 1

    if args.debug or args.dry_run:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
