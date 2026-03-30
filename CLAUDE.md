# TRTC AI Integration 知识库

本项目是 TRTC（Tencent Real-Time Communication）的 AI 辅助集成知识库，通过 Claude Code Skills 帮助开发者快速集成和排障。

## 项目结构

```
ai-integration/
├── CLAUDE.md                          # 本文件 — 项目级 AI 指令
├── .claude/skills/trtc/               # Claude Code Skills
│   ├── SKILL.md                       # 路由 skill（入口）
│   ├── onboarding/SKILL.md            # 新手引导（分流 → demo/集成/排障/扩展）
│   ├── search/SKILL.md                # 搜索 slice（原子能力）和 scenario（集成场景）
│   ├── apply/SKILL.md                 # 应用/校验代码
│   └── topic/SKILL.md                 # 场景引导
├── llms.txt                           # llms.txt 内容规范 + 初始模板（顶层产品索引）
├── llms/                              # llms.txt 子文件模板（最终由文档站构建流程自动生成）
│   ├── {product}.txt                  # 产品概述 + 平台链接（如 live.txt, chat.txt）
│   └── {product}-{platform}.txt       # 平台概述 + 官方文档链接（如 live-ios.txt）
├── knowledge-base/
│   ├── index.yaml                     # 全量索引（v3.0 — 含 source/priority/domain 字段）
│   ├── slice-spec.md                  # Slice 定义规范（拆分标准、编写规范、规划方法论）
│   ├── slices/                        # 原子能力片段
│   │   ├── {product}/                 # 按产品分类 (chat/call/rtc-engine/live/room)
│   │   │   ├── {ability}.md           # 产品级概览（跨平台通用）
│   │   │   └── {platform}/            # 按平台分类 (web/android/ios/flutter)
│   │   │       └── {ability}.md       # 平台实现细节
│   └── scenarios/                     # 场景组合
│       └── {scenario-name}.md         # 引用多个 slice 的完整场景
```

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

**三级结构**：`llms.txt`（产品索引）→ `{product}.txt`（产品概述 + 平台链接）→ `{product}-{platform}.txt`（平台概述 + 官方文档链接）

**定位**：仓库中的文件是**内容规范和初始模板**，最终由 trtc.io 文档站构建流程自动生成并部署到 CDN。文档站团队根据此模板编写生成脚本，从文档源（MDX/Markdown）自动产出 llms.txt 系列文件，确保文档更新时自动同步。

**与 knowledge-base 的关系**：
- `knowledge-base/`（slices + scenarios）= 面向内部 AI Skills 的结构化知识库，包含详细的代码示例、排障指南
- `llms/` = 面向外部 LLM 的轻量索引，仅包含概述和指向 trtc.io 官方文档的链接

### 三层架构
```
Layer 3: Skills（用户交互层）— trtc / onboarding / search / apply / topic
Layer 2: Knowledge Base（结构化知识层）— slices/ + scenarios/ + index.yaml
Layer 1: Claude Code Runtime — .claude/skills/ + CLAUDE.md
```

## AI 行为指令

**语言**：根据用户输入语言回复，默认英文。知识库内容为中文，回复时翻译为用户语言。代码标识符、API 名称、错误码保持原样。

**新用户检测**：当用户首次使用或描述从零开始的集成需求时，优先进入 `onboarding/SKILL.md` 引导流程。

当用户提出 TRTC 相关问题时：
1. **识别产品**：Chat / Call / RTC Engine / Live / Room
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
| Room | `slices/room/` | 房间管理（创建/销毁/成员管理） |

## 支持的平台

Web / Android / iOS / Flutter / Electron / Unity
