"""Unit tests for hooks/cursor-adapter.py.

Strategy: replace each guardrail script with a tiny stub in a fake plugin
root, then run the adapter and assert the right script ran with the right
stdin/env. Same strategy used in tests/unit/test_trtc_*.py — direct
subprocess invocation, no test-framework magic.

Run with:
    python3 -m unittest tests.unit.test_cursor_adapter

Pytest also picks these up if available.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ADAPTER_SRC = REPO_ROOT / "hooks" / "cursor-adapter.py"


# Mirror of the DISPATCH dict inside cursor-adapter.py — keep in sync.
DISPATCH = {
    "trtc-prepare-ui":      "skills/trtc/room-builder/guardrails/trtc_prepare_ui.py",
    "gate-slice-read":      "skills/trtc-topic/guardrails/gate_slice_read.py",
    "gate-slice-write":     "skills/trtc-topic/guardrails/gate_slice_write.py",
    "verify-ui-post-write": "skills/trtc/room-builder/guardrails/verify_ui_post_write.sh",
    "verify-slice-must":    "skills/trtc-apply/guardrails/verify_slice_must_rules.py",
    "stop-apply-evidence":  "skills/trtc-topic/guardrails/stop_require_apply_evidence.py",
    "trtc-verify-ui":       "skills/trtc/room-builder/guardrails/trtc_verify_ui.py",
    "verify-apply-project": "skills/trtc-apply/guardrails/verify_apply_project.py",
}


class CursorAdapterTestBase(unittest.TestCase):
    """Builds a fake plugin tree at <tmp>/plugin/ containing a copy of the
    real adapter, so adapter's __file__-based PLUGIN_ROOT resolution lands
    on our temp directory.
    """

    def setUp(self) -> None:
        # macOS resolves /var/folders → /private/var/folders; realpath the
        # tmp dir so what we observe matches what the adapter sees.
        self.tmp = Path(tempfile.mkdtemp(prefix="trtc-adapter-")).resolve()
        (self.tmp / "hooks").mkdir(parents=True, exist_ok=True)
        self.adapter = self.tmp / "hooks" / "cursor-adapter.py"
        shutil.copy2(ADAPTER_SRC, self.adapter)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---- helpers --------------------------------------------------------

    def plant_stub(self, rel_path: str, *, exit_code: int = 0, stderr_text: str = "") -> None:
        """Write a stub at <tmp>/<rel_path> that records its stdin/env to
        <tmp>/hook-trace.json, prints stderr_text, and exits exit_code.
        """
        abs_path = self.tmp / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        trace_path = self.tmp / "hook-trace.json"

        if abs_path.suffix == ".sh":
            # Match the .sh script wrapping pattern used in verify_ui_post_write.sh.
            body = textwrap.dedent(f"""\
                #!/usr/bin/env bash
                data=$(cat)
                python3 - <<PY
                import json
                with open({json.dumps(str(trace_path))}, 'w') as f:
                    json.dump({{
                        'stdin': {json.dumps('')!r}.replace("''", json.dumps(${{data!r}})) if False else $(python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))' <<<'$data'),
                        'env_CLAUDE_PLUGIN_ROOT': {json.dumps('CLAUDE_PLUGIN_ROOT_PLACEHOLDER')},
                        'env_CLAUDE_PROJECT_DIR': {json.dumps('CLAUDE_PROJECT_DIR_PLACEHOLDER')},
                    }}, f)
                PY
                """)
            # Simpler, robust shell-stub: write JSON via plain Python heredoc.
            body = textwrap.dedent(f"""\
                #!/usr/bin/env bash
                stdin_data=$(cat)
                python3 -c '
                import json, os, sys
                trace = {{
                  "stdin": sys.stdin.read(),
                  "env_CLAUDE_PLUGIN_ROOT": os.environ.get("CLAUDE_PLUGIN_ROOT", ""),
                  "env_CLAUDE_PROJECT_DIR": os.environ.get("CLAUDE_PROJECT_DIR", ""),
                }}
                with open({json.dumps(str(trace_path))}, "w") as f:
                  json.dump(trace, f)
                ' <<< "$stdin_data"
                if [ -n {json.dumps(stderr_text)} ]; then
                  echo -n {json.dumps(stderr_text)} >&2
                fi
                exit {exit_code}
                """)
        else:
            body = textwrap.dedent(f"""\
                #!/usr/bin/env python3
                import json, os, sys
                trace = {{
                  "stdin": sys.stdin.read(),
                  "env_CLAUDE_PLUGIN_ROOT": os.environ.get("CLAUDE_PLUGIN_ROOT", ""),
                  "env_CLAUDE_PROJECT_DIR": os.environ.get("CLAUDE_PROJECT_DIR", ""),
                  "argv": sys.argv,
                }}
                with open({json.dumps(str(trace_path))}, "w") as f:
                  json.dump(trace, f)
                if {json.dumps(stderr_text)}:
                  sys.stderr.write({json.dumps(stderr_text)})
                sys.exit({exit_code})
                """)

        abs_path.write_text(body)
        abs_path.chmod(0o755)

    def run_adapter(self, dispatch_key: str, stdin: str = "", extra_env: dict | None = None):
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            ["python3", str(self.adapter), dispatch_key],
            input=stdin,
            capture_output=True,
            text=True,
            env=env,
        )

    def read_trace(self) -> dict | None:
        p = self.tmp / "hook-trace.json"
        if not p.exists():
            return None
        return json.loads(p.read_text())


class TestSilentAllow(CursorAdapterTestBase):

    def test_unknown_dispatch_key_is_silent_allow(self):
        result = self.run_adapter("totally-bogus-key")
        self.assertEqual(result.returncode, 0)

    def test_missing_target_script_is_silent_allow(self):
        # Plant nothing — script doesn't exist.
        result = self.run_adapter(
            "gate-slice-read",
            stdin=json.dumps({"file_path": "/x"}),
        )
        self.assertEqual(result.returncode, 0)

    def test_malformed_stdin_is_silent_allow(self):
        self.plant_stub(DISPATCH["gate-slice-read"], exit_code=0)
        result = self.run_adapter("gate-slice-read", stdin="not json at all")
        # Adapter still dispatches with empty payload; inner stub exits 0; net 0.
        self.assertEqual(result.returncode, 0)

    def test_pretooluse_with_non_write_tool_short_circuits(self):
        # Stub plants exit 2; if adapter wrongly invoked it, we'd see deny.
        self.plant_stub(DISPATCH["gate-slice-write"], exit_code=2, stderr_text="should not fire")
        result = self.run_adapter(
            "gate-slice-write",
            stdin=json.dumps({"tool_name": "Shell", "tool_input": {"command": "ls"}}),
        )
        self.assertEqual(result.returncode, 0)
        # Trace file should NOT exist — adapter short-circuited before subprocess.
        self.assertIsNone(self.read_trace())


class TestPayloadTranslation(CursorAdapterTestBase):

    def test_before_read_file_translates_to_tool_name_read(self):
        self.plant_stub(DISPATCH["gate-slice-read"], exit_code=0)
        result = self.run_adapter(
            "gate-slice-read",
            stdin=json.dumps({
                "file_path": "/repo/knowledge-base/slices/conference/web/login-auth.md",
                "content": "...",
                "hook_event_name": "beforeReadFile",
            }),
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        trace = self.read_trace()
        self.assertIsNotNone(trace, "stub did not run")
        seen = json.loads(trace["stdin"])
        self.assertEqual(seen["tool_name"], "Read")
        self.assertEqual(
            seen["tool_input"]["file_path"],
            "/repo/knowledge-base/slices/conference/web/login-auth.md",
        )

    def test_pretooluse_with_write_dispatches_with_normalized_payload(self):
        self.plant_stub(DISPATCH["gate-slice-write"], exit_code=0)
        result = self.run_adapter(
            "gate-slice-write",
            stdin=json.dumps({
                "tool_name": "Write",
                "tool_input": {"file_path": "/proj/src/main.ts"},
            }),
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        trace = self.read_trace()
        self.assertIsNotNone(trace)
        seen = json.loads(trace["stdin"])
        self.assertEqual(seen["tool_name"], "Write")
        self.assertEqual(seen["tool_input"]["file_path"], "/proj/src/main.ts")

    def test_after_file_edit_translates_for_verify_slice_must(self):
        self.plant_stub(DISPATCH["verify-slice-must"], exit_code=0)
        result = self.run_adapter(
            "verify-slice-must",
            stdin=json.dumps({
                "file_path": "/proj/src/Room.vue",
                "edits": [{"old_string": "a", "new_string": "b"}],
            }),
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        trace = self.read_trace()
        self.assertIsNotNone(trace)
        seen = json.loads(trace["stdin"])
        self.assertEqual(seen["tool_name"], "Edit")
        self.assertEqual(seen["tool_input"]["file_path"], "/proj/src/Room.vue")


class TestEnvForwarding(CursorAdapterTestBase):

    def test_claude_plugin_root_exported_to_inner_script(self):
        self.plant_stub(DISPATCH["trtc-prepare-ui"], exit_code=0)
        result = self.run_adapter("trtc-prepare-ui", stdin="")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        trace = self.read_trace()
        self.assertIsNotNone(trace)
        self.assertEqual(trace["env_CLAUDE_PLUGIN_ROOT"], str(self.tmp))

    def test_cursor_project_dir_forwarded_as_claude_project_dir(self):
        self.plant_stub(DISPATCH["trtc-prepare-ui"], exit_code=0)
        result = self.run_adapter(
            "trtc-prepare-ui",
            stdin="",
            extra_env={"CURSOR_PROJECT_DIR": "/some/project", "CLAUDE_PROJECT_DIR": ""},
        )
        self.assertEqual(result.returncode, 0)

        trace = self.read_trace()
        self.assertIsNotNone(trace)
        self.assertEqual(trace["env_CLAUDE_PROJECT_DIR"], "/some/project")


class TestExitCodeMapping(CursorAdapterTestBase):

    def test_inner_exit_2_becomes_cursor_deny_envelope_and_exit_2(self):
        self.plant_stub(
            DISPATCH["gate-slice-read"],
            exit_code=2,
            stderr_text="Slice read out of bounds — finish current slice first.",
        )
        result = self.run_adapter(
            "gate-slice-read",
            stdin=json.dumps({"file_path": "/repo/knowledge-base/slices/conference/web/x.md"}),
        )
        self.assertEqual(result.returncode, 2)

        envelope = json.loads(result.stdout)
        self.assertEqual(envelope["permission"], "deny")
        # Both user-facing and agent-facing messages should be set so Cursor
        # can surface the warning in whichever channel the current event
        # supports (preToolUse blocks the AI; afterAgentResponse logs to
        # the Output panel and may surface user_message).
        self.assertIn("Slice read out of bounds", envelope["agent_message"])
        self.assertIn("Slice read out of bounds", envelope["user_message"])

    def test_inner_exit_1_also_maps_to_deny(self):
        # verify_slice_must_rules.py and verify_apply_project.py exit 1 on
        # check failure (not 2). Adapter must still translate to Cursor deny.
        self.plant_stub(
            DISPATCH["verify-slice-must"],
            exit_code=1,
            stderr_text="MUST-rule check failed",
        )
        result = self.run_adapter(
            "verify-slice-must",
            stdin=json.dumps({"file_path": "/p/x.vue"}),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn('"permission":', result.stdout)
        self.assertIn('"deny"', result.stdout)


if __name__ == "__main__":
    unittest.main()
