"""Code injector — overwrites placeholder files in workspace with AI-generated code.

Responsibilities:
1. Auto-register injection points not yet declared in INJECTION.json (template only ships one example).
2. Copy AI-generated code files into workspace at declared targets.
3. **Entry Bridge Generation** (三端统一): After injection, scan injected files for entry-point
   classes/functions and auto-generate platform-specific bridge code so the App loads the injected
   code on startup.
   - iOS: detect UIViewController subclass → overwrite SceneDelegate.swift
   - Android: detect Activity subclass or @Composable entry → overwrite MainActivity.kt
   - Web: detect exported entry (default export / named export) → patch main.ts to import & mount
   (Rule: "Injected code must be reachable from the application entry point.")
"""
import json
import re
import shutil
import subprocess
from pathlib import Path


class InjectError(Exception):
    pass


def _load_injection_config(workspace: Path) -> dict:
    """Load INJECTION.json from workspace."""
    return json.loads((workspace / "INJECTION.json").read_text())


def _allowed_targets(cfg: dict) -> set[str]:
    return {p["path"] for p in cfg["injection_points"]}


def _ensure_injection_points(workspace: Path, injection_map: dict) -> None:
    """Auto-register injection targets from case's demo_injection_map into INJECTION.json.

    The template project only ships a single example injection point (GeneratedView.swift).
    The eval tool is responsible for supplementing additional injection points declared by
    each test case's demo_injection_map before performing the actual code injection.
    """
    cfg = _load_injection_config(workspace)
    existing_paths = {p["path"] for p in cfg["injection_points"]}

    modified = False
    for ai_file, point in injection_map.items():
        target_rel = point.target_file if hasattr(point, "target_file") else point.get("target_file", "")
        if not target_rel:
            continue
        if target_rel not in existing_paths:
            # Derive a human-readable name from the filename
            name = Path(target_rel).name
            replace_mode = (
                point.replace_mode if hasattr(point, "replace_mode")
                else point.get("replace_mode", "overwrite")
            )
            cfg["injection_points"].append({
                "name": name,
                "path": target_rel,
                "placeholder": True,
                "replace_mode": replace_mode,
            })
            existing_paths.add(target_rel)
            modified = True

    if modified:
        (workspace / "INJECTION.json").write_text(
            json.dumps(cfg, indent=2, ensure_ascii=False) + "\n"
        )


# ---------------------------------------------------------------------------
# Entry Bridge: ensure injected code is loaded at app startup (三端统一)
# ---------------------------------------------------------------------------

# --- iOS ---
# Matches: class Foo: UIViewController, final class Bar : UIViewController, etc.
_IOS_VC_CLASS_RE = re.compile(
    r"(?:final\s+)?class\s+(\w+)\s*:\s*(?:\w+,\s*)*UIViewController"
)

# Matches custom init (not required init?(coder:)) to extract parameter list.
# Examples:
#   init(liveID: String, liveName: String) {
#   init(roomID: String) {
#   convenience init(config: Config = .default) {
_IOS_CUSTOM_INIT_RE = re.compile(
    r"(?:convenience\s+)?init\s*\(([^)]*)\)\s*\{",
    re.MULTILINE,
)

# Default value generators for common Swift types
_SWIFT_TYPE_DEFAULTS: dict[str, str] = {
    "String": '""',
    "Int": "0",
    "UInt": "0",
    "Double": "0.0",
    "Float": "0.0",
    "Bool": "false",
    "CGFloat": "0.0",
    "CGRect": ".zero",
    "CGSize": ".zero",
    "CGPoint": ".zero",
}


