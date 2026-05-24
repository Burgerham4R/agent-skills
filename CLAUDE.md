# TRTC AI Integration 知识库

本项目是 TRTC（Tencent Real-Time Communication）的 AI 辅助集成知识库，通过 Plugin 模式分发，支持 Claude Code / Cursor / Codex / CodeBuddy 一键安装。

## 分发模式

本项目是标准 **Plugin** 格式，用户无需 clone 仓库即可使用。

```bash
# 用户安装（GitHub 发布后）
/plugin marketplace add tencent-trtc/trtc-ai-integration
/plugin install trtc-ai-setup
```

- Skills 路径引用使用 `${CLAUDE_PLUGIN_ROOT}/knowledge-base/...`
- Hooks 通过 `hooks/hooks.json` 分发（路径使用 `${CLAUDE_PLUGIN_ROOT}`）
- `.claude/skills/trtc-eval/` 为维护者专属，不随 plugin 分发

## 项目结构

```
ai-integration/
├── 🔵 .claude-plugin/plugin.json         # Claude Code plugin 入口
├── 🔵 .cursor-plugin/plugin.json         # Cursor plugin 入口
├── 🔵 .codex-plugin/plugin.json          # Codex plugin 入口
├── 🔵 .codebuddy-plugin/plugin.json      # CodeBuddy plugin 入口
├── 🔵 hooks/hooks.json                   # Plugin hooks（路径使用 ${CLAUDE_PLUGIN_ROOT}）
├── 🔵 skills/                            # Plugin Skills（用户安装后自动加载）
│   ├── trtc/SKILL.md                     #   路由入口 — 识别产品/平台，分发到子 skill
│   ├── trtc-onboarding/SKILL.md          #   新手引导 — Demo 运行 / 集成教程 / 排障 / 扩展
│   ├── trtc-search/SKILL.md              #   智能搜索 — 7 策略匹配 + 4 级 Fallback
│   ├── trtc-apply/SKILL.md               #   代码生成与校验 — 生成生产级代码 + 自我校验
│   ├── trtc-docs/SKILL.md                #   文档问答（定价/配额/错误码等事实性问题）
│   ├── trtc-topic/SKILL.md               #   场景引导 — Checkpoint 式分步教程
│   │   └── guardrails/                   #   hook 调 (用户机器必须有)
│   │       ├── gate_slice_read.py        #     PreToolUse: 阅读门控
│   │       ├── gate_slice_write.py       #     PreToolUse: 写入门控
│   │       └── stop_require_apply_evidence.py  # Stop: 校验证据
│   └── trtc/room-builder/               #   UI 模板与主题资产
│       ├── references/                   #     scenarios.yaml (单一数据源) + 渲染产物
│       ├── uikit/assets/themes/          #     主题资产 (meeting-classic 等)
│       ├── 🔘 MAINTAINING-SCENARIOS.md   #     维护者文档（如何加新场景/主题）
│       ├── 🔵 guardrails/               #     hook 调 (用户机器必须有)
│       │   ├── trtc_prepare_ui.py        #       SessionStart: 资产准备
│       │   ├── trtc_verify_ui.py         #       Stop / PostToolUse: 资产校验
│       │   ├── verify_ui_post_write.sh   #       PostToolUse 胶水
│       │   └── lib/{session_state,theme_registry}.py
│       └── 🔘 tools/                    #     维护者跑 (用户不调)
│           ├── render_ai_instructions.py #       ai-instructions/ → CLAUDE.md / AGENTS.md / .cursor/rules/
│           └── render_scenario_mapping.py#       scenarios.yaml → scenario-mapping.md
│
├── 🔵 CLAUDE.md                          # 本文件 — 项目级 AI 指令
├── 🔵 AGENTS.md                          # ⊙ 由 ai-instructions/ 渲染生成
│                                         #   OpenAI Codex CLI / Aider / Cline / CodeBuddy 自动读取
├── 🔵 CODEBUDDY.md                       # CodeBuddy 兼容入口
│
├── 🔵 knowledge-base/                    # 结构化知识层 (search/apply 读)
│   ├── index.yaml                        #   全量索引（v4.0 — products/slices/scenarios/cross_product_relations）
│   ├── slice-spec.md                     #   Slice 定义规范（拆分标准、编写规范、规划方法论）
│   ├── slices/                           #   原子能力片段（按产品 → 平台组织）
│   └── scenarios/                        #   场景组合（多 Slice 串联的完整流程）
│
├── 🔵 llms.txt + llms/                   # llms.txt 标准模板（供外部 LLM 发现文档）
│   ├── {product}.txt                     #   产品概述 + 平台链接（如 live.txt, conference.txt）
│   └── {product}/{platform}.txt          #   平台概述 + 官方文档链接（如 live/ios.txt, conference/web.txt）
│
├── 🔘 ai-instructions/                   # 工具无关的指令源（用户拿派生产物，不读源）
│   └── ui-mode.md                        #   渲染到 CLAUDE.md / AGENTS.md / .cursor/rules/
│
├── 🔘 tests/                             # 单元测试 (pytest, 仅维护者跑)
├── 🔘 bootstrap.sh                       # 维护者一键安装 + 渲染派生
└── 🔵 .claude/skills/trtc-eval/          # 评测工具 skill（独立体系，不随 plugin 分发）
```

