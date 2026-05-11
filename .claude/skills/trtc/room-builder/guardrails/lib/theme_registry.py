"""theme_registry.py — Load scenarios.yaml; map scenario id → Theme dataclass.

This module is the single contract by which trtc_prepare_ui.py and
trtc_verify_ui.py learn theme parameters. Adding a new themed scenario =
editing scenarios.yaml; no Python changes required.

Loud failure: malformed yaml raises ValueError naming the path. We never
silently fall through, because a bad registry would make every hook silently
no-op (looks like "all green" but actually nothing is enforced).
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


REGISTRY_REL_PATH = (
    ".claude/skills/trtc/room-builder/references/scenarios.yaml"
)


@dataclass(frozen=True)
class Theme:
    """All five parameters that vary per UI theme.

    These flow yaml → registry → prepare/verify scripts. Adding a new theme
    means adding a yaml block with all five keys.
    """
    slug: str
    source_dir: Path        # absolute, resolved against KB root
    data_theme: str
    import_path: str
    target_dir: str         # relative to user project root


def load_registry(kb_root):
    """Read scenarios.yaml under kb_root; return dict[scenario_id, Theme | None].

    `Theme | None` because some scenarios are listed for human discoverability
    but don't have themes yet (`theme: ~`).

    Raises ValueError on malformed yaml; the error message names the path so
    a maintainer can fix it fast.
    """
    yaml_path = Path(kb_root) / REGISTRY_REL_PATH
    raw = yaml.safe_load(yaml_path.read_text())
    if not isinstance(raw, dict) or "scenarios" not in raw:
        raise ValueError(
            f"theme_registry: malformed yaml at {yaml_path}: expected top-level "
            f"`scenarios:` key"
        )

    out = {}
    for entry in raw["scenarios"]:
        if not isinstance(entry, dict) or "id" not in entry:
            raise ValueError(
                f"theme_registry: malformed scenario entry in {yaml_path}: "
                f"missing `id` key in {entry!r}"
            )
        scenario_id = entry["id"]
        theme_block = entry.get("theme")
        if theme_block is None:
            out[scenario_id] = None
            continue
        # Resolve source_dir against kb_root (the yaml stores it relative).
        source_dir = (Path(kb_root) / theme_block["source_dir"]).resolve()
        out[scenario_id] = Theme(
            slug=theme_block["slug"],
            source_dir=source_dir,
            data_theme=theme_block["data_theme"],
            import_path=theme_block["import_path"],
            target_dir=theme_block["target_dir"],
        )
    return out


def theme_for_scenario(reg, scenario):
    """Look up the Theme for a scenario id. Forgiving:
    None / unknown id / theme: ~ row → all return None.
    """
    if scenario is None:
        return None
    return reg.get(scenario)