def _parse_swift_init_params(param_str: str) -> list[tuple[str, str, str | None]]:
    """Parse Swift init parameter string into list of (label, type, default_or_None).

    Examples:
        "liveID: String, liveName: String" -> [("liveID", "String", None), ("liveName", "String", None)]
        "_ id: String, name: String = \"\"" -> [("_", "String", "\"\""), ("name", "String", "\"\"")]
    """
    params = []
    if not param_str.strip():
        return params

    # Split by comma, but respect nested generics/closures
    depth = 0
    current = []
    for ch in param_str:
        if ch in "(<[":
            depth += 1
            current.append(ch)
        elif ch in ")>]":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            params.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        params.append("".join(current).strip())

    result = []
    for p in params:
        # Strip attributes like @escaping, @autoclosure
        p = re.sub(r"@\w+\s*", "", p).strip()
        # Check for default value
        default_val = None
        if "=" in p:
            parts = p.split("=", 1)
            p = parts[0].strip()
            default_val = parts[1].strip()
        # Parse "label: Type" or "_ label: Type" or "externalLabel internalLabel: Type"
        colon_idx = p.find(":")
        if colon_idx == -1:
            continue
        label_part = p[:colon_idx].strip()
        type_part = p[colon_idx + 1:].strip()
        # Handle "external internal" or just "label"
        label_tokens = label_part.split()
        if len(label_tokens) >= 2:
            external_label = label_tokens[0]  # _ or named
        else:
            external_label = label_tokens[0]
        result.append((external_label, type_part, default_val))
    return result


def _generate_init_call(class_name: str, params: list[tuple[str, str, str | None]]) -> str:
    """Generate a Swift initializer call with default values for parameters without defaults.

    Returns e.g.: 'AnchorLiveViewController(liveID: "", liveName: "")'
    """
    if not params:
        return f"{class_name}()"

    args = []
    for label, type_name, default_val in params:
        if default_val is not None:
            # Has default value, can omit
            continue
        # Generate a sensible default based on type
        # Strip optionals
        base_type = type_name.rstrip("?").strip()
        if type_name.endswith("?"):
            val = "nil"
        elif base_type in _SWIFT_TYPE_DEFAULTS:
            val = _SWIFT_TYPE_DEFAULTS[base_type]
        else:
            # Unknown type: try nil if optional, otherwise use .init() or empty string
            val = '""'  # Safest fallback for demo purposes

        if label == "_":
            args.append(val)
        else:
            args.append(f"{label}: {val}")

    if not args:
        return f"{class_name}()"
    return f"{class_name}({', '.join(args)})"

# --- Android ---
# Matches: class Foo : ComponentActivity, class Bar : AppCompatActivity, class Baz : FragmentActivity
_ANDROID_ACTIVITY_RE = re.compile(
    r"(?:abstract\s+)?class\s+(\w+)\s*(?:\(.*?\))?\s*:\s*(?:\w+,\s*)*"
    r"(?:ComponentActivity|AppCompatActivity|FragmentActivity|Activity)"
)
# Matches: class Foo : Fragment (for Fragment-based injection)
_ANDROID_FRAGMENT_RE = re.compile(
    r"(?:abstract\s+)?class\s+(\w+)\s*(?:\(.*?\))?\s*:\s*(?:\w+,\s*)*Fragment\b"
)

# --- Web ---
# Matches: export default function xxx, export default class xxx, export default { ... }
_WEB_DEFAULT_EXPORT_RE = re.compile(
    r"export\s+default\s+(?:(?:function|class)\s+(\w+)|(\{))"
)
# Matches: export function mount/render/init/bootstrap/setup/start/run/main
_WEB_NAMED_ENTRY_RE = re.compile(
    r"export\s+(?:async\s+)?function\s+(mount|render|init|bootstrap|setup|start|run|main)\b"
)
# Matches: export class XxxView / XxxApp / XxxComponent
_WEB_CLASS_EXPORT_RE = re.compile(
    r"export\s+class\s+(\w+(?:View|App|Component|Page|Panel))"
)


# ---------------------------------------------------------------------------
# iOS Entry Bridge
# ---------------------------------------------------------------------------

def _extract_entry_viewcontroller(injected_files: list[Path]) -> tuple[str, str] | None:
    """Scan injected Swift files and return the VC class name + init call expression.

    Returns:
        ("ClassName", "ClassName(param: defaultVal, ...)") or None.
        If the VC has a parameterless init, returns ("ClassName", "ClassName()").
    """
    for f in injected_files:
        if f.suffix != ".swift":
            continue
        content = f.read_text(errors="replace")
        m = _IOS_VC_CLASS_RE.search(content)
        if m:
            class_name = m.group(1)
            # Find all non-required inits in this class
            # We want to detect if there's a parameterless init or if all inits need params
            has_parameterless_init = False
            custom_init_params: list[tuple[str, str, str | None]] | None = None

            for init_match in _IOS_CUSTOM_INIT_RE.finditer(content):
                param_str = init_match.group(1).strip()
                # Skip required init?(coder:)
                if "coder" in param_str and "NSCoder" in param_str:
                    continue
                if not param_str:
                    has_parameterless_init = True
                    break
                # Parse params; if all have defaults, it's effectively parameterless
                params = _parse_swift_init_params(param_str)
                all_have_defaults = all(p[2] is not None for p in params)
                if all_have_defaults:
                    has_parameterless_init = True
                    break
                if custom_init_params is None:
                    # Use the first custom init found
                    custom_init_params = params

            if has_parameterless_init or custom_init_params is None:
                return (class_name, f"{class_name}()")
            else:
                init_call = _generate_init_call(class_name, custom_init_params)
                return (class_name, init_call)
    return None


