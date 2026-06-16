#!/usr/bin/env node

"use strict";

/**
 * @tencent-rtc/trtc-agent-skills installer
 *
 * Installs the TRTC AI Integration skill suite (6 cross-referencing skills:
 * trtc + trtc-onboarding/docs/topic/search/apply) plus the shared
 * knowledge-base into your IDE's skills directory, and wires up the
 * `tencent-rtc-skill-tool` MCP server (used for prompt / runtime telemetry).
 *
 * IMPORTANT — why skills are copied as SIBLING DIRECTORIES:
 *   The entry skill `trtc/SKILL.md` routes to the others via relative paths
 *   like `../trtc-onboarding/SKILL.md`. They MUST remain siblings under the
 *   same skills root, otherwise routing breaks. We therefore copy each
 *   skills/<name>/ dir verbatim — we never concatenate them.
 *
 * Usage:
 *   npx @tencent-rtc/trtc-agent-skills add
 *   npx @tencent-rtc/trtc-agent-skills add --ide cursor
 *   npx @tencent-rtc/trtc-agent-skills add --ide all
 *   npx @tencent-rtc/trtc-agent-skills add --clean
 *   npx @tencent-rtc/trtc-agent-skills add --no-report
 *   npx @tencent-rtc/trtc-agent-skills add --list
 *   npx @tencent-rtc/trtc-agent-skills add --help
 */

const fs   = require("fs");
const os   = require("os");
const path = require("path");

// ── tiny color helpers (no deps) ───────────────────────────────────────────────
const useColor = process.stdout.isTTY && !process.env.NO_COLOR;
const c = {
  bold:   (s) => (useColor ? `\x1b[1m${s}\x1b[0m`  : s),
  cyan:   (s) => (useColor ? `\x1b[36m${s}\x1b[0m` : s),
  green:  (s) => (useColor ? `\x1b[32m${s}\x1b[0m` : s),
  yellow: (s) => (useColor ? `\x1b[33m${s}\x1b[0m` : s),
  red:    (s) => (useColor ? `\x1b[31m${s}\x1b[0m` : s),
  gray:   (s) => (useColor ? `\x1b[90m${s}\x1b[0m` : s),
  dim:    (s) => (useColor ? `\x1b[2m${s}\x1b[0m`  : s),
};

// ── paths ───────────────────────────────────────────────────────────────────────
const PKG_ROOT    = path.resolve(__dirname, "..");
const PKG_JSON    = require(path.join(PKG_ROOT, "package.json"));
const PKG_VERSION = PKG_JSON.version || "0.0.0";
const SKILLS_SRC  = path.join(PKG_ROOT, "skills");
const KB_SRC      = path.join(PKG_ROOT, "knowledge-base");

// The 6 skills that make up the suite. Order is cosmetic; `trtc` is the entry.
const SKILL_NAMES = [
  "trtc",
  "trtc-onboarding",
  "trtc-docs",
  "trtc-topic",
  "trtc-search",
  "trtc-apply",
];

// IDE skill-install targets (project-level). Each IDE reads skills from a
// different directory, but the layout inside is identical: one dir per skill.
const IDE_TARGETS = {
  claude:    { skillsRoot: ".claude/skills",    kind: "dir" },
  cursor:    { skillsRoot: ".cursor/skills",    kind: "dir" },
  codebuddy: { skillsRoot: ".codebuddy/skills", kind: "dir" },
  // Codex reads project-root .agents/skills/. Same dir-per-skill layout works.
  codex:     { skillsRoot: ".agents/skills",    kind: "dir" },
};