**分发规则**：插件市场打包 / 命令行安装时只下发 🔵 标记的部分。🔘 标记的（顶层 `tests/`、`ai-instructions/`、`bootstrap.sh`，以及 skill 内的 `room-builder/tools/`、`room-builder/MAINTAINING-SCENARIOS.md`）即使物理路径在 skill 树下也只供维护者使用，用户不会调用，不暴露入口。

## 核心概念

### Slice（原子能力片段）
一个 slice 对应一个原子能力（如「进房」「推流」「多实例登录」）。每个 slice 包含：
- **产品级概览**：功能说明、核心概念、最佳实践、排障指南（跨平台通用）
- **平台实现细节**：具体 API 调用、代码示例、平台特有注意事项

Slice 分为两层：
- **🅰️ 主线 Slice (baseline)**：按 SDK 能力域系统规划，保证核心功能覆盖
- **🅱️ 反馈 Slice (feedback)**：从用户高频问题中提炼，补充真实的坑和边缘场景

> 详细规范见 `knowledge-base/slice-spec.md`

### Scenario（场景组合）
一个 scenario 是完整的使用场景，引用多个 slice 并定义执行顺序。

### llms.txt（LLM 文档发现）
遵循 [llms.txt 标准](https://llmstxt.org/) 的渐进式文档披露系统，供外部 LLM（ChatGPT、Claude 等）发现和加载 TRTC 文档。

**三级结构**：`llms.txt`（产品索引）→ `{product}.txt`（产品概述 + 平台链接）→ `{product}/{platform}.txt`（平台概述 + 官方文档链接）

**定位**：仓库中的文件是**内容规范和初始模板**，最终由 trtc.io 文档站构建流程自动生成并部署到 CDN。文档站团队根据此模板编写生成脚本，从文档源（MDX/Markdown）自动产出 llms.txt 系列文件，确保文档更新时自动同步。

**与 knowledge-base 的关系**：
- `knowledge-base/`（slices + scenarios）= 面向内部 AI Skills 的结构化知识库，包含详细的代码示例、排障指南
- `llms/` = 面向外部 LLM 的轻量索引，仅包含概述和指向 trtc.io 官方文档的链接

### 三层架构
```
Layer 3: Skills（用户交互层）— trtc / onboarding / search / apply / docs / topic
Layer 2: Knowledge Base（结构化知识层）— slices/ + scenarios/ + index.yaml
Layer 1: Plugin Runtime — skills/ (分发) + hooks/hooks.json + CLAUDE.md
```

## AI 行为指令

**语言**：根据用户输入语言回复，默认英文。知识库内容为中文，回复时翻译为用户语言。代码标识符、API 名称、错误码保持原样。

**新用户检测**：当用户首次使用或描述从零开始的集成需求时，优先进入 `onboarding/SKILL.md` 引导流程。

当用户提出 TRTC 相关问题时：
1. **识别产品**：Chat / Call / RTC Engine / Live / Conference
2. **识别平台**：Web / Android / iOS / Flutter / Electron
3. **读取知识库**：先读产品级概览，再读平台实现细节
4. **回答时引用来源**：标明参考的 slice ID 和官方文档链接

## TRTC 产品线

| 产品 | 目录 | 说明 |
|------|------|------|
| Chat | `slices/chat/` | 即时通信（消息、会话、群组） |
| Call | `slices/call/` | 音视频通话（1v1/群组通话） |
| RTC Engine | `slices/rtc-engine/` | 实时音视频引擎（进房/推流/拉流） |
| Live | `slices/live/` | 直播（推流/拉流/连麦） |
| Conference | `slices/conference/` | 视频会议（多人视频、在线教育、远程医疗） |

## 支持的平台

Web / Android / iOS / Flutter / Electron / Unity

<!-- AI-INSTRUCTIONS:BEGIN -->
<!-- DO NOT EDIT — generated from ai-instructions/ by skills/trtc/room-builder/tools/render_ai_instructions.py. Edit the source markdown and re-run the renderer instead. -->

## ui-mode

### When this rule applies

Only when `.trtc-session.yaml` at the repo root has `ui_mode: official-roomkit`
or `ui_mode: full-ui`. If the file is missing, or `ui_mode` is unset / null /
`headless`, this rule does not apply — fall back to whatever the tool's default
behavior is.

### Medical new-project shortcut

When the user request is for medical online consultation (for example
`1v1-video-consultation`, remote diagnosis, online medical consultation,
doctor-patient video visit) **and** the task is to generate a brand-new
project rather than integrate into an existing app, bypass the normal full-ui
theme workflow entirely. Do not run `trtc_prepare_ui.py`, do not generate Vue
SFCs by hand, and do not run UI or medical verifiers.

Instead, directly copy the bundled medical template project:

```bash
skills/trtc/room-builder/templates/scenarios/medical-consultation/
```

to the user's local target project directory, preserving the project exactly
as packaged. In the handoff or integration notes, tell the customer to use
`pnpm install` for dependencies and `pnpm dev` for local development. Do not
recommend `npm install` / `npm run dev`; this medical template starts much
slower with npm and can show a blank first screen for a while.

This shortcut applies only to brand-new medical consultation projects. Existing
project integration still follows the normal scenario / official-roomkit /
full-ui rules below.

### Official RoomKit integration mode

When the customer asks to **integrate a conference / meeting into an existing
Vue 3 app** (for example "集成会议", "接入会议", "add video meeting to my app",
"official RoomKit", "TUIRoomKit") and does not explicitly ask for a fully
custom rebuilt meeting UI, use the official RoomKit integration path instead
of the meeting-classic full-ui theme workflow.

In this mode:

1. Integrate the official Web RoomKit package. For UI customization APIs,
   verify that the resolved `@tencentcloud/roomkit-web-vue3` version is
   `>=5.4.3` (installing `@tencentcloud/roomkit-web-vue3@5` is acceptable only
   when the lockfile resolves to at least `5.4.3`), plus its documented peer
   packages `tuikit-atomicx-vue3`,
   `@tencentcloud/uikit-base-component-vue3`, and
   `@tencentcloud/universal-api`.
2. Render the official components (`ConferenceMainView` for PC and
   `ConferenceMainViewH5` for H5) inside `UIKitProvider`（从
   `@tencentcloud/uikit-base-component-vue3` 导入）.
3. Use the official `conference` API for auth and room lifecycle:
   `conference.login()`, `conference.setSelfInfo()`,
   `conference.createAndJoinRoom()`, `conference.joinRoom()`,
   `conference.leaveRoom()`, `conference.endRoom()`, and `RoomEvent`
   listeners as appropriate for the customer's flow.
4. For UserSig, reuse the existing MCP / local-signing / backend-issued
   credential flow. Do not generate `src/utils/usersig.ts`, do not expose
   `SecretKey` in client code, and do not use `crypto-js`, `pako`,
   `HmacSHA256`, or `tls-sig-api-v2` to sign UserSig in browser code.
5. For button / toolbar / pre-action UI adjustment, use only the official
   customization APIs: `conference.setWidgetVisible()`,
   `conference.registerWidget()`, and `conference.onWill()`.
6. Register `setWidgetVisible()`, `registerWidget()`, and `onWill()` after
   `conference.login()` and before `conference.createAndJoinRoom()` /
   `conference.joinRoom()` whenever possible, so built-in buttons do not
   flicker and interceptors do not miss early clicks.
7. Use `conference.setFeatureConfig()` only for the feature configuration it
   documents. In particular, configure `shareLink` immediately after
   `conference.createAndJoinRoom()` / `conference.joinRoom()` succeeds, so
   the final `roomId` is known.
8. Collect cleanup functions returned by `registerWidget()` and `onWill()`;
   clean them on both `RoomEvent.ROOM_LEAVE` and `RoomEvent.ROOM_DISMISS`.

Do **not** run `trtc_prepare_ui.py`, copy `src/themes/meeting-classic/`,
generate `ui-*` based meeting Vue SFCs, or run `trtc_verify_ui.py` for official
RoomKit integration mode. The acceptance check for this mode is that the app
uses the official package/components and official UI customization APIs, not
the local meeting-classic theme catalog.

### Mandatory workflow

Except for the two bypasses above, `ui_mode: full-ui` means the user has opted
into a styled meeting UI built on the meeting-classic uikit theme. Three things
must be true of the user project (`project_state.project_root` in the session
file):

1. `src/themes/meeting-classic/` is the full theme copy.
2. `src/main.ts` (or `main.js`) imports `'@/themes/meeting-classic/index.css'`.
3. `index.html` has `data-theme="mc"` on the `<html>` tag.

These are wired up by:

```bash
python3 skills/trtc/room-builder/guardrails/trtc_prepare_ui.py
```

The script is idempotent — safe to run at any time. **Run it before
generating any Vue SFC.** If it errors (missing project root etc.), surface
the error to the user; do not proceed with code generation against a
half-wired project.

### During SFC generation

Every interactive or visually distinct element in your generated `.vue`
templates must use a `ui-*` class drawn from the catalog at
`skills/trtc/room-builder/uikit/references/component-catalog.md`.

The minimum is enforced (per file ≥ 3 classes; project total ≥ 30) by:

```bash
python3 skills/trtc/room-builder/guardrails/trtc_verify_ui.py --file <path-to-vue>
```

If this exits 2, read the stderr — it names the file and the count, and
points at the catalog. Fix the file before continuing.

### Before declaring the task complete

Run the project-wide check:

```bash
python3 skills/trtc/room-builder/guardrails/trtc_verify_ui.py
```

Only declare done when this exits 0. The Stop / pre-commit hook will run
this anyway; declaring done before it passes wastes a turn.

### Forbidden shortcuts

- Do **not** write a placeholder `tokens.css` — `trtc_prepare_ui.py` copies
  the full theme. Re-run it instead of substituting.
- Do **not** invent `ui-*` class names. If `component-catalog.md` doesn't
  list a class for what you need, stop and tell the user — do not silently
  emit `ui-thing-i-made-up`.
- Do **not** generate "minimum viable UI now, full UI later." That defeats
  the entire `ui_mode: full-ui` distinction.
- Do **not** skip `trtc_prepare_ui.py` to "keep the diff small." The theme
  copy IS the diff for full-ui mode.

<!-- AI-INSTRUCTIONS:END -->
