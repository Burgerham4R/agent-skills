"""Web PlatformAdapter implementation."""
import subprocess
import signal
import os
import time
from pathlib import Path

from .base import PlatformAdapter, Device


class WebAdapter(PlatformAdapter):
    platform_id = "web"

    # Track the dev server PID for stop()
    _server_pid: int | None = None

    def discover_devices(self, policy: str) -> list[Device]:
        # Web always has a "local" virtual device
        return [Device(kind="simulator", id="local", extra={})]

    def build(self, workspace: Path, compile_log: Path) -> int:
        compile_log.parent.mkdir(parents=True, exist_ok=True)
        with open(compile_log, "w") as log_f:
            # npm ci
            proc = subprocess.run(
                ["npm", "ci"],
                cwd=str(workspace),
                stdout=log_f,
                stderr=subprocess.STDOUT,
                check=False,
            )
            if proc.returncode != 0:
                return proc.returncode
            # npm run build
            proc = subprocess.run(
                ["npm", "run", "build"],
                cwd=str(workspace),
                stdout=log_f,
                stderr=subprocess.STDOUT,
                check=False,
            )
        return proc.returncode

    def install(self, workspace: Path, device: Device) -> int:
        # No-op for web (npm ci already done in build phase)
        return 0

    def launch_with_nonce(self, workspace: Path, device: Device, nonce: str) -> int:
        # Rewrite .env.local with nonce
        _inject_web_nonce(workspace, nonce)

        # Start dev server in background
        env = {**os.environ, "EVAL_RUN_NONCE": nonce}
        proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(workspace),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        self._server_pid = proc.pid

        # Give dev server time to start
        time.sleep(3)
        return 0

    def stop(self, workspace: Path, device: Device) -> None:
        if self._server_pid:
            try:
                os.kill(self._server_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            self._server_pid = None

    def log_stream_command(self, device: Device, nonce: str | None = None) -> list[str]:
        # Web uses a log-bridge Node script that connects via CDP to capture console output
        # The bridge script is expected at templates/web-demo/scripts/log-bridge.mjs
        return [
            "node", "scripts/log-bridge.mjs",
            "--url", "http://127.0.0.1:5173",
        ]


def _inject_web_nonce(workspace: Path, nonce: str) -> None:
    """Rewrite .env.local to include the eval nonce."""
    env_local = workspace / ".env.local"
    lines: list[str] = []
    if env_local.exists():
        lines = [
            line for line in env_local.read_text().splitlines()
            if not line.startswith("VITE_EVAL_RUN_NONCE=")
        ]
    lines.append(f"VITE_EVAL_RUN_NONCE={nonce}")
    env_local.write_text("\n".join(lines) + "\n")
