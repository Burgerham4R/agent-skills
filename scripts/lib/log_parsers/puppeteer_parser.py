"""Puppeteer / browser console log parser for Web platform."""
import json
import re
from datetime import datetime


def parse_puppeteer_console(log_path: str) -> list[dict]:
    """Parse Web runtime.log (console output captured by log-bridge or Puppeteer)."""
    events: list[dict] = []
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                event = _parse_line(line)
                if event:
                    events.append(event)
    except FileNotFoundError:
        pass
    return events


def _parse_line(line: str) -> dict | None:
    """Extract event from a console log line."""
    # Try JSON format (CDP message)
    line_stripped = line.strip()
    if line_stripped.startswith("{"):
        try:
            obj = json.loads(line_stripped)
            if "event" in obj:
                return {
                    "ts": obj.get("ts", datetime.now().isoformat()),
                    "platform": "web",
                    "event": obj["event"],
                    "ok": obj.get("ok", True),
                    "raw": line_stripped,
                }
        except json.JSONDecodeError:
            pass

    # Try plain text with event pattern
    event_match = re.search(r"\b(on\w+)\b", line)
    if event_match and any(kw in line.lower() for kw in ["trtc", "liteav", "livecoreview"]):
        return {
            "ts": datetime.now().isoformat(),
            "platform": "web",
            "event": event_match.group(1),
            "ok": "error" not in line.lower(),
            "raw": line_stripped,
        }
    return None