def _generate_entry_bridge_ios(workspace: Path, _entry_vc_class: str, init_call: str) -> None:
    """Overwrite SceneDelegate.swift to set the injected VC as rootViewController.

    When EVAL_AUTO_RUN_FLOW is set at runtime, delegates to AutoRunCoordinator instead
    of showing the injected VC directly — this enables automated evaluation flows.
    """
    scene_delegate_path = workspace / "MyApplication" / "SceneDelegate.swift"
    if not scene_delegate_path.exists():
        return

    bridge_code = f'''\
//
//  SceneDelegate.swift
//  MyApplication
//
//  Auto-generated by eval tool: entry bridge for injected view.
//

import UIKit
import os.log

private let evalLog = OSLog(subsystem: "com.template.myapplication", category: "eval")

class SceneDelegate: UIResponder, UIWindowSceneDelegate {{

    var window: UIWindow?

    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {{
        guard let windowScene = (scene as? UIWindowScene) else {{ return }}
        let window = UIWindow(windowScene: windowScene)

        // If EVAL_AUTO_RUN_FLOW is set, use AutoRunCoordinator for automated evaluation
        if let autoRunFlow = ProcessInfo.processInfo.environment["EVAL_AUTO_RUN_FLOW"],
           !autoRunFlow.isEmpty {{
            os_log("Entry bridge: EVAL_AUTO_RUN_FLOW=%{{public}}@, delegating to AutoRunCoordinator", log: evalLog, type: .info, autoRunFlow)
            let rootVC = {init_call}
            window.rootViewController = rootVC
            window.makeKeyAndVisible()
            self.window = window
            // Trigger AutoRun after window is visible
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {{
                AutoRunCoordinator.runIfNeeded {{ _ in }}
            }}
        }} else {{
            window.rootViewController = {init_call}
            window.makeKeyAndVisible()
            self.window = window
        }}
    }}

    func sceneDidDisconnect(_ scene: UIScene) {{}}
    func sceneDidBecomeActive(_ scene: UIScene) {{}}
    func sceneWillResignActive(_ scene: UIScene) {{}}
    func sceneWillEnterForeground(_ scene: UIScene) {{}}
    func sceneDidEnterBackground(_ scene: UIScene) {{}}
}}
'''
    scene_delegate_path.write_text(bridge_code)


# ---------------------------------------------------------------------------
# Android Entry Bridge
# ---------------------------------------------------------------------------

def _extract_entry_android(injected_files: list[Path]) -> tuple[str, str] | None:
    """Scan injected Kotlin files for Activity or Fragment subclass.

    Returns:
        ("activity", "ClassName") or ("fragment", "ClassName") or None.
    """
    for f in injected_files:
        if f.suffix != ".kt":
            continue
        content = f.read_text(errors="replace")
        # Prefer Activity match (it can be launched directly)
        m = _ANDROID_ACTIVITY_RE.search(content)
        if m:
            return ("activity", m.group(1))
    # Second pass: look for Fragment
    for f in injected_files:
        if f.suffix != ".kt":
            continue
        content = f.read_text(errors="replace")
        m = _ANDROID_FRAGMENT_RE.search(content)
        if m:
            return ("fragment", m.group(1))
    return None


def _detect_android_package(injected_files: list[Path]) -> str:
    """Extract the package declaration from the first injected .kt file."""
    for f in injected_files:
        if f.suffix != ".kt":
            continue
        content = f.read_text(errors="replace")
        m = re.search(r"^package\s+([\w.]+)", content, re.MULTILINE)
        if m:
            return m.group(1)
    return "com.template.myapplication.generated"


