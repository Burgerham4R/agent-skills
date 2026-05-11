"""Unit tests for .claude/skills/trtc/room-builder/guardrails/lib/theme_registry.py.

TDD discipline: tests added one at a time. Each pins one observable behavior
of the registry loader.

Convention follows tests/unit/test_orchestrator.py: sys.path hack + tmp_path,
no conftest.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / ".claude/skills/trtc/room-builder/guardrails"))

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

from lib import theme_registry


# ---------------------------------------------------------------------------
# Test 1: real scenarios.yaml parses to all 4 expected keys
# ---------------------------------------------------------------------------


def test_load_registry_parses_all_4_scenarios():
    """Real yaml on disk has 4 scenarios: 2 themed + 2 TODO.

    This pins the file's basic structural integrity. If load_registry()
    silently ate any rows, this would catch it.
    """
    reg = theme_registry.load_registry(REPO_ROOT)
    assert set(reg.keys()) == {
        "general-meeting",
        "webinar-large",
        "online-classroom",
        "telemedicine",
    }, f"unexpected scenarios: {sorted(reg.keys())}"


# ---------------------------------------------------------------------------
# Test 2: theme: ~ rows resolve to None
# ---------------------------------------------------------------------------


def test_theme_for_scenario_returns_none_for_todo_rows():
    """Telemedicine / online-classroom in yaml have `theme: ~`.

    They must surface as None so callers (in_scope) can treat "TODO row" the
    same as "scenario doesn't exist" — both mean "hooks no-op silently".
    """
    reg = theme_registry.load_registry(REPO_ROOT)
    assert theme_registry.theme_for_scenario(reg, "telemedicine") is None
    assert theme_registry.theme_for_scenario(reg, "online-classroom") is None


# ---------------------------------------------------------------------------
# Test 3: full theme entry resolves to a Theme dataclass with all 5 fields
# ---------------------------------------------------------------------------


def test_theme_for_scenario_returns_dataclass_for_meeting_classic():
    """general-meeting maps to a fully-populated Theme.

    Pins every field of the Theme contract. If any param drifts (e.g. slug
    typo'd in yaml), this fires.
    """
    reg = theme_registry.load_registry(REPO_ROOT)
    theme = theme_registry.theme_for_scenario(reg, "general-meeting")
    assert theme is not None
    assert theme.slug == "meeting-classic"
    assert theme.data_theme == "mc"
    assert theme.import_path == "@/themes/meeting-classic/index.css"
    assert theme.target_dir == "src/themes/meeting-classic"
    assert theme.source_dir.is_absolute(), (
        f"source_dir must be absolute (resolved against kb_root); got {theme.source_dir}"
    )
    assert str(theme.source_dir).endswith("themes/meeting-classic"), (
        f"source_dir must end with themes/meeting-classic; got {theme.source_dir}"
    )


# ---------------------------------------------------------------------------
# Test 4: unknown scenario → None (forgiving lookup)
# ---------------------------------------------------------------------------


def test_theme_for_scenario_returns_none_for_unknown_scenario():
    """Unknown scenario id → None (not KeyError).

    The caller (in_scope) treats None as "no scope, no-op". Raising would
    promote a typo in onboarding's session.scenario into a hook crash —
    worse UX than silent no-op.
    """
    reg = theme_registry.load_registry(REPO_ROOT)
    assert theme_registry.theme_for_scenario(reg, "made-up-scenario") is None


# ---------------------------------------------------------------------------
# Test 5: None scenario arg → None
# ---------------------------------------------------------------------------


def test_theme_for_scenario_returns_none_for_none_scenario():
    """`scenario(session)` returns None when the field is absent.

    Forwarding that None must not crash. This is a null-safety guard for the
    very first session-yaml-write moment when onboarding hasn't picked yet.
    """
    reg = theme_registry.load_registry(REPO_ROOT)
    assert theme_registry.theme_for_scenario(reg, None) is None


# ---------------------------------------------------------------------------
# Test 6: malformed yaml raises ValueError naming the path
# ---------------------------------------------------------------------------


def test_load_registry_raises_on_malformed_yaml(tmp_path):
    """Yaml entry missing `id` key → ValueError with path mentioned.

    Loud failure is the design choice. A bad registry that silently produced
    an empty dict would make every hook no-op while looking healthy —
    exactly the failure mode this whole architecture exists to prevent.
    """
    fake_kb = tmp_path / "kb"
    yaml_dir = fake_kb / ".claude/skills/trtc/room-builder/references"
    yaml_dir.mkdir(parents=True)
    (yaml_dir / "scenarios.yaml").write_text(
        "version: 1\n"
        "scenarios:\n"
        "  - path: general-meeting/\n"  # no `id` key
        "    template: meeting-classic\n"
    )
    try:
        theme_registry.load_registry(fake_kb)
    except ValueError as e:
        assert "scenarios.yaml" in str(e), f"error must name path; got: {e}"
        assert "id" in str(e), f"error must mention missing `id`; got: {e}"
        return
    assert False, "load_registry must raise ValueError on malformed yaml"


# ---------------------------------------------------------------------------
# Test 7: source_dir is resolved against the passed kb_root, not CWD
# ---------------------------------------------------------------------------


def test_theme_source_dir_resolves_against_kb_root(tmp_path):
    """If kb_root is /tmp/x, theme.source_dir starts with /tmp/x/...

    This pins that the registry never depends on CWD. Hooks fire from
    different CWDs depending on whether Claude Code launched in the KB or
    via `cd`-on-session-start; resolving against kb_root makes the lookup
    deterministic.
    """
    fake_kb = tmp_path / "kb"
    yaml_dir = fake_kb / ".claude/skills/trtc/room-builder/references"
    yaml_dir.mkdir(parents=True)
    (yaml_dir / "scenarios.yaml").write_text(
        "version: 1\n"
        "scenarios:\n"
        "  - id: x\n"
        "    path: x/\n"
        "    template: foo\n"
        "    reference_html: foo/index.html\n"
        "    notes: ''\n"
        "    theme:\n"
        "      slug: foo\n"
        "      source_dir: foo-theme-dir\n"
        "      data_theme: fo\n"
        "      import_path: '@/themes/foo/index.css'\n"
        "      target_dir: src/themes/foo\n"
    )
    # We need source_dir to actually exist for resolve() to work properly on
    # systems where resolve(strict=False) still normalises:
    (fake_kb / "foo-theme-dir").mkdir()

    reg = theme_registry.load_registry(fake_kb)
    theme = theme_registry.theme_for_scenario(reg, "x")
    assert theme is not None
    assert str(theme.source_dir).startswith(str(fake_kb.resolve())), (
        f"source_dir must be inside kb_root; got {theme.source_dir} outside {fake_kb}"
    )


# ---------------------------------------------------------------------------
# Test 8: one theme can back multiple scenarios (webinar-large reuses meeting-classic)
# ---------------------------------------------------------------------------


def test_webinar_large_shares_meeting_classic_theme():
    """webinar-large and general-meeting both point at meeting-classic.

    Pins that the registry doesn't artificially restrict 1 theme to 1
    scenario. Real-world: many scenarios will share themes (a "meeting"
    theme covers gallery, focus, sidebar variants).
    """
    reg = theme_registry.load_registry(REPO_ROOT)
    a = theme_registry.theme_for_scenario(reg, "general-meeting")
    b = theme_registry.theme_for_scenario(reg, "webinar-large")
    assert a is not None and b is not None
    assert a.slug == b.slug == "meeting-classic"
    assert a.target_dir == b.target_dir
    assert a.source_dir == b.source_dir