// MCP config locations per IDE.
//   claude:    project-level <root>/.mcp.json (JSON)
//   cursor:    user-level ~/.cursor/mcp.json (JSON)
//   codebuddy: user-level ~/.codebuddy/mcp.json (JSON)
//   codex:     user-level ~/.codex/config.toml (TOML, [mcp_servers.xxx])
const MCP_TARGETS = {
  claude:    { configFile: ".mcp.json",                                       format: "json" },
  cursor:    { configFile: path.join(os.homedir(), ".cursor",    "mcp.json"),    format: "json" },
  codebuddy: { configFile: path.join(os.homedir(), ".codebuddy", "mcp.json"),    format: "json" },
  codex:     { configFile: path.join(os.homedir(), ".codex", "config.toml"),     format: "toml" },
};

const MCP_SERVER_NAME  = "tencent-rtc-skill-tool";
const MCP_SERVER_ENTRY = "@tencent-rtc/skill-tool@latest";

// Knowledge-base lives next to the skills root (sibling), because skills
// reference it via ${CLAUDE_PLUGIN_ROOT}/knowledge-base — we mirror that by
// placing knowledge-base/ as a sibling of the skills dir's parent. To keep it
// simple and robust across IDEs, we copy KB into <skillsRoot>/../knowledge-base
// AND keep a project-root copy. See copyKnowledgeBase().

// ── fs helpers ──────────────────────────────────────────────────────────────────
function ensureDir(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function copyRecursive(src, dest) {
  const stat = fs.statSync(src);
  if (stat.isDirectory()) {
    ensureDir(dest);
    for (const entry of fs.readdirSync(src)) {
      copyRecursive(path.join(src, entry), path.join(dest, entry));
    }
  } else {
    ensureDir(path.dirname(dest));
    fs.copyFileSync(src, dest);
  }
}

function rmrf(target) {
  if (fs.existsSync(target) || isSymlink(target)) {
    fs.rmSync(target, { recursive: true, force: true });
  }
}

function isSymlink(p) {
  try { return fs.lstatSync(p).isSymbolicLink(); }
  catch { return false; }
}

// ── project root resolution ───────────────────────────────────────────────────
// Walk UP from cwd for strong repo-root signals (P1 monorepo manifest,
// P2 package.json workspaces, P3 .git). Otherwise P4 cwd-local package.json,
// else P5 cwd. Same semantics as the reference installer.
function findProjectRoot(startCwd) {
  const start = path.resolve(startCwd);
  let dir = start;
  while (true) {
    if (
      fs.existsSync(path.join(dir, "pnpm-workspace.yaml")) ||
      fs.existsSync(path.join(dir, "lerna.json")) ||
      fs.existsSync(path.join(dir, "turbo.json"))
    ) return dir;

    const pkgPath = path.join(dir, "package.json");
    if (fs.existsSync(pkgPath)) {
      try {
        const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));
        if (pkg && pkg.workspaces) return dir;
      } catch { /* malformed — keep walking */ }
    }

    if (fs.existsSync(path.join(dir, ".git"))) return dir;

    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  if (fs.existsSync(path.join(start, "package.json"))) return start;
  return start;
}

// ── argv parsing ──────────────────────────────────────────────────────────────
function getFlag(args, name) {
  const i = args.indexOf(name);
  return i !== -1 ? args[i + 1] : undefined;
}

// ── help / list ───────────────────────────────────────────────────────────────
function printHelp() {
  console.log(`
  ${c.bold("@tencent-rtc/trtc-agent-skills")} — Install TRTC AI Integration skills + MCP

  ${c.bold("Usage:")}
    ${c.cyan("npx @tencent-rtc/trtc-agent-skills add")}                  Install (default IDE: claude)
    ${c.cyan("npx @tencent-rtc/trtc-agent-skills add --ide <name>")}     One of: claude / cursor / codebuddy / codex / all
    ${c.cyan("npx @tencent-rtc/trtc-agent-skills add --clean")}          Wipe existing trtc* skill dirs first
    ${c.cyan("npx @tencent-rtc/trtc-agent-skills add --no-report")}      Skip anonymous install reporting
    ${c.cyan("npx @tencent-rtc/trtc-agent-skills add --list")}           List skills shipped in this package
    ${c.cyan("npx @tencent-rtc/trtc-agent-skills add --help")}           Show this help

  ${c.bold("Installs:")}
    ${c.dim("Skills :")} ${c.gray("<projectRoot>/.claude/skills/  (or .cursor/, .codebuddy/, .agents/)")}
    ${c.dim("KB     :")} ${c.gray("alongside the skills root as knowledge-base/")}
    ${c.dim("MCP    :")} ${c.gray("tencent-rtc-skill-tool → IDE mcp config (npx @tencent-rtc/skill-tool@latest)")}

  ${c.dim("Skills are copied as sibling dirs so relative routing (../trtc-onboarding) keeps working.")}
`);
}

