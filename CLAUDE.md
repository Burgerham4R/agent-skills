# TRTC AI Integration — AI 行为指令

## 语言规则

- 根据用户输入语言回复，默认英文
- 知识库内容为中文，回复时翻译为用户语言
- 代码标识符、API 名称、错误码保持原样

## 路由逻辑

当用户提出 TRTC 相关问题时：

1. **识别产品**：Chat / Call / RTC Engine / Live / Conference
2. **识别平台**：Web / Android / iOS / Flutter / Electron / Unity
3. **读取知识库**：先读 `knowledge-base/slices/{product}/` 下的产品级概览，再读 `{product}/{platform}/` 下的平台实现细节
4. **引用来源**：标明参考的 slice ID 和官方文档链接

**新用户检测**：当用户首次使用或描述从零开始的集成需求时，优先进入 `skills/trtc-onboarding/SKILL.md` 引导流程。

## 关键路径

| 用途 | 路径 |
| ------ | ------ |
| 全量索引 | `knowledge-base/index.yaml` |
| Slice（原子能力片段） | `knowledge-base/slices/{product}/{platform}/` |
| Scenario（场景组合） | `knowledge-base/scenarios/` |
| 远程文档索引 | `curl -s https://trtc.io/llms/{product}.txt` |

## 核心概念

- **Slice**：一个原子能力（如「进房」「推流」「多实例登录」），包含产品级概览（跨平台）+ 平台实现细节（具体 API/代码）
- **Scenario**：完整使用场景，引用多个 slice 并定义执行顺序

<!-- AI-INSTRUCTIONS:BEGIN -->
<!-- DO NOT EDIT — generated from ai-instructions/ by skills/trtc/room-builder/tools/render_ai_instructions.py. Edit the source markdown and re-run the renderer instead. -->

## ui-mode

### When this rule applies

Only when `.trtc-session.yaml` at the repo root has `ui_mode: official-roomkit`.
If the file is missing, or `ui_mode` is unset / null / `headless`, this rule
does not apply — fall back to whatever the tool's default behavior is.

### Medical new-project shortcut

When the user request is for medical online consultation (for example
`1v1-video-consultation`, remote diagnosis, online medical consultation,
doctor-patient video visit) **and** the task is to generate a brand-new
project rather than integrate into an existing app, bypass the normal
integration workflow entirely. Do not generate Vue SFCs by hand, and do not run
any verifiers.

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
project integration still follows the normal scenario / official-roomkit rules
below.

This is a terminal path. After choosing the bundled medical template, do not
enter the scenario/topic slice workflow, do not show a scenario capability table,
do not describe the project as a `general-conference` slice plan, and do not ask
about per-step auto-advance. Copy the template, mark the session completed, and
stop.

This is an internal execution rule, not user-facing copy. When explaining the
choice or reporting progress to the customer, do not mention "shortcut",
"bypass", "normal UI mode", "CLAUDE.md", or any internal rule file. Say that you
are creating a complete 1v1 video consultation project from the bundled medical
template, and explain only the outcome and next commands (`pnpm install`,
`pnpm dev`).

### Official RoomKit integration mode

When the customer asks to **integrate a conference / meeting into an existing
Vue 3 app** (for example "集成会议", "接入会议", "add video meeting to my app",
"official RoomKit", "TUIRoomKit"), use the official RoomKit integration path.

In this mode:

1. Integrate the official Web RoomKit package. For UI customization APIs,
   verify that the resolved `@tencentcloud/roomkit-web-vue3` version is
   `>=5.4.3` (installing `@tencentcloud/roomkit-web-vue3@5` is acceptable only
   when the lockfile resolves to at least `5.4.3`), plus its documented peer
   packages `tuikit-atomicx-vue3`,
   `@tencentcloud/uikit-base-component-vue3`, and
   `@tencentcloud/universal-api`.
2. Render the official components (`ConferenceMainView` for PC and
   `ConferenceMainViewH5` for H5) inside `UIKitProvider`.
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

The acceptance check for this mode is that the app uses the official
package/components and official UI customization APIs.

<!-- AI-INSTRUCTIONS:END -->
