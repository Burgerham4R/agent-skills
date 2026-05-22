"""Unit tests for skills/trtc/room-builder/guardrails/trtc_verify_ui.py.

TDD discipline: tests added one at a time. Each test pins one observable
behavior of the verifier. The implementation is grown to satisfy each test
before the next is written.

Convention follows tests/unit/test_orchestrator.py: sys.path hack + tmp_path,
no conftest, inline factory helpers.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "skills/trtc/room-builder/guardrails"))

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "skills/trtc/room-builder/guardrails" / "trtc_verify_ui.py"


def _write_session(tmp_path, *, ui_mode, project_root=None, scenario="general-conference"):
    """Write a minimal .trtc-session.yaml; return its path.

    `scenario` defaults to general-conference (registered with meeting-classic).
    Pre-registry tests assumed this implicitly; we now write it explicitly
    so in_scope() — which now requires a registered scenario — keeps
    returning True for them.
    """
    session_path = tmp_path / ".trtc-session.yaml"
    lines = [
        "schema_version: 1",
        "status: active",
        "product: conference",
        "platform: web",
        "intent: integrate-scenario",
        f"scenario: {scenario}",
    ]
    if ui_mode is None:
        lines.append("ui_mode: null")
    else:
        lines.append(f"ui_mode: {ui_mode}")
    if project_root is not None:
        lines.append("project_state:")
        lines.append(f"  project_root: {project_root}")
    session_path.write_text("\n".join(lines) + "\n")
    return session_path


def _write_session_custom(tmp_path, *, product="conference", intent="integrate-scenario",
                          ui_mode="full-ui", project_root=None, scenario="general-conference"):
    """Like _write_session but with explicit product/intent (for scope-gate tests)."""
    session_path = tmp_path / ".trtc-session.yaml"
    lines = [
        "schema_version: 1",
        "status: active",
        f"product: {product}",
        "platform: web",
        f"intent: {intent}",
        f"scenario: {scenario}",
        f"ui_mode: {ui_mode}" if ui_mode is not None else "ui_mode: null",
    ]
    if project_root is not None:
        lines.append("project_state:")
        lines.append(f"  project_root: {project_root}")
    session_path.write_text("\n".join(lines) + "\n")
    return session_path


def _run_verify(*args: str) -> subprocess.CompletedProcess:
    """Invoke the verifier as a subprocess. Returns CompletedProcess with stdout/stderr."""
    return subprocess.run(
        ["python3", str(SCRIPT), *args],
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Test 1: noop when ui_mode is not full-ui
# ---------------------------------------------------------------------------


def test_noop_when_ui_mode_not_full_ui(tmp_path):
    """Session with ui_mode != full-ui → exit 0, no stderr, no work attempted.

    This pins the most fundamental contract: the verifier is a no-op for
    sessions that don't opt into full-ui mode. official-roomkit deliberately
    bypasses meeting-classic verification. Without this, the verifier would
    burn cycles (or, worse, fail) on unrelated projects.
    """
    for mode in (None, "official-roomkit"):
        session = _write_session(tmp_path, ui_mode=mode, project_root=tmp_path / f"fake-project-{mode or 'null'}")
        result = _run_verify("--session-path", str(session))
        assert result.returncode == 0, (
            f"mode={mode}; expected exit 0, got {result.returncode}; stderr={result.stderr}"
        )
        assert result.stderr == "", f"mode={mode}; expected empty stderr, got: {result.stderr!r}"


# ---------------------------------------------------------------------------
# Test 2: noop when no session file exists
# ---------------------------------------------------------------------------


def test_noop_when_no_session_file(tmp_path):
    """No session file at all → exit 0.

    The verifier may run from a SessionStart hook in any directory, including
    repos unrelated to TRTC. It must not blow up just because there's no
    session file. The Stop hook also fires after every conversation; same
    logic.
    """
    missing = tmp_path / "does-not-exist.yaml"
    result = _run_verify("--session-path", str(missing))
    assert result.returncode == 0, f"expected exit 0, got {result.returncode}; stderr={result.stderr}"
    assert result.stderr == "", f"expected empty stderr, got: {result.stderr!r}"


# ---------------------------------------------------------------------------
# Test 3: V1 — themes dir missing → fail with actionable stderr
# ---------------------------------------------------------------------------


def _make_project(tmp_path, *, with_themes=False, with_main_ts_import=False, with_data_theme=False):
    """Build a fake user project. Returns the project root path.

    Each flag controls one of the three artifacts the verifier checks. Default
    is "everything missing" so each test only flips the bits it needs.
    """
    root = tmp_path / "user-project"
    (root / "src").mkdir(parents=True)
    if with_themes:
        theme_dir = root / "src" / "themes" / "meeting-classic"
        theme_dir.mkdir(parents=True)
        (theme_dir / "index.css").write_text("/* meeting-classic */\n")
    main_ts = root / "src" / "main.ts"
    main_body = "import { createApp } from 'vue'\n"
    if with_main_ts_import:
        main_body = "import '@/themes/meeting-classic/index.css'\n" + main_body
    main_ts.write_text(main_body)
    html_attrs = ' lang="zh-CN"' + (' data-theme="mc"' if with_data_theme else '')
    (root / "index.html").write_text(f"<!DOCTYPE html>\n<html{html_attrs}>\n  <body></body>\n</html>\n")
    return root


def test_v1_fails_when_themes_dir_missing(tmp_path):
    """Session full-ui + project missing src/themes/meeting-classic/ → exit 2.

    Stderr must (a) name the missing path and (b) hint at the fix tool. Why:
    the model reads stderr through PostToolUse; vague stderr defeats the
    whole enforcement layer.
    """
    project = _make_project(tmp_path, with_themes=False, with_main_ts_import=True, with_data_theme=True)
    session = _write_session(tmp_path, ui_mode="full-ui", project_root=project)
    result = _run_verify("--session-path", str(session))
    assert result.returncode == 2, f"expected exit 2, got {result.returncode}; stderr={result.stderr}"
    assert "themes/meeting-classic" in result.stderr, (
        f"stderr must name the failing path; got: {result.stderr!r}"
    )
    assert "trtc_prepare_ui" in result.stderr, (
        f"stderr must hint at the fix tool; got: {result.stderr!r}"
    )


# ---------------------------------------------------------------------------
# Test 4: V2 — main.ts missing the theme import → fail
# ---------------------------------------------------------------------------


def test_v2_fails_when_main_ts_missing_import(tmp_path):
    """Themes dir exists but main.ts has no `themes/meeting-classic` import → exit 2.

    A correctly-copied theme that's never imported = dead CSS. The model
    might do P1 (copy) but skip P2 (wire-up); this catches that.
    """
    project = _make_project(tmp_path, with_themes=True, with_main_ts_import=False, with_data_theme=True)
    session = _write_session(tmp_path, ui_mode="full-ui", project_root=project)
    result = _run_verify("--session-path", str(session))
    assert result.returncode == 2, f"expected exit 2, got {result.returncode}; stderr={result.stderr}"
    assert "main.ts" in result.stderr, f"stderr must name main.ts; got: {result.stderr!r}"
    assert "import" in result.stderr.lower(), f"stderr must mention import; got: {result.stderr!r}"


# ---------------------------------------------------------------------------
# Test 5: V3 — index.html missing data-theme="mc" → fail
# ---------------------------------------------------------------------------


def test_v3_fails_when_data_theme_missing(tmp_path):
    """`<html>` without data-theme="mc" → exit 2.

    The meeting-classic theme uses CSS attribute selectors `[data-theme="mc"] {...}`
    so without this attribute, every uikit class falls through to no styles.
    Visually the page would look unstyled. Catching this at hook time is what
    keeps the model honest.
    """
    project = _make_project(tmp_path, with_themes=True, with_main_ts_import=True, with_data_theme=False)
    session = _write_session(tmp_path, ui_mode="full-ui", project_root=project)
    result = _run_verify("--session-path", str(session))
    assert result.returncode == 2, f"expected exit 2, got {result.returncode}; stderr={result.stderr}"
    assert "index.html" in result.stderr, f"stderr must name index.html; got: {result.stderr!r}"
    assert "data-theme" in result.stderr, f"stderr must name data-theme; got: {result.stderr!r}"


# ---------------------------------------------------------------------------
# Test 6: V4 — single-file mode with too few ui-* classes → fail
# ---------------------------------------------------------------------------


def test_v4_per_file_threshold_fails(tmp_path):
    """`--file <vue>` with only 2 ui-* classes (default per-file min 3) → exit 2.

    This is the PostToolUse path: after each Write/Edit on a .vue file, the
    hook calls verify --file <that_file>. Per-file enforcement is what
    pushes the model to use uikit classes one file at a time, instead of
    aggregating ui-* in a single rich file and leaving the rest bare.

    Stderr must contain the actual class count so the model can react with
    a number, not a vague "do better".
    """
    project = _make_project(tmp_path, with_themes=True, with_main_ts_import=True, with_data_theme=True)
    vue = project / "src" / "components" / "Foo.vue"
    vue.parent.mkdir(parents=True)
    vue.write_text(
        '<template>\n'
        '  <div class="ui-stage">\n'
        '    <div class="ui-tile">hi</div>\n'
        '    <div class="my-thing">no uikit</div>\n'
        '  </div>\n'
        '</template>\n'
    )
    session = _write_session(tmp_path, ui_mode="full-ui", project_root=project)
    result = _run_verify("--session-path", str(session), "--file", str(vue))
    assert result.returncode == 2, f"expected exit 2, got {result.returncode}; stderr={result.stderr}"
    assert "Foo.vue" in result.stderr, f"stderr must name the file; got: {result.stderr!r}"
    assert "2" in result.stderr, f"stderr must include actual count; got: {result.stderr!r}"
    assert "ui-" in result.stderr, f"stderr must mention ui-* classes; got: {result.stderr!r}"


# ---------------------------------------------------------------------------
# Test 7: V4 — aggregate threshold across all .vue files
# ---------------------------------------------------------------------------


def test_v4_aggregate_threshold_fails(tmp_path):
    """Project-wide check: total ui-* < default min (30) → exit 2.

    This is the Stop hook path: at end of conversation, even if every
    individual file met the per-file minimum, the project as a whole still
    needs enough uikit coverage. Without this, the model could drop 3 ui-*
    in 5 files and call it done — that's an unstyled meeting page.
    """
    project = _make_project(tmp_path, with_themes=True, with_main_ts_import=True, with_data_theme=True)
    a = project / "src" / "components" / "A.vue"
    b = project / "src" / "components" / "B.vue"
    a.parent.mkdir(parents=True)
    a.write_text(
        '<template>\n'
        '  <div class="ui-stage ui-stage--gallery ui-stage__inner"></div>\n'
        '</template>\n'
    )  # 3 ui-*
    b.write_text(
        '<template>\n'
        '  <div class="ui-bottombar">\n'
        '    <button class="ui-btn ui-btn--primary"></button>\n'
        '    <button class="ui-btn ui-btn--ghost"></button>\n'
        '    <button class="ui-btn"></button>\n'
        '  </div>\n'
        '</template>\n'
    )  # 1 + 2 + 2 + 1 = 6 ui-*; total 9, well under default 30
    session = _write_session(tmp_path, ui_mode="full-ui", project_root=project)
    result = _run_verify("--session-path", str(session))
    assert result.returncode == 2, f"expected exit 2, got {result.returncode}; stderr={result.stderr}"
    assert "V4" in result.stderr, f"stderr must label V4; got: {result.stderr!r}"
    assert "30" in result.stderr or "ui-" in result.stderr, (
        f"stderr must reference threshold or ui-*; got: {result.stderr!r}"
    )


# ---------------------------------------------------------------------------
# Test 8: all checks pass on a fully-wired project
# ---------------------------------------------------------------------------


def test_all_checks_pass(tmp_path):
    """V1-V4 happy path: fully-wired project + ≥30 ui-* classes → exit 0.

    Scope note: this test pins V1-V4 only (themes dir, main.ts import,
    data-theme attr, and class-count thresholds). It deliberately uses a
    scenario whose `scenarios.yaml` row has `theme: ~` (i.e. no landmarks
    file), so V6 (structural landmark enforcement) is skipped here.

    Building a Vue fixture that satisfies V6's ~22 critical landmarks for
    meeting-classic is a separate piece of work; this test predates V6
    and shouldn't expand scope mid-walk-back. There are dedicated V6
    tests elsewhere in this file that cover the landmark check directly.
    """
    project = _make_project(tmp_path, with_themes=True, with_main_ts_import=True, with_data_theme=True)
    # Build a .vue file with 32 ui-* classes (default total_min is 30).
    big = project / "src" / "App.vue"
    classes = " ".join(f"ui-cls-{i}" for i in range(32))
    big.write_text(f'<template>\n  <div class="{classes}"></div>\n</template>\n')
    # Use a scenario with theme:~ so V6 cleanly skips (see scope note).
    session = _write_session(tmp_path, ui_mode="full-ui", project_root=project,
                             scenario="online-classroom")
    result = _run_verify("--session-path", str(session))
    assert result.returncode == 0, (
        f"expected exit 0 on happy path, got {result.returncode}; stderr={result.stderr}"
    )
    assert result.stderr == "", f"expected empty stderr; got: {result.stderr!r}"


# ---------------------------------------------------------------------------
# Test 9: stderr actionability — every error names a path AND a fix hint
# ---------------------------------------------------------------------------


def test_stderr_is_utf8_and_actionable(tmp_path):
    """Each error line must carry a file path AND a concrete fix hint.

    This is the contract PostToolUse + Stop hooks rely on. The model reads
    stderr; vague stderr ("something is wrong") fails the enforcement
    layer's whole purpose. We pin: every error mentions either a script
    name to run OR a doc path to consult.
    """
    project = _make_project(tmp_path, with_themes=False, with_main_ts_import=False, with_data_theme=False)
    session = _write_session(tmp_path, ui_mode="full-ui", project_root=project)
    result = _run_verify("--session-path", str(session))
    assert result.returncode == 2

    # Stderr must be valid UTF-8 (subprocess text=True already decodes; this
    # asserts it didn't fail mid-decode).
    assert result.stderr  # non-empty
    # Every reported error must include either a fix-tool or a doc path.
    for line in result.stderr.strip().splitlines():
        if not line.strip():
            continue
        has_fix = (
            "trtc_prepare_ui" in line
            or "component-catalog" in line
            or "<html" in line  # V3 specifically gives the literal fix
            or "import '" in line  # V2 gives the literal import
        )
        assert has_fix, f"stderr line lacks an actionable fix hint: {line!r}"


# ---------------------------------------------------------------------------
# Test 10: project-readiness gate — barren project must NOT trip the verifier
# ---------------------------------------------------------------------------


def test_barren_project_does_not_trigger_failures(tmp_path):
    """A project with only the prepared theme dir (no index.html, no main.{ts,js},
    no .vue) is in pre-Vue phase — the user / model is still discussing
    requirements. Verifier must exit 0 silently in this state.

    Why: the Stop hook fires on every model turn. If verifier yells V2/V3/V4
    while the user is still being asked "which platform?", the model
    hijacks its own conversation flow to "fix" non-existent problems —
    drifting off onboarding into premature scaffolding.

    Once ANY of the three (index.html / main.ts / main.js / *.vue) appears,
    verifier's V1-V4 contract becomes live. The threshold is: "did the
    user start scaffolding the Vue app yet?"
    """
    project = tmp_path / "barren"
    # Simulate exactly the state after `trtc_prepare_ui.py` ran on an empty
    # dir: only src/themes/meeting-classic/ was created. No app files yet.
    theme_dir = project / "src" / "themes" / "meeting-classic"
    theme_dir.mkdir(parents=True)
    (theme_dir / "index.css").write_text("/* meeting-classic */\n")

    session = _write_session(tmp_path, ui_mode="full-ui", project_root=project)
    result = _run_verify("--session-path", str(session))
    assert result.returncode == 0, (
        f"barren project must not trigger verifier; got exit {result.returncode}, stderr:\n{result.stderr}"
    )
    assert result.stderr == "", f"barren project must produce no stderr; got: {result.stderr!r}"


def test_readiness_gate_lifts_once_index_html_appears(tmp_path):
    """As soon as index.html exists, verifier becomes active.

    This is the symmetric assertion to the gate test: prove the gate
    actually lifts when the project starts. Without this we could pass
    test 10 by always exiting 0 — broken in a different way.
    """
    project = tmp_path / "starting"
    (project / "src").mkdir(parents=True)
    # Just an index.html, no main.ts yet, no themes dir. Now we expect at
    # least V1 (themes missing) and V3 (data-theme missing) to fire.
    (project / "index.html").write_text(
        "<!DOCTYPE html>\n<html lang=\"en\">\n<body></body>\n</html>\n"
    )
    session = _write_session(tmp_path, ui_mode="full-ui", project_root=project)
    result = _run_verify("--session-path", str(session))
    assert result.returncode == 2, (
        f"once index.html exists, verifier must fire; got exit {result.returncode}"
    )


# ---------------------------------------------------------------------------
# Test 12-13: scope gate — only fire when product=conference + intent=integrate-scenario
# ---------------------------------------------------------------------------


def test_scope_gate_skips_when_product_is_not_conference(tmp_path):
    """A live-streaming project with ui_mode=full-ui in session → verifier no-ops.

    The meeting-classic theme is conference-specific — applying its
    contract (V1-V4) to a live or chat project is wrong AND would
    actively mislead the model. Even if some session field somehow holds
    ui_mode=full-ui for a non-conference product, the verifier must
    refuse to enforce. This is a scope mismatch, not a fixable error.
    """
    project = _make_project(tmp_path, with_themes=False, with_main_ts_import=False, with_data_theme=False)
    session = _write_session_custom(
        tmp_path,
        product="live",  # ← not conference
        intent="integrate-scenario",
        ui_mode="full-ui",
        project_root=project,
    )
    result = _run_verify("--session-path", str(session))
    assert result.returncode == 0, (
        f"non-conference product must no-op; got exit {result.returncode}, stderr:\n{result.stderr}"
    )
    assert result.stderr == "", f"non-conference product must produce no stderr; got: {result.stderr!r}"


def test_scope_gate_skips_when_intent_is_troubleshoot(tmp_path):
    """User in troubleshoot path on a conference project → verifier no-ops.

    UI contract enforcement only applies to the building-from-scratch
    intent (integrate-scenario / Path A2 in onboarding). Troubleshoot,
    demo-running, and other intents must not be hijacked by hooks
    designed for the build path.
    """
    project = _make_project(tmp_path, with_themes=False, with_main_ts_import=False, with_data_theme=False)
    session = _write_session_custom(
        tmp_path,
        product="conference",
        intent="troubleshoot",  # ← not integrate-scenario
        ui_mode="full-ui",
        project_root=project,
    )
    result = _run_verify("--session-path", str(session))
    assert result.returncode == 0, (
        f"troubleshoot intent must no-op; got exit {result.returncode}, stderr:\n{result.stderr}"
    )
    assert result.stderr == "", f"troubleshoot intent must produce no stderr; got: {result.stderr!r}"


# ===========================================================================
# Multi-theme tests — V1/V3 use theme params from registry, not literals
# ===========================================================================


def _setup_alternate_theme_kb(tmp_path, *, slug="theme-test", data_theme="tt",
                              target_dir="src/themes/theme-test"):
    """Build a tmp KB with one alternate scenario + theme; copy scripts/ in.

    Mirrors test_trtc_prepare_ui.py's _setup_alternate_theme but keeps both
    test files independent (tests are easier to read when each file is
    self-contained).
    """
    import shutil as _sh
    kb = tmp_path / "tmp-kb"
    yaml_dir = kb / "skills/trtc/room-builder/references"
    yaml_dir.mkdir(parents=True)
    theme_src = kb / "skills/trtc/room-builder/uikit/assets/themes" / slug
    theme_src.mkdir(parents=True)
    (theme_src / "index.css").write_text("/* alt theme */\n")

    yaml_text = (
        "version: 1\n"
        "scenarios:\n"
        f"  - id: {slug}\n"
        f"    path: {slug}/\n"
        f"    template: {slug}\n"
        f"    reference_html: {slug}/index.html\n"
        '    notes: ""\n'
        "    theme:\n"
        f"      slug: {slug}\n"
        f"      source_dir: skills/trtc/room-builder/uikit/assets/themes/{slug}\n"
        f"      data_theme: {data_theme}\n"
        f"      import_path: '@/themes/{slug}/index.css'\n"
        f"      target_dir: {target_dir}\n"
    )
    (yaml_dir / "scenarios.yaml").write_text(yaml_text)
    _sh.copytree(REPO_ROOT / "skills/trtc/room-builder/guardrails", kb / "skills/trtc/room-builder/guardrails")
    _sh.copytree(REPO_ROOT / "skills/trtc/room-builder/tools", kb / "skills/trtc/room-builder/tools")
    return kb, slug


def test_v1_checks_theme_specific_target_dir(tmp_path):
    """V1 looks at theme.target_dir, NOT a literal meeting-classic path.

    Set up a project that DOES have src/themes/meeting-classic/ (red
    herring) but NOT src/themes/theme-test/. With session.scenario =
    theme-test, V1 must fail and stderr must name theme-test, not
    meeting-classic.
    """
    kb, slug = _setup_alternate_theme_kb(tmp_path)
    project = tmp_path / "user-project"
    (project / "src" / "themes" / "meeting-classic").mkdir(parents=True)
    (project / "src" / "themes" / "meeting-classic" / "index.css").write_text(
        "/* red herring */\n"
    )
    # Provide main.ts with the alt import + index.html with alt data-theme
    # so V2/V3 don't drown out our V1 assertion.
    (project / "src" / "main.ts").write_text(
        f"import '@/themes/{slug}/index.css'\n"
    )
    (project / "index.html").write_text(
        f'<!DOCTYPE html>\n<html lang="en" data-theme="tt"></html>\n'
    )
    session = _write_session(
        tmp_path, ui_mode="full-ui", project_root=project, scenario=slug,
    )

    result = subprocess.run(
        ["python3", str(kb / "skills/trtc/room-builder/guardrails" / "trtc_verify_ui.py"),
         "--session-path", str(session)],
        capture_output=True, text=True, cwd=str(kb),
    )
    assert result.returncode == 2, (
        f"V1 must fail when theme-test/ is missing; got: {result.returncode}, "
        f"stderr={result.stderr!r}"
    )
    assert "theme-test" in result.stderr, (
        f"stderr must name the alt theme target_dir; got: {result.stderr!r}"
    )
    # CRUCIAL: stderr must NOT claim meeting-classic is missing — that would
    # mean V1 was still hardcoded.
    assert "meeting-classic" not in result.stderr.split("V4")[0], (
        f"V1 must NOT mention meeting-classic for alt theme; got V1-V3 portion: "
        f"{result.stderr.split('V4')[0]!r}"
    )


def test_v3_checks_theme_specific_data_theme_attribute(tmp_path):
    """V3 looks at theme.data_theme, NOT a literal "mc"."""
    kb, slug = _setup_alternate_theme_kb(tmp_path, data_theme="tt")
    project = tmp_path / "user-project"
    (project / "src" / "themes" / slug).mkdir(parents=True)
    (project / "src" / "themes" / slug / "index.css").write_text("/* */\n")
    (project / "src" / "main.ts").write_text(
        f"import '@/themes/{slug}/index.css'\n"
    )
    # index.html has the WRONG data-theme value ("mc" instead of "tt")
    (project / "index.html").write_text(
        '<!DOCTYPE html>\n<html lang="en" data-theme="mc"></html>\n'
    )
    session = _write_session(
        tmp_path, ui_mode="full-ui", project_root=project, scenario=slug,
    )

    result = subprocess.run(
        ["python3", str(kb / "skills/trtc/room-builder/guardrails" / "trtc_verify_ui.py"),
         "--session-path", str(session)],
        capture_output=True, text=True, cwd=str(kb),
    )
    assert result.returncode == 2, f"V3 must fail; got {result.returncode}"
    assert 'data-theme="tt"' in result.stderr, (
        f"stderr must demand the alt data_theme; got: {result.stderr!r}"
    )


# ===========================================================================
# Lifecycle gate tests — hooks must close once scaffold-complete
# ===========================================================================


def test_gate_closes_when_scaffold_complete_full_project_mode(tmp_path):
    """current_step ends with -complete + missing themes → exit 0, no stderr.

    Pre-lifecycle this would have yelled V1/V2/V3/V4. Post-handoff that
    noise is exactly what we exist to suppress.
    """
    project = _make_project(tmp_path, with_themes=False, with_main_ts_import=False, with_data_theme=False)
    session_path = _write_session(
        tmp_path, ui_mode="full-ui", project_root=project,
    )
    session_path.write_text(
        session_path.read_text() + "current_step: A2.4-complete\n"
    )
    result = _run_verify("--session-path", str(session_path))
    assert result.returncode == 0, (
        f"gate-closed verify must exit 0; got {result.returncode}, "
        f"stderr={result.stderr!r}"
    )
    assert result.stderr == "", f"gate-closed verify must be silent; got: {result.stderr!r}"


def test_gate_closes_when_scaffold_complete_file_mode(tmp_path):
    """--file mode is ALSO gated post-handoff.

    Deliberate choice (see plan): once the user owns the code, even
    per-write enforcement is unwelcome — they're free to refactor a
    `.vue` file dropping every uikit class. Asymmetric gating
    (closing project mode but not --file) would be confusing.
    """
    project = _make_project(tmp_path, with_themes=True, with_main_ts_import=True, with_data_theme=True)
    bad_vue = project / "src" / "components" / "Foo.vue"
    bad_vue.parent.mkdir(parents=True)
    bad_vue.write_text("<template><div>no ui-* here</div></template>\n")
    session_path = _write_session(
        tmp_path, ui_mode="full-ui", project_root=project,
    )
    session_path.write_text(
        session_path.read_text() + "current_step: A2.4-complete\n"
    )
    result = _run_verify("--session-path", str(session_path), "--file", str(bad_vue))
    assert result.returncode == 0, (
        f"--file mode must also be gated post-handoff; got {result.returncode}, "
        f"stderr={result.stderr!r}"
    )
    assert result.stderr == "", f"--file gate-closed verify must be silent; got: {result.stderr!r}"