function listSkills() {
  console.log(`\n  ${c.bold("Skills shipped in this package:")}\n`);
  console.log(`  ${c.cyan("trtc/")}            ${c.dim("Entry router — detects product/platform, routes to sub-skills")}`);
  console.log(`  ${c.cyan("trtc-onboarding/")} ${c.dim("Get-started / integration / troubleshooting flow")}`);
  console.log(`  ${c.cyan("trtc-docs/")}       ${c.dim("Docs & error-code lookup")}`);
  console.log(`  ${c.cyan("trtc-topic/")}      ${c.dim("Step-by-step scenario walkthrough")}`);
  console.log(`  ${c.cyan("trtc-search/")}     ${c.dim("Internal slice lookup (AI-facing)")}`);
  console.log(`  ${c.cyan("trtc-apply/")}      ${c.dim("Internal compile/integration quality gate")}`);
  console.log("");
}

// ── core: skill install ─────────────────────────────────────────────────────────
function cleanSkills(skillsRootAbs) {
  if (!fs.existsSync(skillsRootAbs)) return 0;
  let wiped = 0;
  for (const name of SKILL_NAMES) {
    const target = path.join(skillsRootAbs, name);
    if (fs.existsSync(target)) { rmrf(target); wiped++; }
  }
  // also wipe a co-located knowledge-base copy if present
  const kb = path.join(path.dirname(skillsRootAbs), "knowledge-base");
  if (fs.existsSync(kb)) { rmrf(kb); }
  return wiped;
}

function installSkills(skillsRootAbs) {
  ensureDir(skillsRootAbs);
  for (const name of SKILL_NAMES) {
    const src = path.join(SKILLS_SRC, name);
    if (fs.existsSync(src)) {
      copyRecursive(src, path.join(skillsRootAbs, name));
    }
  }
}

// Copy knowledge-base so that skills can resolve it. Skills use
// ${CLAUDE_PLUGIN_ROOT}/knowledge-base; the practical robust choice is to put
// knowledge-base as a sibling of the skills root (e.g. .claude/knowledge-base),
// which is what plugin-style roots expect.
function copyKnowledgeBase(skillsRootAbs) {
  const dest = path.join(path.dirname(skillsRootAbs), "knowledge-base");
  rmrf(dest);
  copyRecursive(KB_SRC, dest);
  return dest;
}

// ── MCP installation ──────────────────────────────────────────────────────────
function installMcp(ideList, resolvedRoot) {
  const serverEntry = {
    type: "stdio",
    command: "npx",
    args: ["-y", MCP_SERVER_ENTRY],
  };

  for (const ide of ideList) {
    const mcpTarget = MCP_TARGETS[ide];
    if (!mcpTarget) continue;

    const configPath = path.isAbsolute(mcpTarget.configFile)
      ? mcpTarget.configFile
      : path.join(resolvedRoot, mcpTarget.configFile);
    ensureDir(path.dirname(configPath));

    if (mcpTarget.format === "toml") {
      installMcpToml(configPath, serverEntry);
    } else {
      let config = {};
      if (fs.existsSync(configPath)) {
        try { config = JSON.parse(fs.readFileSync(configPath, "utf8")); }
        catch { config = {}; }
      }
      if (!config.mcpServers || typeof config.mcpServers !== "object") {
        config.mcpServers = {};
      }
      config.mcpServers[MCP_SERVER_NAME] = serverEntry;
      fs.writeFileSync(configPath, JSON.stringify(config, null, 2) + "\n", "utf8");
    }
    console.log(c.green("    ✓ ") + `${ide} MCP → ${configPath}`);
  }
}

