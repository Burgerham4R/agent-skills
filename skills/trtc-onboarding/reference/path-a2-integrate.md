# Path A2 — Direct Integration

> Loaded by `../../trtc-onboarding/SKILL.md` when `intent ∈ {integrate-scenario, integrate-feature}` in `${CLAUDE_PROJECT_DIR}/.trtc-session.yaml`.
> Before reading this file, SKILL.md must have populated `${CLAUDE_PROJECT_DIR}/.trtc-session.yaml` and passed Stage 1 calibration (including Stage 1.0 conflict resolution if applicable).

**Your role: Co-developer.** You scan the project and write code that follows slice-defined best practices. Every code-writing step silently runs through `../../trtc-apply/SKILL.md` as an internal quality gate before being declared done — the user never opts into it, and it is never surfaced as a user-facing service. See **"Calling apply"** below for the exact request/response contract.

## Calling apply (internal quality gate)

apply is invoked per step, not per file, and not per session. It follows the I/O contract defined in `../../trtc-apply/SKILL.md` Phase 0. Construct each call explicitly; do not dump raw code and hope apply infers context.

**Request construction** (build this before calling apply):

```yaml
request:
  code:
    - path: {relative path under project root}
      content: {full file content after this step's edits}
    # include every file this step created or modified, not just the "main" one

  product:     {product}
  platform:    {platform}
  capability:  {slice_id of the step just completed, e.g. "live/coguest-apply"}

  project_context:
    root:              {project root absolute path, if file scanning is available}
    modified_files:    {list of paths touched by this step}
    has_existing_tests: {true if the project has a test command configured, else false}

  related_capabilities:
    # include any prerequisite slices the current step depends on,
    # so apply can verify cross-slice prerequisites without re-inferring
    - {e.g. live/login-auth if this step depends on login}
    - {e.g. live/device-control if this step opens camera/mic}

  mode: full | quick | static-only
    # full        → first integration of a full scenario step
    # quick       → small edits (< 50 lines), single capability
    # static-only → no project_context.root available
```

**Mode selection rules:**

| Situation | mode |
|-----------|------|
| First implementation of a slice, full project available | `full` |
| User asked for an adjustment in A2-Q3 option 3, edit is < 50 lines | `quick` |
| No project scanning / no build env (user pasted snippet) | `static-only` |

**Response handling:**

After apply returns, read the structured `response` and branch as follows:

| response.status | What to do |
|-----------------|------------|
| `pass` | Report the step done (see step summary template in A2-Q3). Show the compile command + exit code from `response.compile_check` as proof. Do not display constraint-check details unless the user asks. |
| `partial` | Step done with non-blocking warnings. Show the warnings inline in the step report, in a single collapsed note. Do NOT block the user from moving to the next step unless a warning is a `critical` severity. |
| `fail` | Step NOT done. Do not write the step summary. Follow `response.retry_hint.strategy`: see below. |

**Acting on `retry_hint` when `status = fail`:**

| retry_hint.strategy | What to do |
|---------------------|------------|
| `patch` | Apply the specific fixes listed in `response.constraint_check.issues[*].fix.code_diff`, write the updated files, re-call apply **once** with the same `capability` but updated `code`. |
| `regenerate` | Re-generate the step's code from scratch, guided by `retry_hint.focus_on` (those are the things to fix on the re-gen). Call apply again with the new code. |
| `give-up` | Stop retrying silently. Surface a message to the user framed as "I hit a snag on step N" — never "apply skill said X". Include what was tried (`attempts`) and ask the user whether to skip this step, pause, or provide more context. |
| `missing-field` | **Do NOT retry.** This is a contract violation on the caller side (onboarding built a malformed request), not a code-quality problem. Log the missing field names from `retry_hint.focus_on` internally, then surface "I hit an internal snag on step N" to the user and offer to skip this step. Treat as a self-bug to report rather than a generation quality issue. |

**Retry guidance:** apply runs an idempotent grep — re-running it after a code change either passes or surfaces a different rule_text. Iterate until apply passes; the Stop hook keeps the loop alive while the state is `apply_failed`. There is no fixed retry cap or `failure_signature` mechanism in the current runtime (the V2 give-up cap was removed).

**Never:**
- Never tell the user "I'm calling apply" or "apply said X". apply is silent infrastructure.
- Never show raw `request` / `response` yaml to the user. Translate to the step report template.
- Never skip apply to "move faster". Compile evidence is the only acceptable proof that a step is done.
- **If apply is skipped for any reason** (e.g. context overflow, tool unavailability): the generated file MUST include the following comment at the very top, and the step summary shown to the user MUST include `⚠️ 编译未验证 — apply 未执行，请手动编译确认`. Never declare a step done without this disclosure when apply was not run.

```ts
// ⚠️ APPLY VERIFICATION SKIPPED — compile and verify manually before shipping
```

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

