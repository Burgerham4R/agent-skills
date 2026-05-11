"""Shared helpers for reading .trtc-session.yaml state.

trtc_prepare_ui.py and trtc_verify_ui.py both consume session state. Helpers
are centralised here so the two scripts can't drift on parsing/validation.

The full scope contract for ui_mode hooks (see in_scope below):
  ui_mode == "full-ui"
    AND product == "conference"
    AND intent == "integrate-scenario"
    AND scenario is registered with a theme

The first three guard against hooks acting on unrelated workflows (live /
chat / troubleshoot / demo). The fourth ties theme selection to the registry,
so adding/removing themed scenarios is yaml-only.
"""
from pathlib import Path

import yaml

# Local import — uses the registry as the single source of truth for which
# scenarios have themes.
from . import theme_registry


def load_session(session_path):
    """Read .trtc-session.yaml at session_path.

    Returns a parsed dict, or None if the file does not exist. An empty/
    malformed-but-readable file parses to {}.
    """
    p = Path(session_path)
    if not p.exists():
        return None
    return yaml.safe_load(p.read_text()) or {}


def project_root(session):
    """Extract project_state.project_root from a parsed session dict.

    Returns a pathlib.Path, or None if unset.
    """
    state = session.get("project_state") or {}
    pr = state.get("project_root")
    return Path(pr) if pr else None


def ui_mode(session):
    """Return the ui_mode string from a parsed session (None if unset)."""
    return session.get("ui_mode")


def scenario(session):
    """Return the scenario string from a parsed session (None if unset).

    Set by onboarding skill at A2-Q0 when the user picks a scenario. Used
    here as the registry lookup key.
    """
    if session is None:
        return None
    return session.get("scenario")


def scaffold_complete(session):
    """True iff session.current_step ends with '-complete'.

    Why this signal: onboarding writes `current_step: A2.<N>-complete` when
    a user finishes the integration path. Once that flips, the user owns
    the code — hooks must close silently. Continuing to fire post-handoff
    would either be noise (silent green) or actively wrong (yelling about
    legitimate user refactors that don't fit the original meeting-classic
    contract).

    Defensive: returns False on missing field, None, empty string, and
    non-string types (a yaml-coerced int doesn't have .endswith).
    """
    if session is None:
        return False
    step = session.get("current_step")
    if not isinstance(step, str):
        return False
    return step.endswith("-complete")


# Scope of the ui_mode hooks: which sessions they're allowed to act on.
#
# Defense-in-depth: each clause guards a different misuse case.
#   ui_mode != full-ui    → user opted out of UI mode
#   product != conference → wrong product (theme is conference-specific)
#   intent  != integrate  → wrong workflow phase (troubleshoot/demo)
#   theme   == None       → scenario unknown or in TODO state in registry
_SCOPE_PRODUCT = "conference"
_SCOPE_INTENT = "integrate-scenario"
_SCOPE_UI_MODE = "full-ui"


def in_scope(session, kb_root):
    """Return True if the ui_mode hooks should act on this session.

    `kb_root` is needed so we can load the theme registry to confirm the
    session's scenario actually has a theme. Without that lookup, scenarios
    listed as TODO (theme: ~) in scenarios.yaml would still be "in scope"
    and the hooks would crash trying to copy a nonexistent theme.

    False on any clause failure — caller should exit 0 silently. We never
    raise from here: the hooks must degrade quietly on out-of-scope
    sessions, never crash.
    """
    if session is None:
        return False
    if session.get("ui_mode") != _SCOPE_UI_MODE:
        return False
    if session.get("product") != _SCOPE_PRODUCT:
        return False
    if session.get("intent") != _SCOPE_INTENT:
        return False
    # Final clause: scenario must be in registry AND have a non-None theme.
    reg = theme_registry.load_registry(kb_root)
    theme = theme_registry.theme_for_scenario(reg, scenario(session))
    if theme is None:
        return False
    return True
