# Path A2 — Direct Integration

> Loaded by `../../trtc-onboarding/SKILL.md` when `intent ∈ {integrate-scenario, integrate-feature}` in `${CLAUDE_PROJECT_DIR}/.trtc-session.yaml`.
> Before reading this file, SKILL.md must have populated `${CLAUDE_PROJECT_DIR}/.trtc-session.yaml` and passed Stage 1 calibration (including Stage 1.0 conflict resolution if applicable).

**Your role: Co-developer.** You scan the project and write code that follows slice-defined best practices. Code-writing runs inside the topic slice loop, where a silent internal structural gate (`apply.py`) runs before each step is declared done — the user never opts into it, and it is never surfaced as a user-facing service. See **"About apply"** below.

## About apply (internal structural gate)

A2 does **not** call apply directly. Code-writing happens inside the topic slice loop (A2 hands off to `../../trtc-topic/SKILL.md`), and topic runs `apply.py` as a per-step **structural gate** during that loop. You do not construct any apply request here.

What the gate is (and isn't): it is a state-machine forcing function + a lightweight check that code exists and each slice's entry symbol is wired up — it stops the AI from declaring a step done without running a deterministic check. It does **not** verify types, compilation, or runtime correctness. See `../../trtc-apply/SKILL.md` for the exact behavior. Correctness comes from copying slices verbatim and the user confirming in their real project.

**Never:**
- Never tell the user "I'm calling apply" or "apply said X". apply is silent infrastructure.
- Never declare a step done while topic's state machine is at `apply_failed` — the Stop hook blocks end-of-turn until apply passes.

> **Slice discovery vs. slice loading in this path:**
>
> - **When the slice ID is already known** (user picked from A2-Q1 menu, or scenario file lists the slice sequence): read `${CLAUDE_PLUGIN_ROOT}/${CLAUDE_PLUGIN_ROOT}/knowledge-base/{slice.file}` and the platform-specific file at `${CLAUDE_PLUGIN_ROOT}/knowledge-base/slices/{product}/{platform}/{ability}.md` directly. Do NOT call search.
> - **When the slice ID is unknown** (user described a feature in free text, or Stage 0 inferred `target_features` from natural language): call `../../trtc-search/SKILL.md` with `intent=feature` to discover the matching slice ID. Read `response` fields by name — see `../../trtc-search/SKILL.md` → "Response Contract" for the schema.
> - **When `response.status == 'matched'` and `matches.length == 1`** (and `content_loaded: full`): the slice is found — load the file directly from `matches[0].file_paths_read` and proceed.
> - **When `response.status == 'matched'` and `matches.length > 1`** (typically with `content_loaded: summary` set per match): present the slice summaries to the user and let them pick which to integrate. Use `AskUserQuestion` with each summary as an option.
> - **When `response.status == 'no_match'` or `'no_slice'`**: the feature is not covered in the knowledge base. Fall back to `../../trtc-docs/SKILL.md` (which will use llms.txt to find official documentation). Inform the user in their language that the KB doesn't have a detailed integration guide for this feature, and present the official docs instead.
> - **When `response.status == 'status_planned'`**: the slice is indexed but not yet written. Show the user `matches[0]`'s index-level description, tell them this feature's detailed playbook is still being authored, and offer to fall back to `../../trtc-docs/SKILL.md` for the official-doc equivalent.
> - **When `response.status == 'ambiguous_product'`**: the user's description plausibly matches multiple products (`response.ambiguous_candidates`). Ask the user to confirm which product, then re-call search with the confirmed `product` set. Do NOT pick silently.
>
> Users never see that search was involved — you compose the final answer with the slice content.

Recap example:
> Alright — Live on iOS, adding gift function to your existing project. I see your Podfile already has AtomicXCore and LoginStore is set up, so we'll start at the gift module directly.

## A2-Qpre — Capability overview (Conference only)

**Trigger**: `product = conference` AND `intent ∈ {integrate-scenario, integrate-feature}` AND `capability_overview_shown != true` in `${CLAUDE_PROJECT_DIR}/.trtc-session.yaml`.

Skip for all other products. Skip whenever `capability_overview_shown = true` (already shown earlier this session, including session reloads and A2-Q4 "Add another feature" loop-backs).

**Purpose**: Conference has 16+ capability slices spanning 7 functional groups. Users who are new to the product cannot make informed scenario or feature choices without first understanding what Conference can do. This step provides a structured capability overview before any selection question, replacing the "blind choice" problem with "informed choice."

**Execution**:

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/trtc-topic/references/execution-units.yaml` → `scenarios.general-conference.delivery_units` for the authoritative grouping.
2. Read `${CLAUDE_PLUGIN_ROOT}/knowledge-base/index.yaml` → `slices` for each slice's `name` and `description` (filter by `id` starting with `conference/`).
3. Render the capability overview in the user's language, using this format:

```
Conference 可以帮你搭建视频会议应用，以下是可集成的全部能力：

[会议基础链路]
  登录与鉴权 — 统一登录态、SDKAppID/UserID/UserSig 鉴权、登录失效/多端顶替处理
  房间创建、加入、离开与结束 — 会议从创建到结束的主链路

[会前准备]
  入会前设备检查 — 摄像头/麦克风/扬声器的会前检测与本地预览
  设备控制 — 会中摄像头/麦克风/扬声器的开关、切换、权限处理

[音视频与布局]
  参会人列表与状态 — 参会人列表、角色、发言态、音视频状态
  视频布局 — 视频区域渲染、布局模板切换、共享突出展示
  网络质量 — 会中网络状态感知、弱网提示、重连状态

[会中协作]
  屏幕分享 — 桌面端共享屏幕、共享系统音频、共享状态监听
  会中聊天 — 会议与群组会话绑定、消息收发、历史分页

[成员与会控]
  参会人管理与角色治理 — 角色治理、全员/单成员会控、设备申请审批
  会中呼叫 — 会议进行中向房外用户发起实时呼叫

[预约会议]
  预约会议 — 未来会议的创建、更新、取消、列表查询与到点提醒

[视频增强]
  美颜效果 — 磨皮/美白/红润等基础美颜
  虚拟背景 — 背景虚化/替换、模型资源配置、浏览器支持性检测
```

4. After the overview, do NOT ask a separate "Did you read this?" question. Proceed directly to A2-Q0 (scenario selection) or A2-Q1 (module selection), depending on `intent`.
5. **Persist `capability_overview_shown = true`** to `${CLAUDE_PROJECT_DIR}/.trtc-session.yaml`. Piggyback on the next session write (the Stage 1 confirmed write, or the first Checkpoint write) — do NOT trigger an extra Write just for this field.

**Key rules**:
- The overview is **informational only** — no selection, no `AskUserQuestion`. It exists to give the user mental context for the choices that follow.
- Group titles come from `execution-units.yaml` `delivery_units[].title`. Slice descriptions come from `index.yaml` `slices[].description`. Do NOT hardcode either — read them at runtime so the overview stays in sync when slices are added/removed.
- Keep descriptions to one line each. This is a menu card, not a tutorial.
- If `execution-units.yaml` is missing or has no entry for `general-conference`, fall back to listing all `conference/*` slices from `index.yaml` in declaration order without grouping.
- This step runs **once per session**, gated by `capability_overview_shown`. On subsequent returns (e.g. A2-Q4 "Add another feature" → loop back to A2-Q1), skip A2-Qpre — the user has already seen the overview.

## A2-Q0 — Scenario vs single-feature branching

Skip if `intent = integrate-feature` was already explicitly set (user said "add gift" — no need to ask about scenarios).

Ask when `intent = integrate-scenario`, or when the user finished Path A1 of a product that supports scenario-based UI (Conference / Live), or when `target_features` is empty.

**If `product = conference`:** A2-Qpre has already been shown (or skipped on reload). The user now has context about what Conference can do. Proceed with scenario selection.

Question text: "What kind of experience are you building?"

The supported scenarios for v1 are `general-conference` and `1v1-video-consultation`. Do NOT read `index.yaml` to construct this list — these two are aligned with `reference/supported-matrix.md`.

These two scenarios are NOT interchangeable: `1v1-video-consultation` is a **medical-only terminal path** that copies a complete healthcare project (see CLAUDE.md → Medical new-project shortcut). It must NEVER be presented as a generic option to non-medical users.

### A2-Q0 high-confidence short-circuit (run FIRST)

**Precondition**: A2-Qpre has already been shown (or skipped per its trigger rules). The user has seen the capability overview and now has context for what Conference can do.

Before showing any menu, check `scenario` already in `${CLAUDE_PROJECT_DIR}/.trtc-session.yaml` (populated by Stage 0 business-keyword inference, see `SKILL.md` → Business-scenario → product mapping table):

| Inferred `scenario` | Confidence signal (from user's first message) | Action |
|---|---|---|
| `general-conference` | "企业内部会议", "部门例会", "团队会议", "团队协作", "corporate meeting", "internal meeting", "general meeting", "视频面试", "远程培训", "online classroom" — any non-medical multi-party scenario keyword | Skip the 2-option menu. Show a single confirmation step: recap the scenario fit ("企业内部会议属于通用会议场景，覆盖多人视频会议、屏幕共享、会控、成员管理"), then `AskUserQuestion` with ONE option "Confirm general-conference" (the auto Other lets the user disagree if needed). On confirm → A2-Q0.5. On Other → re-run Stage 0 inference on the free text. |
| `1v1-video-consultation` | "远程医疗", "在线问诊", "视频问诊", "医患沟通", "telemedicine", "remote consultation" — any medical-domain keyword | Skip the 2-option menu. Show a single confirmation: recap "1v1 视频问诊场景将创建一个完整的问诊项目模板", `AskUserQuestion` with ONE option "Confirm 1v1-video-consultation". On confirm → A2-Q0.5 (medical new-project condition). On Other → re-run Stage 0 inference. |
| `general-conference` AND `1v1-video-consultation` both inferred (rare, only when first message mixes both domains) | — | Fall through to the 2-option menu below. |
| Neither inferred (`scenario = null`) or scenario is one not in v1 (e.g. webinar) | — | Fall through to the 2-option menu below (or trigger Integration scenario gate for hidden scenarios). |

**Why short-circuit exists**: the two scenarios are domain-segregated. Forcing a non-medical user (e.g. "企业内部会议") to look at "1v1 视频问诊 — copies a medical project" alongside their actual choice creates confusion and erodes trust. When the inference is unambiguous, skip the menu.

### Scenario matching rule (for the fall-through 2-option menu only)

When the short-circuit does NOT trigger (i.e. `scenario` is null, or the user described a use case that doesn't cleanly map to either v1 scenario):

1. Acknowledge what they asked for
2. State that this specific use case does not have a dedicated scenario template
3. Show the supported scenarios with their scope description (from the option table below)
4. Recommend the best fit — state which one and why it's the closest match
5. Let the user confirm

**The key rules:**
- NEVER silently map an unsupported scenario name to a supported one without explaining
- NEVER present the medical template as suitable for non-medical use cases (it copies a complete medical-specific project) — the short-circuit above handles unambiguous non-medical inputs; the 2-option menu only runs when intent is genuinely ambiguous
- When the 2-option menu DOES run (genuine ambiguity), show both options with their scope description so the user can make an informed choice
- Do NOT invent features or promise capabilities that are not in the scenario — only describe what the scenario actually provides

**Question text** (for the 2-option menu — runs only when the short-circuit above did NOT fire):

"What kind of experience are you building?"

| # | Option | Fills |
|---|--------|-------|
| 1 | General meeting / 通用会议 (multi-party video meeting — fits most use cases including online education, remote training, team collaboration) | `scenario = general-conference` |
| 2 | Telemedicine / 1v1 视频问诊 (medical consultation template — ONLY for healthcare scenarios, copies a complete medical project) | `scenario = 1v1-video-consultation` |

(2 options only. "Type something" is auto-provided by AskUserQuestion's Other — do NOT add it as an explicit option. If free-text input maps to an unsupported scenario, trigger Integration scenario gate.)

**Free-text handling**: if the user's free text maps to a hidden scenario (e.g. "webinar", "研讨会", "multidoctor", "会诊"), trigger the Integration scenario gate recap from `onboarding/SKILL.md` → `### Integration scenario gate` instead of falling through to A2-Q1.

**After user selects a conference scenario** → proceed immediately to A2-Q0.5 (Conference integration mode). Do NOT skip A2-Q0.5.

**If `product = live`:**

| # | Option | Fills |
|---|--------|-------|
| 1 | Entertainment live room (gifts, barrage, co-guest) | `scenario = entertainment-live-room` |
| 2 | E-commerce live streaming | `scenario = ecommerce-live` |
| 3 | I want to pick individual features myself | fall through to A2-Q1 |
| 4 | Type something | free-text |

## A2-Q0.5 — Conference integration mode (conference scenarios only)

**Trigger**: the user picked one of the conference scenarios in A2-Q0
(`general-conference` / `webinar-conference` / `1v1-video-consultation` / `medical-multidoctor-consultation`).
Skip for all other products and for the A2-Q1 fall-through branch.

**Purpose**: decide how topic will integrate the conference UI — as the
official RoomKit UI, or as headless composables where the user supplies their
own UI. Ask BEFORE handing off to topic, so topic reads `ui_mode` from the
session file at skill entry.

**User-facing wording rule**: Do not expose implementation labels such as
`A2-Q0.5`, `ui_mode`, "CLAUDE.md", "shortcut", "bypass", "theme workflow",
"normal UI mode selection", or "topic handoff" in chat. Present this as a
product choice the customer is making, not as internal routing.

### Medical new-project condition

When ALL of the following are true, use the **medical-specific 3-option menu** below instead of the default 3-option menu:

- `scenario = 1v1-video-consultation`
- `project_state.has_trtc_dep = false` (no existing TRTC project detected — indicates a brand-new project)

For new medical consultation projects, the recommended path is copying the
bundled template project directly. This is an internal routing rule; do not
mention the shortcut or CLAUDE.md to the user.

**Question text (medical new-project)** (translate to user's language at runtime):

> How would you like to start the 1v1 video consultation project?

| # | Option | Fills | Next |
|---|--------|-------|------|
| 1 | Create a complete runnable consultation project (recommended: includes the full consultation UI, mock data, and config; start with `pnpm install` and `pnpm dev`) | `ui_mode = medical-template` | execute Medical template copy flow (below) |
| 2 | Add business logic only (composables / stores / types; customer provides UI) | `ui_mode = headless` | hand off to `../../trtc-topic/SKILL.md` (Read) with headless spec |

(2 options; "Type something" is auto-provided by AskUserQuestion's Other — do NOT add it as an explicit option per Global rule #2.)

**Medical template copy flow (option 1 selected):**

1. Ask the user for the target project directory (or default to a sibling directory like `../medical-consultation/`).
2. Copy `${CLAUDE_PLUGIN_ROOT}/skills/trtc/room-builder/templates/scenarios/medical-consultation/` to the target directory, preserving structure exactly as packaged.
3. Do NOT read `../../trtc-topic/SKILL.md`, do NOT show scenario capabilities or a slice/module overview, and do NOT run A2-Q0.6. The template path is terminal and does not enter the slice state machine.
4. Do NOT generate Vue SFCs, do NOT run any UI/medical verifiers.
5. Tell the user to use `pnpm install` for dependencies and `pnpm dev` for local development. Do NOT recommend `npm install` / `npm run dev` (this template starts much slower with npm and can show a blank first screen for a while).
6. Set `ui_mode = 'medical-template'`, `current_step = 'template-copied'`, and `status = completed` in `${CLAUDE_PROJECT_DIR}/.trtc-session.yaml`. Write session.
7. Do NOT hand off to topic — the template is a complete, self-contained project; no step-by-step slice execution needed.

**Medical template user-facing recap**: When option 1 is selected, say something
like: "好的，我会创建一个完整的 1v1 视频问诊项目，里面已经包含问诊 UI、模拟数据和基础配置。创建完成后用 `pnpm install` 和 `pnpm dev` 启动。" Do not say the user "hit" or "matched" an internal rule.

**Medical template default / recommendation rule**: When `scenario = 1v1-video-consultation` AND `project_state.has_trtc_dep = false`, map short confirmations ("推荐", "默认", "1", "模板", "快速", "直接复制") to option 1 (template copy). Only proceed to options 2–3 when the user explicitly asks for a different integration approach.

**Medical template resume rule**: If a later turn resumes a session with
`ui_mode = medical-template`, `current_step = template-copied`, or
`status = completed`, do not resume topic and do not re-open the slice sequence.
Summarize that the complete 1v1 consultation project has already been created
and repeat only the next commands (`pnpm install`, `pnpm dev`) if useful.

---

### Default 2-option menu (non-medical or existing project)

When the medical condition above is NOT met (i.e. `scenario != 1v1-video-consultation` OR `project_state.has_trtc_dep = true`), use the standard menu:

**Question text** (translate to user's language at runtime):

> How do you want to integrate the conference UI?

| # | Option | Fills | Next |
|---|--------|-------|------|
| 1 | 用官方现成会议界面（推荐，最快）— 直接用官方会议组件,开箱即有完整界面（视频、工具栏、成员列表、聊天等），按钮/挂件/拦截/分享链接/布局通过官方 API 调整 | `ui_mode = official-roomkit` | execute official-roomkit fast path (no topic handoff) |
| 2 | 只要业务逻辑代码,界面我自己写 — 生成可嵌入的 composables / stores / 类型,**不含任何会议界面**;适合已有设计系统或想完全自己掌控 UI 的项目 | `ui_mode = headless` | hand off to `../../trtc-topic/SKILL.md` (Read) with headless spec |

(2 options; "Type something" is auto-provided by AskUserQuestion's Other — do NOT add it as an explicit option per Global rule #2.)

Persist `ui_mode` to `${CLAUDE_PROJECT_DIR}/.trtc-session.yaml`. Piggyback on the Stage 1 confirmed
write — do NOT trigger an extra Write just for this field.

**Default / recommendation rule (non-medical)**: If the user says "集成会议", "接入会议",
"快速接入", "官方 UI", "RoomKit", "TUIRoomKit", or asks for UI tweaks on top of
the official meeting UI, recommend option 1 and map short confirmations
("推荐", "默认", "1", "官方") to `ui_mode = official-roomkit`.

**Telemedicine default**: maps to room-builder's `one-on-one` scene. Multi-party
consultation is out of scope for this release (see pending_todos).

When a scenario is chosen:

0. **Terminal medical-template guard.** If `scenario = 1v1-video-consultation`
   and `ui_mode = medical-template`, STOP here and execute the Medical template
   copy flow above. Do not run the following topic handoff steps.

**Branch by `ui_mode`:**

### If `ui_mode = official-roomkit` (fast path — no topic, no state machine)

Official RoomKit mode does NOT hand off to topic. The official component
packages all 16 capabilities internally — there is no per-slice code to
generate. Onboarding handles the entire generation inline:

1. **Read these files (and only these):**
   - `${CLAUDE_PLUGIN_ROOT}/knowledge-base/slices/conference/web/official-roomkit-api.md` — complete API signatures, calling sequence, code example, MUST/MUST NOT
   - `${CLAUDE_PLUGIN_ROOT}/knowledge-base/slices/conference/web/official-roomkit-login-ui.md` — login page UI structure and styling constraints
   - `${CLAUDE_PLUGIN_ROOT}/skills/trtc-onboarding/reference/usersig-handling.md` — UserSig credential protocol

2. **Generate the project files in one shot:**
   - Login page (collect/pre-fill sdkAppId + userId, placeholder userSig per the UserSig protocol)
   - Meeting room page (mount `ConferenceMainView`/`ConferenceMainViewH5` inside `UIKitProvider`, wire `conference.*` API calls)
   - Router config (login → meeting transition)
   - Any scenario-specific customizations (e.g., `setWidgetVisible` to hide/show widgets relevant to the chosen scenario)

3. **Run one compliance check** against `official-roomkit-api.md`'s MUST/MUST NOT rules. No need for the full apply pipeline — just verify:
   - No `SecretKey` / `crypto-js` / `pako` in client code
   - `conference.login()` before room operations
   - `setWidgetVisible` / `registerWidget` / `onWill` registered after login, before joinRoom
   - `setFeatureConfig({ shareLink })` after joinRoom succeeds
   - Cleanup functions collected and called on ROOM_LEAVE + ROOM_DISMISS

4. **Save session:** `current_step = 'official-roomkit-done'`, `status = completed`.

4.5. **UserSig fill guidance + run steps (MUST surface to user):** the login
   code always uses a placeholder userSig (the skill never auto-generates one).
   Include the **"如何获取并填入 UserSig"** handoff block from
   `reference/usersig-handling.md` → "Completion handoff", with the real
   file path / variable filled in. Direct the user to the TRTC console to
   generate a test userSig. Also tell the user to install dependencies before
   `dev` (`pnpm install` → `pnpm dev`, or the project's package manager).

5. **Do NOT:**
   - Read any other slice file (room-lifecycle.md, device-control.md, etc.)
   - Hand off to `../../trtc-topic/SKILL.md`
   - Run the state machine (init_slice_queue, next_slice, etc.)
   - Ask A2-Q0.6 (auto-advance policy) — irrelevant without a slice loop

### If `ui_mode = headless` (topic path — state machine)

1. **Handoff to `../../trtc-topic/SKILL.md` via Read.** Read `${CLAUDE_PLUGIN_ROOT}/skills/trtc-topic/SKILL.md` and execute its flow. (Plain Read is the current handoff convention — the §3.5 cross-skill `Skill()` tool handoff was walked back. The real constraints that prevent topic from being silently bypassed live in PreToolUse / Stop hooks and the on-disk state machine, not in how SKILL.md is loaded — so plain Read is sufficient.)

   Scenario-driven step-by-step execution (reading the scenario file, walking the ordered slice list, loading per-step slices, pausing between steps, verification checklist) is topic's responsibility, not onboarding's. For Vue3 Web no-UI Atomicx/API-direct requests, topic must first run its headless business-flow audit before generating code. Onboarding A2 owns intent identification and scenario selection; once a scenario is picked, topic owns the drive.
   Do not mark `session_context.headless_business_flow_confirmed = true` in onboarding. Topic owns that confirmation after it asks the Atomicx no-UI business-flow questions and records the user's answers.
2. Pass the scenario id and the current `session_context` (product, platform, credentials if collected, `target_features`, `project_state`) to topic as inputs. Topic will read `${CLAUDE_PLUGIN_ROOT}/${CLAUDE_PLUGIN_ROOT}/knowledge-base/{scenario.file}` itself.
3. Save `session_context.current_step = 'topic-handoff'` and `session_context.scenario = <chosen-id>` so if the user later returns mid-flow, routing can resume topic from where it paused.
4. Do NOT run A2-Q1 (module selection) or A2-Q3 (per-step execution) for scenario-driven flows — those paths are for `intent = integrate-feature` only.

Scenario-driven UI presets, default layouts, and scenario-specific A2-Q4 tweaks are not onboarding's concern after handoff — topic handles them (or defers UI adjustments back to the user as a follow-up).

If the chosen scenario has `status: planned` in the index: tell the user (in their own language) that the detailed playbook for this scenario is still being written, and offer two options — (a) fall through to A2-Q1 for manual module selection, or (b) let onboarding/topic compose the flow on-the-fly from the available slices. Do NOT silently Read `../../trtc-topic/SKILL.md` in this case; topic needs a concrete scenario file to drive its walk-through.

## A2-Q0.6 — Auto-advance policy (scenario-driven flows only)

**Trigger**: the user picked any scenario in A2-Q0 (i.e. `intent = integrate-scenario`).
Skip for `integrate-feature` flows.

**MUST ask — do NOT silently default.** This question must be explicitly asked
before topic starts the slice loop. The "unset → treated as `pause_each`" rule
below is a **fail-closed safety net for legacy/interrupted sessions only**, NOT
a license to skip the question on a fresh scenario flow. Topic re-checks this at
its Step 3 gate: if `intent = integrate-scenario` and `auto_advance_policy` is
unset when the loop is about to start, topic bounces back here. (Skip only when
`ui_mode = official-roomkit` or `medical-template`, which have no slice loop.)

**Purpose**: decide how topic paces the slice loop after `apply.py` passes —
either pause and ask the user 继续? after each slice, or let `apply.py`
auto-advance the cursor when its checks succeed. Pausing on apply
**failure** is unconditional regardless of policy — the user always sees a
break when the code didn't pass the gate.

Ask AFTER A2-Q0.5 (so topic reads both `ui_mode` and `auto_advance_policy`
from the session at skill entry). Piggyback the Stage 1 confirmed write —
no extra Write just for these fields.

**Question text** (translate to user's language at runtime):

> Between each step, do you want me to pause and check in with you, or keep going automatically when things look good?

| # | Option | Fills | Notes |
|---|--------|-------|------|
| 1 | Keep going automatically — only pause if something looks wrong (recommended — fastest, still safe) | `auto_advance_policy = "pause_on_failure"` | Default. apply.py auto-advances cursor on pass |
| 2 | Pause after every step so I can review what changed (slower but maximum control) | `auto_advance_policy = "pause_each"` | Original behaviour |
| 3 | Type something | free-text | re-infer |

Persist `auto_advance_policy` (root-level field) to `${CLAUDE_PROJECT_DIR}/.trtc-session.yaml`. Unset / unknown
values are treated as `pause_each` by topic — fail closed.

## A2-Q1 — Module selection (single-feature mode)

Trigger: `intent = integrate-feature`, or the user chose "pick individual features" in A2-Q0, or A2-Q0 was skipped.

**If `product = conference`:** A2-Qpre has already shown the capability overview. Now present a grouped module selection that mirrors the delivery-unit structure the user just saw. This ensures the selection interaction is visually consistent with the overview — users pick from the same categories they just read about.

Question text: "Which capability groups do you want to integrate? (multi-select; [会议基础链路] is required as the foundation)"

Use `AskUserQuestion` with `multiSelect: true`. Group options by delivery units from `${CLAUDE_PLUGIN_ROOT}/skills/trtc-topic/references/execution-units.yaml` → `scenarios.general-conference.delivery_units`. Map each delivery unit to one option; the option label is the unit title, the option description lists the included slices by name. Example:

| # | Option | Description (auto-generated from unit title + slice names) | Slices |
|---|--------|-------|--------|
| 1 | 会议基础链路（必选） | 登录与鉴权 + 房间创建、加入、离开与结束 | conference/login-auth, conference/room-lifecycle |
| 2 | 会前准备 | 入会前设备检查 + 设备控制 | conference/prejoin-check, conference/device-control |
| 3 | 音视频与布局 | 参会人列表与状态 + 视频布局 + 网络质量 | conference/participant-list, conference/video-layout, conference/network-quality |
| 4 | 会中协作 | 屏幕分享 + 会中聊天 | conference/screen-share, conference/room-chat |
| 5 | 成员与会控 | 参会人管理与角色治理 + 会中呼叫 | conference/participant-management, conference/room-call |
| 6 | 预约会议 | 预约会议 | conference/room-schedule |
| 7 | 视频增强 | 美颜效果 + 虚拟背景 | conference/beauty-effects, conference/virtual-background |

> **Note**: This table shows 7 options which exceeds `AskUserQuestion`'s 4-option cap. Apply the **A2-Q1 conference grouping merge** below to reduce to 4 options.

### A2-Q1 conference grouping merge

When `product = conference`, the 7 delivery units must be merged into 4 options to fit `AskUserQuestion`'s cap. Use this fixed merge:

| # | Option | Merged delivery units | Slices |
|---|--------|----------------------|--------|
| 1 | 会议基础 + 会前准备（必选） | foundation + prejoin | conference/login-auth, conference/room-lifecycle, conference/prejoin-check, conference/device-control |
| 2 | 音视频 + 协作 + 会控 | media + collaboration + moderation | conference/participant-list, conference/video-layout, conference/network-quality, conference/screen-share, conference/room-chat, conference/participant-management, conference/room-call |
| 3 | 预约会议 | schedule | conference/room-schedule |
| 4 | 视频增强（美颜 + 虚拟背景） | effects | conference/beauty-effects, conference/virtual-background |

Option 1 is always selected (required foundation). Options 2–4 are multi-select.

**If `product = live`** (or any non-conference product): use the existing flat option list. Pull from `${CLAUDE_PLUGIN_ROOT}/knowledge-base/index.yaml` slices filtered by product. Example for `product = live`:

| # | Option | Slice |
|---|--------|-------|
| 1 | Login & authentication (required) | live/login-auth |
| 2 | Anchor broadcast + device control | live/anchor-preview + device-control + anchor-lifecycle |
| 3 | Audience watch + live list | live/audience-watch + live-list |
| 4 | Barrage (live comments) | live/barrage |
| 5 | Gift | live/gift |
| 6 | Co-guest (audience goes on mic) | live/coguest-apply |
| 7 | Beauty filters | live/beauty |
| 8 | Audio effects | live/audio |
| 9 | Audience management (mute, kick, admin) | live/audience-manage |
| 10 | Type something | free-text |

Use `AskUserQuestion` with `multiSelect: true`.

### A2-Q1.5 — Business decisions collection (per-slice)

After A2-Q1 multi-select completes, before advancing to A2-Q2: for each slice in the chosen list, run a **business-decisions collection** pass to fill in the open variables that code generation needs. This step is governed by Hard rule #13 in `../SKILL.md`.

**Why this exists:** A slice describes **which APIs** to call. But generating concrete code requires answering business-side questions that are independent of the API surface — e.g. for `conference/login-auth` the slice tells you to call `login(sdkAppId, userId, userSig)`, but it doesn't tell you where `userSig` comes from, what `userId` is mapped from, or where to navigate when the session is lost. Guessing these defaults produces code the user has to rip out. Asking takes one extra `AskUserQuestion` per decision and saves the rewrite.

**The decision list comes from each slice's frontmatter, NOT from a hardcoded table here.** Onboarding reads `business_decisions:` in the slice's frontmatter and asks one `AskUserQuestion` per entry. When a slice author adds / removes / changes decisions, the rule follows automatically — no edit needed in this skill.

**Slice frontmatter contract:**

```yaml
---
id: conference/login-auth
platform: web
business_decisions:
  - key: usersig_source              # YAML key — used as session_context lookup
    tier: blocking                   # blocking (default) | deferrable — see "Decision tiers" below
    question: "UserSig 从哪里获取？"   # exact question shown to user (translate at runtime)
    options:
      - { label: "后端签发（生产推荐）", value: "backend" }
      - { label: "控制台临时生成（开发期）", value: "console" }
    # optional fields:
    multi_select: false              # default false; true → multi-select question
    destructive_subset: false        # default false; true → ask "是否需要破坏性操作？" gate first
    depends_on:                      # only ask this decision if another decision matches
      key: creation_pattern          # ex: "scheduled_features" only asked if "creation_pattern includes scheduled"
      value: ["scheduled", "both"]
  - key: on_session_lost
    tier: deferrable                 #异常/边界路径 → 不阻塞主流程
    default: redirect-login          # deferrable 项 MUST 提供推荐默认值
    question: "登录态失效后页面如何处理？"
    options:
      - { label: "跳回登录页（推荐默认）", value: "redirect-login" }
      - { label: "后台静默重连", value: "auto-refresh" }
      - { label: "弹窗让用户决定", value: "prompt-user" }
  - key: management_features          # multi-select example with a baseline
    tier: blocking
    multi_select: true
    baseline: ["list"]               # always-generated values, NOT shown as options
    question: "主持人需要哪些会控权限？（参会人列表默认展示）"
    options:                         # only the user-selectable extras appear here
      - { label: "管控单个成员", value: "single-control" }
      - { label: "全场管控", value: "all-room" }
      - { label: "成员身份管理", value: "role-and-kick" }
---
```

**Baseline values (`baseline` field, multi-select only):**

某些多选决策里存在"基础项"——它是该能力的前提，几乎总要生成（如 `participant-management` 的成员列表 `list`）。把基础项和真正的可选项放进同一个多选框，会造成颗粒度不一致（用户在"前提"和"权限"之间纠结）。

解决办法：用 `baseline: [...]` 声明这些始终生成的值。规则：
- `baseline` 里的值 **不作为 `options` 展示**，A2-Q1.5 不会让用户勾选它们。
- 采集时，`session_context.business_decisions[<slice-id>][<key>]` 的最终值 = `baseline` ∪ 用户在 `options` 里勾选的值。
- 即使用户一个 option 都没勾，baseline 值依然写入（保证基础能力被生成）。
- 仅对 `multi_select: true` 的决策有效；单选决策忽略此字段。
- 问题文案应点明基础项已默认提供（如"参会人列表默认展示"），避免用户以为漏选。

**Decision tiers (`tier` field):**

每个 `business_decisions` 项可声明一个 `tier`，决定"用户没回答时怎么办"：

| tier | 含义 | 未回答时的行为 |
|------|------|---------------|
| `blocking`（默认，可省略） | 决定主流程走哪条代码分支（如 `usersig_source`、`userid_strategy`、`roomid_origin`）。不答就无法正确生成主流程。 | **维持铁律：缺值则 topic STOP，回 A2-Q1.5 问完再继续。** |
| `deferrable` | 只影响异常/边界路径（如 `on_session_lost`、`passive_exit_target`），不影响登录→建房→进会主链路能否跑通。 | **用 `default` 值先生成 + 注入 `// TODO: 确认<决策项>策略，当前用推荐默认值 <default>` 注释**，主流程跑起来后作为 next step 回填。 |

**`deferrable` 契约（slice 作者必须遵守）：**
- 声明 `tier: deferrable` 的项 **MUST 同时提供 `default`**（取 `options` 里的某个 `value`，通常是标注"推荐"的那个）。缺 `default` 的 deferrable 项视为契约错误，apply gate 抛错给 slice 作者。
- `deferrable` 只能用于异常/边界决策。任何会改变主流程分支结构的决策（建不建房、UserSig 来源、是否匿名）必须是 `blocking`。
- `default` **不是"AI 猜的值"**，而是 slice 作者显式声明、且会通过 TODO 注释告知用户的推荐值——这与"先生成默认代码、等用户报错再改"的反模式有本质区别（后者是无声的、错了用户才发现）。

A2-Q1.5 采集时，`deferrable` 项**仍然会问**（顺序上建议放在该 slice 所有 `blocking` 项之后）；只有当用户**显式跳过 / 未答**时才回退到 `default`。也就是说：能问到就用用户的答案，问不到才用 default 兜底跑通主流程。

**A2-Q1.5 execution algorithm:**

The algorithm groups questions by **delivery unit** (from `${CLAUDE_PLUGIN_ROOT}/skills/trtc-topic/references/execution-units.yaml`) for visual coherence — users see "成员与会控" as a section heading covering 3 slices, not 8 disconnected questions. Storage stays per-slice in `session_context.business_decisions[<slice-id>]`; only the question-asking order is grouped.

```
Build the question plan:
  units = execution-units.yaml[scenario].delivery_units
  ordered_groups = []
  consumed_slices = set()

  For each unit in units (in declared order):
      group_slices = [s for s in unit.slices if s in confirmed_plan]
      If group_slices is empty: skip this unit (none of its slices selected).
      ordered_groups.append({ title: unit.title, slices: group_slices })
      consumed_slices.update(group_slices)

  orphan_slices = [s for s in confirmed_plan if s not in consumed_slices]
  If orphan_slices: ordered_groups.append({ title: "其他", slices: orphan_slices })

Run the questionnaire:
  For each group in ordered_groups:
      Show group.title as a section heading to the user (one short line, e.g. "—— 成员与会控 ——").
      For each slice in group.slices:
          Read slice frontmatter business_decisions[]
          If empty / absent: skip this slice (no decisions needed).
          Sort: ask all tier=blocking decisions first, then tier=deferrable ones.
          For each decision in business_decisions[]:
              If session_context.business_decisions[<slice-id>][<key>] already set:
                  skip (already answered in earlier turn — never re-ask)
                  continue
              If decision.depends_on is set:
                  check: does session_context.business_decisions[<slice-id>][<dep.key>]
                         match dep.value?
                  no → skip this decision
              If decision.destructive_subset = true:
                  first ask "是否需要破坏性操作（{decision label}）？" with 是/否
                  no → set value = []
                      continue
                  yes → fall through to options multi-select
              AskUserQuestion(decision.question, decision.options, multi_select)
              If user answered → persist pick to session_context.business_decisions[<slice-id>][<key>]
                  If decision.multi_select AND decision.baseline is set:
                      final_value = decision.baseline ∪ user_picks   # baseline always included
                      persist final_value (even if user_picks is empty)
              If user explicitly skipped / deferred AND decision.tier == "deferrable":
                  do NOT persist a value (leave the key unset)
                  → topic will fall back to decision.default at generation time + inject a TODO
              If user skipped AND decision.tier == "blocking":
                  # baseline-only multi-select: if a baseline exists, skipping = baseline alone (valid)
                  If decision.multi_select AND decision.baseline is set:
                      persist decision.baseline as the value
                      continue
                  Else:
                      cannot proceed — re-ask (blocking decisions must be answered)
```

**Tier-aware skipping:** `blocking` 决策必须答（用户跳过就重问）；`deferrable` 决策允许用户跳过——跳过时不写入 session，由 topic 在生成代码时回退到 frontmatter 的 `default` 并注入 TODO 注释。这让"主流程先跑通、异常处理后补"成为可能，同时不违反"不无声猜值"的铁律（default 是显式声明 + TODO 可见）。

**Baseline merge:** 对带 `baseline` 的多选决策，存入 session 的最终值始终是 `baseline ∪ 用户勾选`。`baseline` 里的值不在 `options` 出现、用户无法取消，保证基础能力（如成员列表）总被生成。即使用户一个额外项都没选，session 里也会写入 baseline 值（而非空数组）。

**`decision_constraints`（跨 key 组合约束）：** 部分 slice 在 frontmatter 里除 `business_decisions` 外还声明 `decision_constraints:`，描述同一 slice 内**多个决策值之间**的组合规则。每条含 `when`（触发条件）+ 下列之一：

| 字段 | 含义 | A2-Q1.5 消费方式 |
|------|------|-----------------|
| `forbid: {key: value}` | `when` 成立时禁止的组合 | 用户答出该组合时，**不持久化**，提示冲突原因（取 `reason`）并**重问**冲突的那个 key，引导改选 |
| `adjust: {key: {disable_option, prefer}}` | `when` 成立时调整另一 key 的选项 | 提问该 key **之前**先检查：若 `when` 已成立，从 `options` 中灰掉 `disable_option`，并把 `prefer` 列表的首项作为推荐默认 |

例（`conference/room-lifecycle`）：`roomid_origin = join-only` 时，① 禁止 `creation_pattern = both`（选到则重问 creation_pattern）；② 提问 `passive_exit_target` 前灰掉 `lobby` 选项、默认推 `login`。约束校验在 `AskUserQuestion` 持久化之后、进入下一 key 之前执行；`adjust` 在目标 key 提问之前执行。topic 生成代码与 apply gate 也共享这些约束。

**Section heading display:** keep it minimal — one short line above the next AskUserQuestion call, in the user's language. Examples: `—— 会议基础链路 ——`, `—— 成员与会控 ——`, `—— 视频增强 ——`. Do NOT show a full progress bar or "step N of M" — the questions themselves are the progress.

**Scenario absence fallback:** if the session's scenario is not present in `execution-units.yaml`, OR `intent = integrate-feature` (single-feature mode, no scenario), skip the grouping pass entirely and ask in `confirmed_plan` order without section headings. The grouping is purely UX sugar — its absence does not change which questions get asked.

**4-option cap handling:** If `decision.options` has more than 4 entries, slice authors should split them into multiple `business_decisions` entries (group by impact tier or sub-domain) rather than one mega-question. Onboarding never silently truncates options.

**Persistence:** Results live under `session_context.business_decisions` in `${CLAUDE_PROJECT_DIR}/.trtc-session.yaml`:

```yaml
session_context:
  business_decisions:
    conference/login-auth:
      usersig_source: "console"
      userid_strategy: "direct"
      on_session_lost: "redirect-login"
    conference/room-lifecycle:
      roomid_origin: "frontend"
      creation_pattern: "instant"
      passive_exit_target: "lobby"
    conference/participant-management:
      management_features: ["list", "single-control", "all-room"]
      # "list" is baseline (always present, not a user option); "single-control"/"all-room" were picked.
      # "role-and-kick" NOT in array → topic skips setAdmin/revokeAdmin/transferOwner/kickParticipant entirely
    conference/room-schedule:
      schedule_features: ["list", "modify", "events"]
      # "list" is baseline (always present, not a user option); "modify"/"events" were picked.
      # "password" NOT in array → 密码字段/校验不生成
```

**Topic-side contract (Step 3, governed by topic G8):** when generating code for a slice, topic MUST consult `session_context.business_decisions[<slice-id>]` and tailor the output:

- For decisions with `value: "X"` (single-select): generate code matching that branch.
  - `usersig_source = "backend"` → emit `fetch('/api/conference/usersig')` skeleton + TODO; `usersig_source = "console"` → emit placeholder `'YOUR_USERSIG'` + console-link comment（用户需自行到 TRTC 控制台生成测试 UserSig 并填入，skill 不自动签发）.
  - `roomid_origin = "frontend"` → emit `createAndJoinRoom` flow; `roomid_origin = "backend-precreated"` → emit `joinRoom` only flow with backend fetch skeleton.
- For decisions with `value: [...]` (multi-select / multi_select=true): generate ONLY APIs whose ids appear in the array. APIs absent MUST NOT be exported, imported, or rendered as UI entry points.

**If a slice has `business_decisions:` but `session_context.business_decisions[<slice-id>]` is missing or partial:** behavior depends on the missing decision's `tier`:
- **`blocking` 缺值** → topic MUST stop code generation and bounce back to A2-Q1.5 to fill the gap. Do not "default to safe values" — silent defaults are exactly the failure mode this rule prevents.
- **`deferrable` 缺值** → topic does NOT stop. Use the frontmatter `default` value to generate the branch, and inject a `// TODO: 确认<decision-key>策略（当前用推荐默认值 <default>，主流程跑通后可调整）` comment at the relevant code site. This keeps the main flow runnable while flagging the deferred decision visibly.

**MUST NOT:**
- Do NOT bundle multiple decisions into a single `AskUserQuestion` (option semantics get muddled, hits the 4-option cap).
- Do NOT skip A2-Q1.5 because "the user seems experienced" or "the slice looks simple" — every slice with `business_decisions` MUST be asked.
- Do NOT generate UI containers (e.g. a panel that conditionally renders every governance API based on a runtime flag) — unselected APIs MUST be absent from source, not hidden behind v-if.
- Do NOT hardcode the decision list inside `onboarding` — the registry of "what to ask" is each slice's frontmatter, not a table here.

**Slice author checklist** (when authoring or editing a slice):
- Identify every variable in the generated code that depends on business choice (where does X come from / which subset of APIs / how to handle Y when it fails).
- Add one `business_decisions` entry per variable.
- **Assign a `tier`**: if the decision changes the main-flow code structure (credential source, build-room-or-not, anonymous-or-not) → `blocking` (default). If it only affects error/edge handling that doesn't block the main flow from running (session-lost handler, passive-exit target) → `deferrable`, and you MUST also provide a `default` value.
- Group destructive operations behind `destructive_subset: true` so they get a yes/no gate before the option list.
- Use `depends_on` when one decision is only meaningful in the context of another (e.g. `schedule_features` only matters when `creation_pattern` includes scheduled rooms).

**Apply gate cross-check:** apply skill verifies generated code consistency with `session_context.business_decisions`. Concrete checks (non-exhaustive):
- If generated code contains `userSig: 'YOUR_USERSIG'` but slice has `business_decisions: usersig_source` → user must have picked `"console"`; if they picked `"backend"` → fail with mismatch error.
- If generated code calls `kickParticipant`/`setAdmin`/`transferOwner` but `business_decisions.management_features` array doesn't contain `"role-and-kick"` → fail. (Same pattern for `single-control` / `all-room` archetypes.)
- If a slice's frontmatter has no `business_decisions` field but generated code contains placeholders that imply a business choice (e.g. hardcoded `'YOUR_USERSIG'`, hardcoded `roomId`) → emit a warning suggesting the slice author add a `business_decisions` entry.
- If a `business_decisions` entry declares `tier: deferrable` but has no `default` field → fail with a slice-author contract error (deferrable decisions MUST carry a default).

## A2-Q2 — Credentials

Ask the user for their **SDKAppID** only — the skill does NOT sign UserSig, so do
NOT ask for the SecretKey, and there is no MCP auto-detection of credentials.
Reuse the A1-Q1 SDKAppID prompt (see `reference/path-a1-demo.md`). Skip entirely
if `credentials.sdk_app_id_provided` is `true` in the session file.

**Important**: SDKAppID is not a secret — after the user provides it, write the numeric value to `credentials.sdkappid` in the session file at the next Checkpoint, and set `credentials.sdk_app_id_provided` to `true` (do not trigger an extra Write just for credentials). The test UserSig itself is obtained by the user from the TRTC console at integration time (see `reference/usersig-handling.md`).

## A2-Q3 — Per-step progression

### Login step enhancement

When the current step's slice is `{product}/login-auth` (or any slice whose
implementation involves `login()` / `LoginStore` / TIM login / TRTC
`enterRoom` authentication):

**⚠️ BLOCKING GATE — 必须在生成任何登录代码之前完成：**

1. Read `reference/usersig-handling.md` and follow its Generation Protocol.
2. Emit a placeholder userSig + console-handoff instructions. The skill does NOT
   auto-generate UserSig (no MCP, no client-side signing).
3. **If this protocol is not followed, the generated login code MUST NOT be written to disk.**

This gate ensures:
- A placeholder userSig with clear console-fill instructions is emitted
- Input fields remain available for custom userID/userSig at runtime
- **No client-side signing code is ever generated** (no `crypto-js`, no `pako`, no `SecretKey` in source)

Follow the Generation Protocol in `usersig-handling.md` (placeholders +
console-handoff instruction comments).

**Violation self-check (same weight as apply gate):** If your about-to-write login
code contains `HmacSHA256`, `crypto-js`, `pako`, `SecretKey` in a non-comment
assignment, `generateUserSig`, or creates a file matching `**/usersig.*` — you
are violating this gate. STOP, discard, re-read `reference/usersig-handling.md`,
and regenerate.

### Per-step execution

After writing code for each step, topic runs `apply.py` (the structural gate, see **"About apply"** above). Only report the step done after apply passes (state → `apply_passed`). Summarize the outcome to the user using this template:

```
Step {n} ({slice name}) done.
Changes: {N files added, M files modified}. Did not touch {AppDelegate.swift / main.ts / etc.}.
Structural gate: passed ({K} slice entries wired up). Verify in your project by running it.
```

**Persist session state** (see `SKILL.md` § Session context → Checkpoints). After a step passes apply:
- Set `current_step` to the next step's id (e.g. from `A2.3` to `A2.4`)
- Append the just-completed slice id to `completed_steps`
- Update `updated_at` timestamp
- Write to `${CLAUDE_PROJECT_DIR}/.trtc-session.yaml`

**First Write of the session** (i.e. right after Stage 1 calibration confirmed, before this step executes): create the file with `status: active`, all inferred fields filled, and trigger the `.gitignore` auto-update flow described in `SKILL.md` § Session context.

If apply fails (state → `apply_failed`), do NOT write this summary **and do NOT advance `current_step` in the session file**. Re-read the slice, regenerate / patch the code based on the failed rule text in the evidence JSON, and re-run apply. The Stop hook keeps the loop alive until apply passes. If you genuinely can't get it to pass, surface a message framed as "I hit a snag on step {n}" — never "apply skill said X" — and list what was tried.

### Auto-advance rules (default behavior)

| apply result | Action |
|---|---|
| `pass` | **Auto-advance.** Do NOT pause or show a question menu. Immediately proceed to the next slice. Output a one-line step summary and continue generating the next step in the same response. |
| `partial` (only `warning`/`info`) | **Auto-advance with note.** Same as `pass`, but append a collapsed line noting warnings. Continue. |
| `partial` (any `critical`) | **Pause.** Show the critical warnings and ask the user how to proceed. |
| `fail` (after retry exhausted / give-up) | **Pause.** Inform the user and offer options (skip / pause / provide context). |

**Batch output:** When consecutive steps all pass, combine their summaries into a single response. The user sees progress flowing without interruption.

**Completion:** After all planned steps pass, present a final summary table. Do NOT show the per-step question menu below — it only activates when the user explicitly requests step-by-step mode.

**Step-by-step override:** If the user explicitly says "一步一步来" / "pause between steps" / "let me review each step", switch to per-step confirmation mode and show the question menu below after each step. Otherwise, auto-advance is the default.

### Per-step question menu (only when step-by-step mode is active)

Question text: "What would you like to do next?"

| # | Option | Action |
|---|--------|--------|
| 1 | Continue to the next step | advance `current_step`, load next slice |
| 2 | Walk me through why this code is structured this way | expand the slice's ALWAYS/NEVER rationale (no session write) |
| 3 | I want to adjust this step's code | collect diff request; after adjusted code passes apply again, re-write session as in the normal Step passes-apply flow |
| 4 | Pause here | set `status: paused`, keep `current_step` unchanged, Write session; exit the loop |
| 5 | Type something | free-text |

## A2-Q4 — Completion

After all planned steps are done.

Question text: "Integration finished. What's next?"

| # | Option | Action |
|---|--------|--------|
| 1 | Add another feature | loop back to A2-Q1 (as single-feature mode); session `status` stays `active` |
| 2 | I'm good for now | set `status: completed`, Write session, end onboarding cleanly |
| 3 | Type something | free-text |