## A2-Q0 — Scenario vs single-feature branching

Skip if `intent = integrate-feature` was already explicitly set (user said "add gift" — no need to ask about scenarios).

Ask when `intent = integrate-scenario`, or when the user finished Path A1 of a product that supports scenario-based UI (Conference / Live), or when `target_features` is empty.

Question text: "What kind of experience are you building?"

**If `product = conference`:**

Use exactly the following 2 options. Do NOT read index.yaml to construct this list — the supported scenarios are defined here and aligned with `reference/supported-matrix.md`.

**Scenario matching rule (MANDATORY — run before showing options):**

When the user has already described a specific use case (e.g. "在线教育", "online classroom", "远程培训", "客户面试") that does not exactly match a supported scenario name:

1. Acknowledge what they asked for
2. State that this specific use case does not have a dedicated scenario template
3. Show the supported scenarios with their scope description (from the option table below)
4. Recommend the best fit — state which one and why it's the closest match
5. Let the user confirm

**The key rules:**
- NEVER silently map an unsupported scenario name to a supported one without explaining
- NEVER present the medical template as suitable for non-medical use cases (it copies a complete medical-specific project)
- ALWAYS show both options with enough context for the user to make an informed choice
- If the user's described scenario clearly maps to one option (e.g. "开个会" → 通用会议), you can recommend more directly but still show both options
- Do NOT invent features or promise capabilities that are not in the scenario — only describe what the scenario actually provides

**Question text** (use when user has NOT described a specific use case, or after the matching explanation above):

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
| 2 | Generate a custom consultation UI in this project (Vue SFC based on the medical scenario) | `ui_mode = full-ui` | hand off to `../../trtc-topic/SKILL.md` (Read) with full-ui spec |
| 3 | Add business logic only (composables / stores / types; customer provides UI) | `ui_mode = headless` | hand off to `../../trtc-topic/SKILL.md` (Read) with headless spec |

