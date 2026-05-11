"""Unit tests for .claude/skills/trtc/room-builder/guardrails/trtc_prepare_ui.py.

Same TDD discipline as test_trtc_verify_ui.py. Each test pins one observable
behavior of the preparer; implementation grown one test at a time.
"""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / ".claude/skills/trtc/room-builder/guardrails"))

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PREPARE_SCRIPT = REPO_ROOT / ".claude/skills/trtc/room-builder/guardrails" / "trtc_prepare_ui.py"
VERIFY_SCRIPT = REPO_ROOT / ".claude/skills/trtc/room-builder/guardrails" / "trtc_verify_ui.py"
THEME_SOURCE = REPO_ROOT / ".claude" / "skills" / "trtc" / "room-builder" / "uikit" / "assets" / "themes" / "meeting-classic"


def _write_session(tmp_path, *, ui_mode, project_root=None, scenario="general-meeting"):
    """Write a minimal .trtc-session.yaml; return its path.

    `scenario` defaults to general-meeting (registered with meeting-classic
    theme). All pre-registry tests assumed this implicitly; we now write it
    explicitly so in_scope() — which now requires a registered scenario —
    keeps returning True for them.
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
                          ui_mode="full-ui", project_root=None, scenario="general-meeting"):
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


def _run_prepare(*args):
    return subprocess.run(
        ["python3", str(PREPARE_SCRIPT), *args],
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Test 1: noop when ui_mode is not full-ui
# ---------------------------------------------------------------------------


def test_noop_when_ui_mode_not_full_ui(tmp_path):
    """Session with ui_mode != full-ui → exit 0, no work done.

    Same fundamental contract as the verifier. The SessionStart hook fires
    on every Claude Code session start in this repo; if we'd mutate state
    just because ui_mode is null, we'd corrupt unrelated workflows.
    """
    project = tmp_path / "user-project"
    project.mkdir()
    session = _write_session(tmp_path, ui_mode=None, project_root=project)
    result = _run_prepare("--session-path", str(session))
    assert result.returncode == 0, f"expected exit 0; stderr={result.stderr}"
    # No themes dir was created.
    assert not (project / "src" / "themes").exists()


# ---------------------------------------------------------------------------
# Test 2: project_root path doesn't exist → exit 1 with clear error
# ---------------------------------------------------------------------------


def test_fails_when_project_root_missing(tmp_path):
    """Session points at a nonexistent path → exit 1, stderr names the path.

    We refuse to mkdir-create an arbitrary path the user typed wrong; better
    to surface the typo than to silently materialize a directory in /tmp.
    Symptom of misconfiguration the model can self-correct from.
    """
    bogus = tmp_path / "definitely-does-not-exist"
    session = _write_session(tmp_path, ui_mode="full-ui", project_root=bogus)
    result = _run_prepare("--session-path", str(session))
    assert result.returncode == 1, f"expected exit 1; got {result.returncode}; stderr={result.stderr}"
    assert str(bogus) in result.stderr, f"stderr must name missing path; got: {result.stderr!r}"


# ---------------------------------------------------------------------------
# Test 3: P1 copies the meeting-classic theme into src/themes/
# ---------------------------------------------------------------------------


def _make_min_project(tmp_path):
    """Minimum viable user project: index.html + src/main.ts. No themes."""
    root = tmp_path / "user-project"
    (root / "src").mkdir(parents=True)
    (root / "src" / "main.ts").write_text("import { createApp } from 'vue'\n")
    (root / "index.html").write_text(
        "<!DOCTYPE html>\n<html lang=\"zh-CN\">\n  <body></body>\n</html>\n"
    )
    return root


def test_p1_copies_themes_on_first_run(tmp_path):
    """Empty project → after prepare, meeting-classic/ is fully populated.

    Proves shutil.copytree actually recursed, not just touched a stub file.
    Asserts on index.css AND an atom file so a surface-level copy would fail
    this test.
    """
    project = _make_min_project(tmp_path)
    session = _write_session(tmp_path, ui_mode="full-ui", project_root=project)
    result = _run_prepare("--session-path", str(session))
    assert result.returncode == 0, f"expected exit 0; stderr={result.stderr}"

    theme = project / "src" / "themes" / "meeting-classic"
    assert (theme / "index.css").exists(), "meeting-classic/index.css must exist after P1"
    atoms = theme / "components" / "atoms"
    assert atoms.exists() and any(atoms.iterdir()), (
        f"meeting-classic/components/atoms must be populated; contents: {list(atoms.iterdir()) if atoms.exists() else 'missing'}"
    )


# ---------------------------------------------------------------------------
# Test 4: P1 is idempotent — re-running must not error
# ---------------------------------------------------------------------------


def test_p1_idempotent_on_second_run(tmp_path):
    """prepare × 2 back-to-back → second run also exits 0 with no stderr.

    Idempotence is the SessionStart hook contract: the hook fires on every
    session resume, and the theme is already there 99% of the time. Without
    dirs_exist_ok=True, the second run would raise FileExistsError.
    """
    project = _make_min_project(tmp_path)
    session = _write_session(tmp_path, ui_mode="full-ui", project_root=project)
    first = _run_prepare("--session-path", str(session))
    assert first.returncode == 0, f"first run failed: {first.stderr}"
    second = _run_prepare("--session-path", str(session))
    assert second.returncode == 0, f"second run failed: {second.stderr}"
    assert second.stderr == "", f"idempotent run must be silent on stderr; got: {second.stderr!r}"


# ---------------------------------------------------------------------------
# Test 5: P2 adds theme import to main.ts when absent
# ---------------------------------------------------------------------------


def test_p2_adds_import_when_missing(tmp_path):
    """main.ts without the theme import → after prepare, import appears exactly once.

    This is what actually wires the copied CSS into the Vue app. Without it
    the theme is dead weight.
    """
    project = _make_min_project(tmp_path)
    session = _write_session(tmp_path, ui_mode="full-ui", project_root=project)
    result = _run_prepare("--session-path", str(session))
    assert result.returncode == 0, f"stderr: {result.stderr}"
    body = (project / "src" / "main.ts").read_text()
    occurrences = body.count("themes/meeting-classic")
    assert occurrences == 1, (
        f"expected exactly 1 theme import; got {occurrences}. main.ts:\n{body}"
    )
    assert "import" in body, "must be an import statement, not just a mention"


# ---------------------------------------------------------------------------
# Test 6: P2 does not duplicate the import when already present
# ---------------------------------------------------------------------------


def test_p2_does_not_duplicate_import(tmp_path):
    """main.ts already has the import → prepare leaves the file byte-identical.

    The SessionStart hook fires on every session resume; if P2 duplicated the
    import we'd accumulate a new copy each resume. Byte-exact comparison is
    the strictest way to pin this.
    """
    project = _make_min_project(tmp_path)
    main_ts = project / "src" / "main.ts"
    original = "import '@/themes/meeting-classic/index.css'\nimport { createApp } from 'vue'\n"
    main_ts.write_text(original)
    session = _write_session(tmp_path, ui_mode="full-ui", project_root=project)
    result = _run_prepare("--session-path", str(session))
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert main_ts.read_text() == original, (
        f"main.ts must be unchanged; got:\n{main_ts.read_text()}"
    )


# ---------------------------------------------------------------------------
# Test 7: P2 falls back to src/main.js when main.ts is absent
# ---------------------------------------------------------------------------


def test_p2_handles_main_js_fallback(tmp_path):
    """Vite project using plain JS (no TS) → patches main.js.

    Reality check: not every Vue project uses TypeScript. If P2 only knew
    about .ts, JS projects would silently skip wiring. Explicit fallback
    keeps the contract universal.
    """
    root = tmp_path / "js-project"
    (root / "src").mkdir(parents=True)
    main_js = root / "src" / "main.js"
    main_js.write_text("import { createApp } from 'vue'\n")
    (root / "index.html").write_text("<!DOCTYPE html>\n<html lang=\"en\"></html>\n")
    session = _write_session(tmp_path, ui_mode="full-ui", project_root=root)
    result = _run_prepare("--session-path", str(session))
    assert result.returncode == 0, f"stderr: {result.stderr}"
    body = main_js.read_text()
    assert "themes/meeting-classic" in body, f"main.js must be patched; got:\n{body}"


# ---------------------------------------------------------------------------
# Test 8: P3 adds data-theme="mc" to <html> when absent
# ---------------------------------------------------------------------------


def test_p3_adds_data_theme_when_missing(tmp_path):
    """`<html lang="zh-CN">` → `<html lang="zh-CN" data-theme="mc">`.

    Must preserve the existing `lang` attribute untouched and not introduce
    newline/whitespace oddities.
    """
    project = _make_min_project(tmp_path)
    session = _write_session(tmp_path, ui_mode="full-ui", project_root=project)
    result = _run_prepare("--session-path", str(session))
    assert result.returncode == 0, f"stderr: {result.stderr}"
    html = (project / "index.html").read_text()
    assert 'data-theme="mc"' in html, f"<html> must gain data-theme; got:\n{html}"
    assert 'lang="zh-CN"' in html, f"existing lang attr must be preserved; got:\n{html}"


# ---------------------------------------------------------------------------
# Test 9: P3 is idempotent — already has data-theme → file bytes unchanged
# ---------------------------------------------------------------------------


def test_p3_idempotent(tmp_path):
    """index.html already has data-theme="mc" → byte-identical after prepare.

    Symmetric to test_p2_does_not_duplicate. Matters for repeated
    SessionStart runs.
    """
    root = tmp_path / "p3-project"
    (root / "src").mkdir(parents=True)
    (root / "src" / "main.ts").write_text(
        "import '@/themes/meeting-classic/index.css'\nimport { createApp } from 'vue'\n"
    )
    # Pre-populate theme so P1 is a no-op too.
    (root / "src" / "themes" / "meeting-classic").mkdir(parents=True)
    (root / "src" / "themes" / "meeting-classic" / "index.css").write_text("/* stub */\n")
    original = '<!DOCTYPE html>\n<html lang="zh-CN" data-theme="mc">\n  <body></body>\n</html>\n'
    html = root / "index.html"
    html.write_text(original)
    session = _write_session(tmp_path, ui_mode="full-ui", project_root=root)
    result = _run_prepare("--session-path", str(session))
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert html.read_text() == original, (
        f"index.html must be byte-identical; got:\n{html.read_text()}"
    )


# ---------------------------------------------------------------------------
# Test 10: --dry-run writes nothing, but stdout lists planned ops
# ---------------------------------------------------------------------------


def test_dry_run_writes_nothing(tmp_path):
    """--dry-run on unpatched project → stdout lists 3 planned ops, disk unchanged.

    Useful for CI / manual inspection without committing to changes.
    """
    project = _make_min_project(tmp_path)
    snapshot = {
        p.relative_to(project): p.read_bytes() for p in project.rglob("*") if p.is_file()
    }
    session = _write_session(tmp_path, ui_mode="full-ui", project_root=project)
    result = _run_prepare("--session-path", str(session), "--dry-run")
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "P1" in result.stdout and "P2" in result.stdout and "P3" in result.stdout, (
        f"dry-run must list all 3 ops; stdout: {result.stdout!r}"
    )
    assert "dry-run" in result.stdout.lower(), f"stdout must mark mode; got: {result.stdout!r}"
    # Disk unchanged.
    after = {p.relative_to(project): p.read_bytes() for p in project.rglob("*") if p.is_file()}
    assert snapshot == after, "dry-run must not mutate any file"
    assert not (project / "src" / "themes").exists(), "dry-run must not create themes dir"


# ---------------------------------------------------------------------------
# Test 11: end-to-end — prepare then verify agrees on V1-V3 contract
# ---------------------------------------------------------------------------


def test_prepare_then_verify_passes_v1_v2_v3(tmp_path):
    """After prepare, verify's V1-V3 checks pass.

    This is the contract pin between the two scripts. If verify and prepare
    drift apart (e.g. prepare writes `data-theme='mc'` with single quotes
    but verify only accepts double) this test catches it first. V4 is
    intentionally left failing here because SFCs still have 0 ui-* — that's
    a separate contract between the model and verify, not prepare.
    """
    project = _make_min_project(tmp_path)
    session = _write_session(tmp_path, ui_mode="full-ui", project_root=project)

    prep = _run_prepare("--session-path", str(session))
    assert prep.returncode == 0, f"prepare failed: {prep.stderr}"

    verify = subprocess.run(
        ["python3", str(VERIFY_SCRIPT), "--session-path", str(session)],
        capture_output=True,
        text=True,
    )
    # V4 will still fail (no .vue with ui-* yet); V1-V3 must pass.
    if verify.returncode != 0:
        # Allow failure ONLY if the only error is V4.
        lines = [l for l in verify.stderr.strip().splitlines() if l.strip()]
        non_v4 = [l for l in lines if not l.startswith("V4")]
        assert not non_v4, (
            f"V1-V3 must pass after prepare; these errors remain:\n"
            + "\n".join(non_v4)
        )


# ---------------------------------------------------------------------------
# Test 12-13: scope gate — prepare must not act on out-of-scope sessions
# ---------------------------------------------------------------------------


def test_prepare_scope_gate_skips_non_conference_product(tmp_path):
    """Live-streaming project with ui_mode=full-ui in session → prepare no-ops.

    The meeting-classic theme is conference-specific. Copying it into a
    live or chat project root would corrupt unrelated work. Prepare
    must refuse — silently exit 0, no theme copy, no main.ts patch, no
    index.html patch.
    """
    project = _make_min_project(tmp_path)
    session = _write_session_custom(
        tmp_path,
        product="live",  # ← not conference
        intent="integrate-scenario",
        ui_mode="full-ui",
        project_root=project,
    )
    result = _run_prepare("--session-path", str(session))
    assert result.returncode == 0, f"non-conference must exit 0; stderr: {result.stderr}"
    assert not (project / "src" / "themes").exists(), (
        "non-conference product must NOT receive meeting-classic theme; "
        "this is a scope mismatch, not a fixable error"
    )
    body = (project / "src" / "main.ts").read_text()
    assert "themes/meeting-classic" not in body, (
        f"main.ts must NOT be patched for non-conference; got:\n{body}"
    )


def test_prepare_scope_gate_skips_non_integrate_intent(tmp_path):
    """User in troubleshoot path on conference project → prepare no-ops.

    Theme prep belongs to the build-from-scratch flow. A user diagnosing
    a bug on an already-built conference app should not have their
    project mutated by SessionStart hook.
    """
    project = _make_min_project(tmp_path)
    session = _write_session_custom(
        tmp_path,
        product="conference",
        intent="troubleshoot",  # ← not integrate-scenario
        ui_mode="full-ui",
        project_root=project,
    )
    result = _run_prepare("--session-path", str(session))
    assert result.returncode == 0, f"troubleshoot intent must exit 0; stderr: {result.stderr}"
    assert not (project / "src" / "themes").exists(), (
        "troubleshoot intent must NOT mutate the project"
    )


# ===========================================================================
# Multi-theme tests — prove parameters flow yaml → registry → script
# ===========================================================================
#
# These tests use a tmp scenarios.yaml + tmp theme dir to prove that NOTHING
# in trtc_prepare_ui.py is still hardcoded to meeting-classic. Earlier tests
# happen to use general-meeting (which IS meeting-classic), so they couldn't
# distinguish "registry lookup works" from "meeting-classic happens to be
# hardcoded everywhere". These do.


def _setup_alternate_theme(tmp_path, *, slug="theme-test", data_theme="tt",
                           target_dir="src/themes/theme-test"):
    """Build a tmp KB with a single 'theme-test' scenario + minimal theme dir.

    Returns (kb_root, scenario_id). The script tree is COPIED (not symlinked)
    into kb_root so REPO_ROOT = Path(__file__).resolve().parent.parent points
    at the tmp kb, not the real one. Symlinking would defeat .resolve().
    """
    import shutil as _sh
    kb = tmp_path / "tmp-kb"
    yaml_dir = kb / ".claude/skills/trtc/room-builder/references"
    yaml_dir.mkdir(parents=True)
    theme_src = kb / ".claude/skills/trtc/room-builder/uikit/assets/themes" / slug
    theme_src.mkdir(parents=True)
    # Marker file — proves recursive copy actually copied THIS theme.
    (theme_src / "marker.txt").write_text(f"slug:{slug}\n")
    # Minimal index.css so verify's V1 has something real to check.
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
        f"      source_dir: .claude/skills/trtc/room-builder/uikit/assets/themes/{slug}\n"
        f"      data_theme: {data_theme}\n"
        f"      import_path: '@/themes/{slug}/index.css'\n"
        f"      target_dir: {target_dir}\n"
    )
    (yaml_dir / "scenarios.yaml").write_text(yaml_text)

    # Copy scripts/ tree so the script's REPO_ROOT-via-__file__ lands inside
    # the tmp kb rather than the real repo. Symlink would resolve back.
    _sh.copytree(REPO_ROOT / ".claude/skills/trtc/room-builder/guardrails", kb / ".claude/skills/trtc/room-builder/guardrails")
    _sh.copytree(REPO_ROOT / ".claude/skills/trtc/room-builder/tools", kb / ".claude/skills/trtc/room-builder/tools")
    return kb, slug


def test_p1_uses_theme_specific_target_dir_for_alternate_theme(tmp_path):
    """Multi-theme proof: prepare against scenario=theme-test copies to
    src/themes/theme-test/ — NOT meeting-classic.

    Pins that THEME_SOURCE / target_dir / etc. flow from yaml, not literals.
    """
    kb, slug = _setup_alternate_theme(tmp_path)
    project = _make_min_project(tmp_path)
    session = _write_session(
        tmp_path, ui_mode="full-ui", project_root=project, scenario=slug,
    )
    result = subprocess.run(
        ["python3", str(kb / ".claude/skills/trtc/room-builder/guardrails" / "trtc_prepare_ui.py"),
         "--session-path", str(session)],
        capture_output=True, text=True, cwd=str(kb),
    )
    assert result.returncode == 0, f"prepare failed: {result.stderr}"

    # Theme-test files copied to the alt target_dir.
    assert (project / "src" / "themes" / slug / "marker.txt").exists(), (
        f"marker.txt missing under alt target_dir; actual project tree:\n"
        f"{list(project.rglob('*'))}\n stderr: {result.stderr}\n stdout: {result.stdout}"
    )
    # Did NOT mistakenly create meeting-classic.
    assert not (project / "src" / "themes" / "meeting-classic").exists(), (
        "alt-theme run must NOT create meeting-classic dir"
    )


def test_p3_uses_theme_specific_data_theme_attribute(tmp_path):
    """Pins data_theme parameter flows from yaml, not literal "mc"."""
    kb, slug = _setup_alternate_theme(tmp_path, data_theme="tt")
    project = _make_min_project(tmp_path)
    session = _write_session(
        tmp_path, ui_mode="full-ui", project_root=project, scenario=slug,
    )
    result = subprocess.run(
        ["python3", str(kb / ".claude/skills/trtc/room-builder/guardrails" / "trtc_prepare_ui.py"),
         "--session-path", str(session)],
        capture_output=True, text=True, cwd=str(kb),
    )
    assert result.returncode == 0, f"prepare failed: {result.stderr}"

    html = (project / "index.html").read_text()
    assert 'data-theme="tt"' in html, f"index.html must carry the alt data-theme; got:\n{html}"
    assert 'data-theme="mc"' not in html, "alt run must NOT inject mc"


# ===========================================================================
# Lifecycle gate tests — hooks must close once scaffold-complete
# ===========================================================================


def test_gate_closes_when_scaffold_complete(tmp_path):
    """current_step ends with -complete → prepare exits 0, project untouched.

    Once onboarding is done, the user owns the code. Prepare must not
    re-create themes (which would clobber any user customisations) or
    re-touch entrypoint files (which could undo refactors).
    """
    project = _make_min_project(tmp_path)
    # Add current_step: A2.4-complete (matches real production session).
    session_path = _write_session(
        tmp_path, ui_mode="full-ui", project_root=project,
    )
    session_path.write_text(
        session_path.read_text() + "current_step: A2.4-complete\n"
    )
    result = _run_prepare("--session-path", str(session_path))
    assert result.returncode == 0, f"gate-closed run must exit 0; stderr: {result.stderr}"
    assert not (project / "src" / "themes").exists(), (
        "gate-closed run must NOT copy themes — user owns the code now"
    )


def test_gate_open_when_step_in_progress(tmp_path):
    """current_step ends with anything else → prepare runs as usual.

    Pins the symmetric assertion: gate fires only on the specific complete
    suffix. Mid-flight onboarding (A2.4 / A2.4-Q1) keeps the gate open.
    """
    project = _make_min_project(tmp_path)
    session_path = _write_session(
        tmp_path, ui_mode="full-ui", project_root=project,
    )
    session_path.write_text(
        session_path.read_text() + "current_step: A2.4\n"
    )
    result = _run_prepare("--session-path", str(session_path))
    assert result.returncode == 0
    assert (project / "src" / "themes" / "meeting-classic" / "index.css").exists(), (
        "in-progress step must allow prepare to copy themes"
    )