function installMcpToml(configPath, serverEntry) {
  let content = fs.existsSync(configPath) ? fs.readFileSync(configPath, "utf8") : "";

  const sectionHeader = `[mcp_servers.${MCP_SERVER_NAME}]`;
  const argsValue = JSON.stringify(serverEntry.args).replace(/,/g, ", ");
  const newSection = [
    sectionHeader,
    `command = "${serverEntry.command}"`,
    `args = ${argsValue}`,
  ].join("\n") + "\n";

  const escapedName = MCP_SERVER_NAME.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const sectionRegex = new RegExp(
    `\\[mcp_servers\\.${escapedName}\\]\\n(?:(?!\\[)[^\\n]*\\n)*`,
    "g"
  );
  content = content.replace(sectionRegex, "");
  content = content.trimEnd() + (content.trim() ? "\n\n" : "") + newSection;
  fs.writeFileSync(configPath, content, "utf8");
}

// ── Claude Code permissions (pre-approve MCP tool) ──────────────────────────────
function installClaudePermissions(ideList, resolvedRoot) {
  if (!ideList.includes("claude")) return;

  const settingsDir  = path.join(resolvedRoot, ".claude");
  const settingsPath = path.join(settingsDir, "settings.json");
  ensureDir(settingsDir);

  let settings = {};
  if (fs.existsSync(settingsPath)) {
    try { settings = JSON.parse(fs.readFileSync(settingsPath, "utf8")); }
    catch { settings = {}; }
  }
  if (!settings.permissions || typeof settings.permissions !== "object") settings.permissions = {};
  if (!Array.isArray(settings.permissions.allow)) settings.permissions.allow = [];

  const rules = [`mcp__${MCP_SERVER_NAME}__*`];
  const added = rules.filter(r => !settings.permissions.allow.includes(r));
  if (added.length > 0) {
    settings.permissions.allow.push(...added);
    fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2) + "\n", "utf8");
    console.log(c.green("    ✓ ") + `claude permissions → ${settingsPath}`);
  } else {
    console.log(c.dim(`    ✓ claude permissions already set, skipped`));
  }
}

// ── Cursor permissions (allowlist MCP tool) ─────────────────────────────────────
function installCursorPermissions(ideList, resolvedRoot) {
  if (!ideList.includes("cursor")) return;

  const permDir  = path.join(resolvedRoot, ".cursor");
  const permPath = path.join(permDir, "permissions.json");
  ensureDir(permDir);

  let perms = {};
  if (fs.existsSync(permPath)) {
    try { perms = JSON.parse(fs.readFileSync(permPath, "utf8")); }
    catch { perms = {}; }
  }
  if (!Array.isArray(perms.mcpAllowlist)) perms.mcpAllowlist = [];

  const rule = `${MCP_SERVER_NAME}:skill_analysis`;
  if (!perms.mcpAllowlist.includes(rule)) {
    perms.mcpAllowlist.push(rule);
    fs.writeFileSync(permPath, JSON.stringify(perms, null, 2) + "\n", "utf8");
    console.log(c.green("    ✓ ") + `cursor permissions → ${permPath}`);
  } else {
    console.log(c.dim(`    ✓ cursor permissions already set, skipped`));
  }
}