(3 options; "Type something" is auto-provided by AskUserQuestion's Other — do NOT add it as an explicit option per Global rule #2.)

**Medical template copy flow (option 1 selected):**

1. Ask the user for the target project directory (or default to a sibling directory like `../medical-consultation/`).
2. Copy `${CLAUDE_PLUGIN_ROOT}/skills/trtc/room-builder/templates/scenarios/medical-consultation/` to the target directory, preserving structure exactly as packaged.
3. Do NOT read `../../trtc-topic/SKILL.md`, do NOT show scenario capabilities or a slice/module overview, and do NOT run A2-Q0.6. The template path is terminal and does not enter the slice state machine.
4. Do NOT run `trtc_prepare_ui.py`, do NOT generate Vue SFCs, do NOT run `trtc_verify_ui.py` or any UI/medical verifiers.
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
| 1 | Official UI (recommended: use the official meeting components for fast integration, with full meeting UI out of the box — video, toolbar, member list, chat, etc. Tune buttons, business widgets, click interceptors, share links, and layouts through official APIs) | `ui_mode = official-roomkit` | execute official-roomkit fast path (no topic handoff) |
| 2 | Business logic only (headless composables / stores / types; you write your own UI — good for projects that already have a design system) | `ui_mode = headless` | hand off to `../../trtc-topic/SKILL.md` (Read) with headless spec |

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
   - `${CLAUDE_PLUGIN_ROOT}/skills/trtc-onboarding/reference/mcp-usersig-generation.md` — UserSig credential protocol

2. **Generate the project files in one shot:**
   - Login page (collect/pre-fill sdkAppId, userId, userSig per the MCP protocol)
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

5. **Do NOT:**
   - Read any other slice file (room-lifecycle.md, device-control.md, etc.)
   - Hand off to `../../trtc-topic/SKILL.md`
   - Run the state machine (init_slice_queue, next_slice, etc.)
   - Run `trtc_prepare_ui.py` or `trtc_verify_ui.py`
   - Ask A2-Q0.6 (auto-advance policy) — irrelevant without a slice loop

### If `ui_mode = headless` (topic path — state machine)

1. **Handoff to `../../trtc-topic/SKILL.md` via Read.** Read `${CLAUDE_PLUGIN_ROOT}/skills/trtc-topic/SKILL.md` and execute its flow. (Plain Read is the current handoff convention — the §3.5 cross-skill `Skill()` tool handoff was walked back. The real constraints that prevent topic from being silently bypassed live in PreToolUse / Stop hooks and the on-disk state machine, not in how SKILL.md is loaded — so plain Read is sufficient.)

   Scenario-driven step-by-step execution (reading the scenario file, walking the ordered slice list, loading per-step slices, pausing between steps, verification checklist) is topic's responsibility, not onboarding's. Onboarding A2 owns intent identification and scenario selection; once a scenario is picked, topic owns the drive.
2. Pass the scenario id and the current `session_context` (product, platform, credentials if collected, `target_features`, `project_state`) to topic as inputs. Topic will read `${CLAUDE_PLUGIN_ROOT}/${CLAUDE_PLUGIN_ROOT}/knowledge-base/{scenario.file}` itself.
3. Save `session_context.current_step = 'topic-handoff'` and `session_context.scenario = <chosen-id>` so if the user later returns mid-flow, routing can resume topic from where it paused.
4. Do NOT run A2-Q1 (module selection) or A2-Q3 (per-step execution) for scenario-driven flows — those paths are for `intent = integrate-feature` only.

Scenario-driven UI presets, default layouts, and scenario-specific A2-Q4 tweaks are not onboarding's concern after handoff — topic handles them (or defers UI adjustments back to the user as a follow-up).

If the chosen scenario has `status: planned` in the index: tell the user (in their own language) that the detailed playbook for this scenario is still being written, and offer two options — (a) fall through to A2-Q1 for manual module selection, or (b) let onboarding/topic compose the flow on-the-fly from the available slices. Do NOT silently Read `../../trtc-topic/SKILL.md` in this case; topic needs a concrete scenario file to drive its walk-through.

## A2-Q0.6 — Auto-advance policy (scenario-driven flows only)

**Trigger**: the user picked any scenario in A2-Q0 (i.e. `intent = integrate-scenario`).
Skip for `integrate-feature` flows.

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

Question text: "Which modules do you want to integrate? (multi-select; login is required as the foundation)"

Options are **product-dependent**. Pull from `${CLAUDE_PLUGIN_ROOT}/knowledge-base/index.yaml` slices filtered by product. Example for `product = live`:

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

## A2-Q2 — Credentials

**Before showing the manual credential prompt**, run the MCP credential detection
protocol: Read `reference/mcp-credential-detection.md` and follow its Steps 1–4.
If MCP detection succeeds (user confirms the detected credentials), skip the
manual prompt below and proceed directly to A2-Q3. Only fall through to the
A1-Q1 format if MCP detection does not apply (Step 4 Fallback).

Reuse A1-Q1 format (see `reference/path-a1-demo.md`) as the manual fallback. Skip entirely if `credentials.sdk_app_id_provided` and `credentials.secret_key_provided` are both `true` in the session file.

**Important**: the actual SDKAppID / SecretKey values are **never** written to `${CLAUDE_PROJECT_DIR}/.trtc-session.yaml`. After the user pastes them (or confirms MCP-detected values), hold them in conversation context only. Update the session file's `credentials.sdk_app_id_provided` / `credentials.secret_key_provided` booleans to `true` — and persist those booleans as part of the next Checkpoint write (do not trigger an extra Write just for credentials).

## A2-Q3 — Per-step progression

### Login step enhancement (MCP-aware)

When the current step's slice is `{product}/login-auth` (or any slice whose
implementation involves `login()` / `LoginStore` / TIM login / TRTC
`enterRoom` authentication):

**⚠️ BLOCKING GATE — 必须在生成任何登录代码之前完成：**

1. Read `reference/mcp-usersig-generation.md` and follow its Generation Protocol.
2. Determine the UserSig 来源：MCP available → call `get_usersig`；MCP unavailable → use placeholders.
3. **If this protocol is not followed, the generated login code MUST NOT be written to disk.**

This gate ensures:
- A real, working test userSig is embedded for immediate testing (if MCP available)
- Input fields remain available for custom userID/userSig at runtime
- The generated login page works out-of-the-box without manual credential setup
- **No client-side signing code is ever generated** (no `crypto-js`, no `pako`, no `SecretKey` in source)

If MCP is not available, follow the Fallback section in `mcp-usersig-generation.md`
(placeholders + instruction comments).

**Violation self-check (same weight as apply gate):** If your about-to-write login
code contains `HmacSHA256`, `crypto-js`, `pako`, `SecretKey` in a non-comment
assignment, `generateUserSig`, or creates a file matching `**/usersig.*` — you
are violating this gate. STOP, discard, re-read `reference/mcp-usersig-generation.md`,
and regenerate.

### Per-step execution

After writing code for each step, call `../../trtc-apply/SKILL.md` as described in **"Calling apply"** above. Only report the step done after `response.status` is `pass` (or `partial` with no `critical` severity issues). Summarize the outcome to the user using this template:

```
Step {n} ({slice name}) done.
Changes: {N files added, M files modified}. Did not touch {AppDelegate.swift / main.ts / etc.}.
Compile check: passed — `{compile_command}` exit 0.
```