def _generate_entry_bridge_android(workspace: Path, entry_type: str, entry_class: str, entry_package: str) -> None:
    """Overwrite MainActivity.kt to launch the injected Activity or load the injected Fragment."""
    main_activity_path = workspace / "app" / "src" / "main" / "java" / "com" / "template" / "myapplication" / "MainActivity.kt"
    if not main_activity_path.exists():
        return

    if entry_type == "activity":
        bridge_code = f'''\
package com.template.myapplication

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import {entry_package}.{entry_class}

/**
 * Auto-generated by eval tool: entry bridge for injected Activity.
 * Launches [{entry_class}] immediately on startup.
 */
class MainActivity : ComponentActivity() {{
    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)
        // Entry Bridge: launch the injected Activity
        startActivity(Intent(this, {entry_class}::class.java))
        finish()
    }}
}}
'''
    else:
        # Fragment-based: embed in a FrameLayout
        bridge_code = f'''\
package com.template.myapplication

import android.os.Bundle
import androidx.activity.ComponentActivity
import {entry_package}.{entry_class}

/**
 * Auto-generated by eval tool: entry bridge for injected Fragment.
 * Loads [{entry_class}] as the main content.
 */
class MainActivity : ComponentActivity() {{
    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)
        setContentView(android.R.layout.activity_list_item)
        if (savedInstanceState == null) {{
            supportFragmentManager.beginTransaction()
                .replace(android.R.id.content, {entry_class}())
                .commit()
        }}
    }}
}}
'''
    main_activity_path.write_text(bridge_code)


# ---------------------------------------------------------------------------
# Web Entry Bridge
# ---------------------------------------------------------------------------

def _extract_entry_web(injected_files: list[Path]) -> tuple[str, str, Path] | None:
    """Scan injected TS/JS files for an exportable entry point.

    Returns:
        ("default", name_or_empty, file_path) — has a default export
        ("named", function_name, file_path) — has a named entry function (mount/render/init/etc.)
        ("class", class_name, file_path) — has an exported class with View/App/Component suffix
        None — no recognizable entry found.
    """
    for f in injected_files:
        if f.suffix not in (".ts", ".tsx", ".js", ".jsx", ".mjs"):
            continue
        content = f.read_text(errors="replace")

        # Check for default export
        m = _WEB_DEFAULT_EXPORT_RE.search(content)
        if m:
            name = m.group(1) or ""
            return ("default", name, f)

        # Check for named entry functions
        m = _WEB_NAMED_ENTRY_RE.search(content)
        if m:
            return ("named", m.group(1), f)

        # Check for exported class
        m = _WEB_CLASS_EXPORT_RE.search(content)
        if m:
            return ("class", m.group(1), f)

    return None


def _compute_web_import_path(workspace: Path, target_file: Path) -> str:
    """Compute the relative import path from src/main.ts to the injected file.

    E.g., if target is at workspace/src/generated/anchorView.ts,
    returns "./generated/anchorView" (without extension).
    """
    src_dir = workspace / "src"
    try:
        rel = target_file.relative_to(src_dir)
    except ValueError:
        # Fallback: relative to workspace
        rel = target_file.relative_to(workspace)
    # Remove extension for import
    import_path = "./" + str(rel.with_suffix("")).replace("\\", "/")
    return import_path


