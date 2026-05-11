# TRTC AI Integration Framework

帮助开发者通过 AI 快速集成和排障 [TRTC](https://trtc.io)（腾讯实时音视频）SDK。

本项目将 TRTC 的产品知识拆解为**原子能力片段（Slice）**，并通过 **Claude Code Skills**、**Cursor Rules** 和 **OpenAI Codex CLI (AGENTS.md)** 提供智能搜索、代码校验、场景引导和新手入门等交互能力，让开发者在对话中完成从零到上线的集成过程。

## 核心理念

```
用户提问 → Skill 路由 → 知识库检索 → 结构化回答 + 代码示例
```

传统文档是"被动阅读"，本框架是"主动交互"：
- **按需加载**：只返回用户当前需要的知识片段，不信息过载
- **代码生成与校验**：基于 Slice 知识生成生产级代码，并通过约束规则 + 编译验证自我校验
- **渐进引导**：通过场景（Scenario）按步骤引导完整功能集成
- **智能兜底**：7 层搜索策略 + 4 级 Fallback，确保用户总能得到有效回答

## 项目结构

> **图例**：🔵 = 对外（随 skill 分发到用户机器）；⚪ = 内部（仅维护者使用，不对外）

```
ai-integration/
├── 🔵 .claude/skills/trtc/                    # Claude Code Skills（分发体）
│   ├── SKILL.md                              #   路由入口 — 识别产品/平台，分发到子 skill
│   ├── onboarding/SKILL.md                   #   新手引导 — Demo 运行 / 集成教程 / 排障 / 扩展
│   ├── search/SKILL.md                       #   智能搜索 — 7 策略匹配 + 4 级 Fallback
│   ├── apply/SKILL.md                        #   代码生成与校验 — 生成生产级代码 + 自我校验
│   ├── topic/SKILL.md                        #   场景引导 — Checkpoint 式分步教程
│   └── room-builder/                         #   UI 模板与主题资产
│       ├── references/                       #     scenarios.yaml（单一数据源）+ 渲染产物
│       ├── uikit/assets/themes/              #     主题资产（meeting-classic 等）
│       ├── ⚪ MAINTAINING-SCENARIOS.md        #     维护者文档（如何加新场景/主题）
│       ├── 🔵 guardrails/                     #     hook 调（用户机器必须有）
│       │   ├── trtc_prepare_ui.py            #       SessionStart：资产准备
│       │   ├── trtc_verify_ui.py             #       Stop / PostToolUse：资产校验
│       │   ├── verify_ui_post_write.sh       #       PostToolUse 胶水
│       │   └── lib/{session_state,theme_registry}.py
│       └── ⚪ tools/                          #     维护者跑（用户不调）
│           ├── render_ai_instructions.py     #       ai-instructions/ → CLAUDE.md / AGENTS.md / .cursor/rules/
│           └── render_scenario_mapping.py    #       scenarios.yaml → scenario-mapping.md
│
├── 🔵 .claude/settings.json                   # Claude Code hooks 注册（SessionStart / PostToolUse / Stop）
│
├── 🔵 .cursor/rules/                          # Cursor Rules（Cursor IDE 适配层）
│   ├── trtc-router.mdc / trtc-onboarding.mdc / trtc-search.mdc / trtc-docs.mdc / trtc-topic.mdc / trtc-apply.mdc
│   └── ui-mode.mdc                           #   ⚙ 由 ai-instructions/ui-mode.md 渲染生成
│
├── 🔵 AGENTS.md                               # ⚙ 由 ai-instructions/ 渲染生成
│                                             #   OpenAI Codex CLI / Aider / Cline / CodeBuddy 自动读取
├── 🔵 CLAUDE.md / CODEBUDDY.md                # ⚙ 派生入口
│
├── 🔵 knowledge-base/                         # 结构化知识层（search/apply 读）
│   ├── index.yaml                            #   全量索引（产品/Slice/场景/跨产品关系）
│   ├── slice-spec.md                         #   Slice 编写规范
│   ├── slices/                               #   原子能力片段（按产品 → 平台组织）
│   └── scenarios/                            #   场景组合（多 Slice 串联的完整流程）
│
├── 🔵 llms.txt + llms/                        # llms.txt 标准模板（供外部 LLM 发现文档）
│
├── ⚪ ai-instructions/                        # 工具无关的指令源（用户拿派生产物，不读源）
│   └── ui-mode.md                            #   渲染到 CLAUDE.md / AGENTS.md / .cursor/rules/
│
├── ⚪ tests/unit/                             # 单元测试（pytest，仅维护者跑）
├── ⚪ bootstrap.sh                            # 维护者一键安装 + 渲染派生
└── 🔵 .claude/skills/trtc-eval/               # 评测工具 skill（独立体系）
```

**分发规则**：插件市场打包 / 命令行安装时只下发 🔵 标记的部分，⚪ 标记的（顶层 `tests/`、`ai-instructions/`、`bootstrap.sh`，以及 skill 内的 `room-builder/tools/`、`room-builder/MAINTAINING-SCENARIOS.md`）即便物理路径在 skill 树下也只供维护者使用，用户不会调用，不暴露入口。

## 核心概念

### Slice（原子能力片段）

一个 Slice 对应一个原子能力（如"登录认证"、"弹幕"、"美颜"），是知识库的最小单元。

每个 Slice 分两层：
- **产品级概览**（`slices/live/barrage.md`）— 跨平台通用的功能说明、核心概念、最佳实践、排障指南
- **平台实现细节**（`slices/live/ios/barrage.md`）— 具体 API 调用、代码示例、平台特有注意事项

Slice 有两类来源：
- **主线 Slice**：按 SDK 能力域系统规划，覆盖核心功能
- **反馈 Slice**：从用户高频问题中提炼，补充真实场景的坑和边缘情况

### Scenario（场景组合）

一个完整的使用场景，串联多个 Slice 并定义执行顺序。例如「秀场直播间」场景包含 15 个 Slice，从登录认证到连麦互动。

### ai-instructions（跨工具单一指令源）

`ai-instructions/*.md` 是**工具无关**的指令源文件，由 `.claude/skills/trtc/room-builder/tools/render_ai_instructions.py` 自动渲染到各工具的入口位置：

| 源文件 | 渲染目标 | 形态 |
|---|---|---|
| `ai-instructions/{name}.md` | `CLAUDE.md` 内 `<!-- AI-INSTRUCTIONS:BEGIN -->` 标记块 | 追加在人工编写内容之后；body 标题自动降级一级 |
| `ai-instructions/{name}.md` | `AGENTS.md` | 全量重新生成；每个源文件一个 `# {name}` 段落 |
| `ai-instructions/{name}.md` | `.cursor/rules/{name}.mdc` | 一对一渲染；自动加上 `alwaysApply: true` 前置 frontmatter |

**好处**：跨 Claude Code / Cursor / Codex / Aider / CodeBuddy 等工具共享一份指令，改一次同步全工具，避免多处漂移。

`bootstrap.sh` 跑完会自动执行渲染；CI 用 `python3 .claude/skills/trtc/room-builder/tools/render_ai_instructions.py --check` 检查源文件改动后是否忘记重新渲染。

### Hooks（Claude Code 强制约束）

部分契约靠 prompt 文字描述容易被模型跳过（典型例：`ui_mode=full-ui` 的资产准备 + uikit class 校验）。`.claude/settings.json` 里注册了三个 Claude Code hook，把软约束变成 harness 强制执行的硬约束：

| 时机 | 调用 | 作用 |
|---|---|---|
| `SessionStart` | `python3 .claude/skills/trtc/room-builder/guardrails/trtc_prepare_ui.py` | 会话启动时自动 cp theme + 改 `main.ts` + 改 `index.html`；幂等 |
| `PostToolUse(Write\|Edit)` | `bash .claude/skills/trtc/room-builder/guardrails/verify_ui_post_write.sh` | 每次写 `.vue` 后立即校验 `ui-*` class 数量；不达标 stderr 反馈给模型 |
| `Stop` | `python3 .claude/skills/trtc/room-builder/guardrails/trtc_verify_ui.py` | 模型声明完成前做项目级总闸校验 |

> 同样的 `trtc_verify_ui.py` 也可以被 git pre-commit hook 调，作为跨工具的最后一道防线。

## TRTC 产品矩阵

| 产品 | 说明 | 当前状态 |
|------|------|---------|
| **Live** | 直播（推流/拉流/连麦/弹幕/礼物/美颜） | ✅ iOS 平台 15 个 Slice 已完成 |
| **Chat** | 即时通信（消息/会话/群组） | 📋 规划中 |
| **Call** | 音视频通话（1v1/群组） | 📋 规划中 |
| **RTC Engine** | 实时音视频引擎（进房/推流/拉流） | 📋 规划中 |
| **Room** | 房间管理（创建/销毁/成员管理） | 📋 规划中 |

**支持平台**：Web / Android / iOS / Flutter / Electron / Unity

## Skills 功能说明

### 路由（SKILL.md）

入口 Skill，识别用户意图中的产品和平台，分发到对应的子 Skill。

### 新手引导（onboarding）

为首次接触 TRTC 的开发者提供四条路径：
- **跑通 Demo**：下载 → 配置 → 运行，最快体验产品能力
- **集成教程**：从零将 SDK 集成到自有项目
- **排障指南**：遇到问题时的诊断和解决流程
- **功能扩展**：在已有集成基础上添加新能力

### 智能搜索（search）

7 层匹配策略按优先级执行：

1. 错误码精确匹配
2. Slice ID 精确匹配
3. 标签精确匹配
4. 产品 + 模糊匹配
5. 跨产品关系匹配
6. 场景匹配
7. 模糊 + 关键词映射（中英互转）

无匹配时进入 4 级 Fallback 链，确保有效回答。

### 代码生成与校验（apply）

基于 Slice 和 Scenario 知识生成生产级示例代码，并通过多层验证确保代码可直接使用。有两种工作模式：

- **生成模式**：读取 Slice 的 API 签名、代码示例和约束规则，生成符合最佳实践的生产级代码
- **审查模式**：用户贴入自己的代码，基于知识库规则进行校验和修复

两种模式共享同一条验证管线：

1. **约束合规检查** — 逐条校验 ALWAYS/NEVER（产品级）和 MUST/MUST NOT（平台级）规则
2. **跨 Slice 检查** — 前置状态验证、跨产品依赖、平台生命周期、清理对称性
3. **编译验证** — 在实际项目环境中编译，以证据而非推测确认代码正确性
4. **集成安全检查** — 确保代码不破坏已有项目（SDK 初始化冲突、依赖冲突、回归测试）

核心原则：**没有编译证据，不声称代码正确；每个 issue 必须附带可直接替换的修复代码。**

### 场景引导（topic）

基于 Scenario 文件，通过 Checkpoint 机制分步引导用户完成完整功能集成，每一步都会确认用户是否成功再继续。

## 多工具支持

同一套知识库 + 同一份 `ai-instructions/` 指令源，适配多种 AI 编程工具：

| 工具 | 适配文件 | 触发方式 |
|------|---------|---------|
| **Claude Code** | `.claude/skills/trtc/`、`CLAUDE.md`、`.claude/settings.json`（hooks） | `/trtc` slash command + 自动 hook 强制约束 |
| **Cursor** | `.cursor/rules/*.mdc` | 关键词触发 / `alwaysApply: true` 自动注入 |
| **OpenAI Codex CLI / Aider / Cline / CodeBuddy** | `AGENTS.md`（项目根目录） | 项目会话启动时自动注入 |
| 任何工具 | `.claude/skills/trtc/room-builder/guardrails/trtc_verify_ui.py` 等命令行脚本 | 通过 Bash 直接调，作为 ground-truth 校验 |

> **设计原则**：
> - **Layer 2 知识库**是单一数据源，多种工具共享同一份 `knowledge-base/`，不重复维护。
> - **`ai-instructions/`** 是跨工具 prompt 的单一真理源，三种入口文件由它派生。
> - **强约束放脚本，软约束放 prompt**：脚本（命令行 + Claude Code hook）是 ground truth，prompt 只起提醒作用，不依赖模型自我克制。

## 三层架构

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 3: Skills / Rules（用户交互层）                             │
│  Claude Code  →  .claude/skills/trtc/  +  .claude/settings.json  │
│                  （SKILL.md 路由 + hooks 强制约束）                 │
│  Cursor       →  .cursor/rules/        (trtc-router.mdc 路由)    │
│  Codex CLI    →  AGENTS.md             (项目根目录自动注入)        │
│                                                                  │
│  ↑ AGENTS.md / CLAUDE.md / .cursor/rules/{...}.mdc 部分内容       │
│    由 ai-instructions/ 单一指令源派生                              │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: Knowledge Base（结构化知识层）— 多种工具共享              │
│  index.yaml → slices/ + scenarios/                               │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: Runtime（各工具自身运行时）                              │
│  Claude Code Runtime / Cursor Agent / OpenAI Codex CLI / ...     │
└─────────────────────────────────────────────────────────────────┘
```

知识库（Layer 2）是**单一数据源**，不因工具不同而重复维护。各工具只替换 Layer 1/3 的适配层；其中跨工具共享的 prompt 部分由 `ai-instructions/` 集中维护、自动派生。