**Persist session state** (see `SKILL.md` § Session context → Checkpoints). After a step passes apply:
- Set `current_step` to the next step's id (e.g. from `A2.3` to `A2.4`)
- Append the just-completed slice id to `completed_steps`
- Update `updated_at` timestamp
- Write to `${CLAUDE_PROJECT_DIR}/.trtc-session.yaml`

**First Write of the session** (i.e. right after Stage 1 calibration confirmed, before this step executes): create the file with `status: active`, all inferred fields filled, and trigger the `.gitignore` auto-update flow described in `SKILL.md` § Session context.

If apply returns `fail`, do NOT write this summary **and do NOT advance `current_step` in the session file**. Follow the retry rules in **"Calling apply → Acting on retry_hint"** (max 2 apply calls per step). If the step ultimately gives up, surface a message framed as "I hit a snag on step {n}" — never "apply skill said X" — and list what was tried.

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
| 2 | Fine-tune the UI (theme / layout) | go to A2-Q4-UI (controlled-adjustment sub-flow); session `status` stays `active` |
| 3 | I'm good for now | set `status: completed`, Write session, end onboarding cleanly |
| 4 | Type something | free-text |

Option 2 is only shown when `product = conference` AND `ui_mode = full-ui`.
Headless integrations have no generated UI for onboarding to fine-tune —
the user edits their own UI directly. For any other product / mode, hide
option 2 entirely.

### A2-Q4-UI — Controlled UI adjustment sub-flow

**Triggered when**: A2-Q4 option 2. Runs AFTER a full integration has passed
apply and `ui_mode = full-ui`. Intent: let users fine-tune the UI without
breaking the business logic or SDK contract.

**Core principle**: every adjustment belongs to a declared *class* with
explicit scope and forbidden operations. No free-form UI editing — the user
picks a class, AI operates within that class's boundaries.

Question text: "What aspect do you want to adjust?"

| # | Class | Scope | Risk |
|---|---|---|---|
| 1 | Theme tokens | `overrides.css` only (brand color, radius, font, dark mode) | Low |
| 2 | Layout | `layout.css` only (panel / toolbar positions) | Medium |
| 3 | I need something else | Free-text; AI classifies and re-routes, or declines if it doesn't fit class 1 / 2 | — |
| 4 | Done | Return to A2-Q4 | — |

Replacing a single generated element with a user-provided component is
deliberately NOT offered in this release — see pending_todos for the plan.

#### Class 1: Theme tokens (safe path)

**Allowed**:
- Run `../../trtc/room-builder/uikit/scripts/generate-theme-overrides.py` with user-specified flags
- Create or update `overrides.css` in the user's project

**Forbidden**:
- Editing any `.vue` file
- Editing `uikit/components/*.css`
- Adding inline `style` attributes in generated code

**Flow**: ask the user which tokens to change (primary color / radius scale /
font family / dark mode). Compose the script invocation, run it, report the
diff of `overrides.css`. Call apply with `mode: quick`. Fail the adjustment
if apply detects any `.vue` file changed or any hardcoded color appears in
the diff.

**After success**: set `ui_customizations.theme_overridden = true`. Persist
at the next checkpoint write.

#### Class 2: Layout (medium path)

**Allowed**:
- Modifying `layout.css` (grid-area, side-panel position, toolbar slot positions)
- Renaming slot positions in the template, as long as the slot name is preserved

**Forbidden**:
- Changing any class name in `<template>` except grid-area classes
- Removing or modifying any node with `v-for` / `@click` / `:class` / `v-model`
- Editing `<script setup>`
- Changing `import` statements

**Flow**: ask the user the layout change (e.g. "move members panel to the left",
"put toolbar at the top"). Generate the edits to `layout.css`. Call apply with
`mode: full`. Required diff checks:
1. All original `v-*` directives and event bindings must be preserved
2. All composable imports must be unchanged
3. Any diff that modifies a reactive binding → rejected with a clear explanation
   ("layout adjustment cannot change business bindings; if you want to replace
   an element, that requires a different flow that is not available yet.")

**After success**: set `ui_customizations.layout_modified = true`. Persist
at the next checkpoint write.

#### Class 3: Free-text fallback

When the user picks option 3 or free-texts a request:
- Matches class 1 intent (colors / radius / font / dark mode) → route to class 1
- Matches class 2 intent (panel position / layout) → route to class 2
- Requests replacing an element with a custom component → decline with: "Custom
  component replacement is not available in this release — it requires additional
  safety checks for RTC mount points and reactive bindings that we're still
  building. You can manually edit the files if needed; the generated code is
  under `src/trtc/views/` and the composables are under `src/trtc/composables/`."
- Any other request → decline politely, restate classes 1 and 2.

Never perform free-form UI edits. The two classes above are the only sanctioned
operations.

#### Loop

After each successful adjustment, ask: "Apply and continue, or adjust more?" —
re-show A2-Q4-UI options if the user wants more, otherwise return to A2-Q4.