def _generate_entry_bridge_web(workspace: Path, entry_type: str, entry_name: str, entry_file: Path) -> None:
    """Patch main.ts to import and mount the injected module in non-auto-run mode."""
    main_ts_path = workspace / "src" / "main.ts"
    if not main_ts_path.exists():
        return

    import_path = _compute_web_import_path(workspace, entry_file)

    if entry_type == "default":
        # Default export: import and call it (assume it's a function or class with mount/render)
        mount_logic = f'''\
    // Entry Bridge: load injected module (default export)
    const mod = await import("{import_path}");
    const entry = mod.default;
    if (typeof entry === "function") {{
      // Could be a class or a function — try calling it
      const result = entry(root);
      if (result && typeof result.then === "function") await result;
    }}'''
    elif entry_type == "named":
        # Named entry function (mount/render/init/etc.)
        mount_logic = f'''\
    // Entry Bridge: load injected module (named export: {entry_name})
    const mod = await import("{import_path}");
    if (typeof mod.{entry_name} === "function") {{
      const result = mod.{entry_name}(root);
      if (result && typeof result.then === "function") await result;
    }}'''
    else:
        # Class export (e.g., AnchorView)
        mount_logic = f'''\
    // Entry Bridge: load injected module (class export: {entry_name})
    const mod = await import("{import_path}");
    const instance = new mod.{entry_name}(root);
    if (typeof instance.mount === "function") {{
      const result = instance.mount();
      if (result && typeof result.then === "function") await result;
    }} else if (typeof instance.render === "function") {{
      const result = instance.render();
      if (result && typeof result.then === "function") await result;
    }}'''

    bridge_code = f'''\
import {{ loadEnv }} from "./env";
import {{ runAutoFlow }} from "./autorun/autoRunCoordinator";

async function bootstrap(): Promise<void> {{
  const env = loadEnv();

  // Expose env globally for injected code to use
  (globalThis as unknown as {{ __trtcEnv: typeof env }}).__trtcEnv = env;

  if (env.autoRunFlow) {{
    await runAutoFlow(env.autoRunFlow);
    return;
  }}

  // Entry Bridge mode: load and mount injected module
  const root = document.getElementById("app");
  if (root) {{
{mount_logic}
  }}
}}

bootstrap().catch((err) => {{
  console.error("[MyApplication] bootstrap failed:", err);
}});
'''
    main_ts_path.write_text(bridge_code)


# ---------------------------------------------------------------------------
# Platform dispatcher
# ---------------------------------------------------------------------------

def _apply_entry_bridge(workspace: Path, injected_dst_files: list[Path], platform: str) -> None:
    """Apply entry bridge generation based on platform.

    Rule: "Injected code must be reachable from the application entry point."

    Supports: ios, android, web.
    """
    if platform == "ios":
        result = _extract_entry_viewcontroller(injected_dst_files)
        if result:
            entry_vc_class, init_call = result
            _generate_entry_bridge_ios(workspace, entry_vc_class, init_call)

    elif platform == "android":
        result = _extract_entry_android(injected_dst_files)
        if result:
            entry_type, entry_class = result
            entry_package = _detect_android_package(injected_dst_files)
            _generate_entry_bridge_android(workspace, entry_type, entry_class, entry_package)

    elif platform == "web":
        result = _extract_entry_web(injected_dst_files)
        if result:
            entry_type, entry_name, entry_file = result
            _generate_entry_bridge_web(workspace, entry_type, entry_name, entry_file)


# ---------------------------------------------------------------------------
# Main injection logic
# ---------------------------------------------------------------------------

def inject(workspace: Path, ai_code_dir: Path, injection_map: dict, platform: str = "ios") -> None:
    """Inject AI-generated code into workspace.

    injection_map: dict mapping ai_filename -> InjectionPoint model or dict with target_file.
    Targets not yet in INJECTION.json will be auto-registered before injection.

    After injection, an entry bridge is generated to ensure the injected code is loaded
    at application startup (required for dynamic evaluation).
    """
    # Auto-supplement injection points declared by the test case
    _ensure_injection_points(workspace, injection_map)

    cfg = _load_injection_config(workspace)
    allowed = _allowed_targets(cfg)

    injected_dst_files: list[Path] = []
    for ai_file, point in injection_map.items():
        # Support both InjectionPoint model and raw dict
        target_rel = point.target_file if hasattr(point, "target_file") else point.get("target_file", "")
        if target_rel not in allowed:
            raise InjectError(f"target '{target_rel}' not in INJECTION.json.injection_points")
        src = ai_code_dir / ai_file
        if not src.exists():
            raise InjectError(f"AI did not produce expected file: {ai_file}")
        dst = workspace / target_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        injected_dst_files.append(dst)

    # Entry Bridge: ensure injected code is loaded at app startup
    _apply_entry_bridge(workspace, injected_dst_files, platform)

    _record_diff(workspace)


def _record_diff(workspace: Path) -> None:
    """Record git diff for audit."""
    meta = workspace / ".eval-meta"
    meta.mkdir(exist_ok=True)
    out = subprocess.run(
        ["git", "-C", str(workspace), "diff", "--stat", "."],
        capture_output=True, text=True, check=False,
    )
    (meta / "injection_diff.txt").write_text(
        out.stdout if out.returncode == 0 else "[git diff unavailable]\n"
    )