// ── install reporting (fire-and-forget) ─────────────────────────────────────────
// Spawns the MCP server with --report. All reporting details (endpoint, etc.)
// live inside the MCP server; install.js only passes context fields.
function reportInstall({ ide }) {
  const payload = JSON.stringify({
    method: 2,                 // 2 = trtc-agent-skills install (1=chat-web-skill, 2=trtc-agent-skills)
    version: PKG_VERSION,
    framework: "all",
    ide,
    os: os.platform(),
  });

  try {
    const { spawn } = require("child_process");
    const child = spawn("npx", ["-y", MCP_SERVER_ENTRY, "--report", payload], {
      detached: true,
      stdio: "ignore",
    });
    child.unref();
  } catch {
    // never block install on reporting failure
  }
}

// ── main ──────────────────────────────────────────────────────────────────────
function main() {
  const args = process.argv.slice(2);
  const cmd  = args[0];

  if (!cmd || cmd === "--help" || cmd === "-h") { printHelp(); process.exit(0); }
  if (cmd === "--list" || cmd === "-l")          { listSkills(); process.exit(0); }
  if (cmd !== "add") {
    console.error(c.red(`\n  Unknown command: ${cmd}`));
    printHelp();
    process.exit(1);
  }
  if (args.includes("--list")) { listSkills(); process.exit(0); }

  const isClean   = args.includes("--clean");
  const noReport  = args.includes("--no-report");
  const ideArg    = getFlag(args, "--ide") || "claude";

  const ideList = ideArg === "all" ? Object.keys(IDE_TARGETS) : [ideArg];
  for (const ide of ideList) {
    if (!IDE_TARGETS[ide]) {
      console.error(c.red(`\n  ✗ Unknown IDE: ${ide}. Valid: ${Object.keys(IDE_TARGETS).join(", ")}, all\n`));
      process.exit(1);
    }
  }

  const cwd = process.cwd();
  let resolvedRoot = findProjectRoot(cwd);
  // Guard: don't install into the package's own tree during local dev.
  if (resolvedRoot === PKG_ROOT) resolvedRoot = cwd;

  console.log(`\n  ${c.bold(c.cyan("@tencent-rtc/trtc-agent-skills"))}  ${c.dim("v" + PKG_VERSION)}`);
  console.log(`  ${c.gray("cwd         : " + cwd)}`);
  console.log(`  ${c.gray("projectRoot : " + resolvedRoot)}`);
  console.log(`  ${c.gray("IDE(s)      : " + ideList.join(", "))}`);
  console.log("");

  // 1. Install skill dirs (+ co-located knowledge-base) for each IDE.
  for (const ide of ideList) {
    const target = IDE_TARGETS[ide];
    const skillsRootAbs = path.join(resolvedRoot, target.skillsRoot);
    console.log(`  ${c.bold(ide)}  ${c.gray("→ " + skillsRootAbs + "/")}`);

    if (isClean) {
      const wiped = cleanSkills(skillsRootAbs);
      if (wiped > 0) console.log(c.dim(`    ✓ cleaned ${wiped} existing skill ${wiped === 1 ? "entry" : "entries"}`));
    }

    installSkills(skillsRootAbs);
    for (const name of SKILL_NAMES) console.log(c.green("    ✓ ") + name + "/");

    const kbDest = copyKnowledgeBase(skillsRootAbs);
    console.log(c.green("    ✓ ") + "knowledge-base/ " + c.dim("→ " + kbDest));
  }

  // 2. Install MCP server config + permissions.
  console.log(`\n  ${c.bold("MCP")}`);
  installMcp(ideList, resolvedRoot);
  installClaudePermissions(ideList, resolvedRoot);
  installCursorPermissions(ideList, resolvedRoot);

  // 3. Anonymous install reporting (fire-and-forget; opt out via --no-report).
  if (!noReport) reportInstall({ ide: ideArg });

  // 4. Done.
  console.log(`\n  ${c.bold("Done.")} ${c.dim("Just describe what you want to build in your IDE — the skill activates automatically.")}\n`);
}

try {
  main();
} catch (err) {
  console.error(c.red(`\n  Error: ${err.message || err}\n`));
  if (err.stack && process.env.DEBUG) console.error(c.dim(err.stack) + "\n");
  process.exit(1);
}
