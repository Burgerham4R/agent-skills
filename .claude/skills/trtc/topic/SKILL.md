---
name: trtc-topic
description: >
  Guide users step-by-step through complete TRTC integration scenarios. Use this
  skill when the user wants to implement a full feature end-to-end — like "I want
  to build a 1v1 video call", "guide me through multi-device login setup",
  "help me implement live streaming", or "I need to add chat to my app". Also
  trigger when the user says "walk me through", "step by step", "how do I build",
  or describes a complete use case rather than asking about a single API. This skill
  loads scenario files that define the sequence of slices to implement and guides
  the user through each step with code examples and verification checkpoints.
---

# TRTC Scenario Guide

You guide users through complete integration scenarios step by step. Each scenario is a sequence of atomic capabilities (slices) that together form a working feature.

Think of yourself as a pair programmer who knows TRTC well. You don't dump everything at once — you walk through one step at a time, give the user code they can try, and check in before moving on.

## Entry points

This skill is reached two ways. Both produce the same in-skill flow once a scenario id is resolved.

1. **Handoff from `onboarding/SKILL.md` Path A2-Q0** — the normal path. Onboarding has already identified `product`, `platform`, `intent = integrate-scenario`, and a concrete `scenario` id from the user's choice in A2-Q0, plus any collected `credentials`, `target_features`, and `project_state`. These are passed via `.trtc-session.yaml` (read it at skill entry) and should be treated as known — do NOT re-ask. Skip Step 1's "match request to scenario" — the scenario is already chosen; go directly to reading `knowledge-base/{scenario.file}`.
2. **Direct routing from the root skill** — when the user arrives with a clear scenario request ("walk me through a 1v1 video call", "step by step multi-device login") and no onboarding session is mid-flight. Run Step 1 to match the request to a scenario.

When a scenario picked by onboarding has `status: planned`, onboarding will have already kept the user in A2-Q1 fall-through; this skill only receives handoffs for scenarios that have written files.

## Guided workflow

### Step 1: Find the right scenario

**Skip this step if onboarding already handed off a concrete `session_context.scenario`** — read the scenario file directly.

Otherwise, read `knowledge-base/index.yaml` and look at the `scenarios` section. Match the user's request to a scenario by its `name`, `description`, and `slices` list.

If a scenario matches, read its file: `knowledge-base/{scenario.file}`. This contains:
- Prerequisites the user needs to have in place
- Ordered implementation steps, each referencing a slice
- A verification checklist at the end

If no scenario matches exactly, compose an ad-hoc sequence from relevant slices. Tell the user (in their own language) that there isn't a pre-built guide for this exact scenario but you can walk them through it with a set of building blocks, list the slice names, and ask whether to proceed.

### Step 1.5: Present scenario capabilities (and pick coverage if applicable)

**MANDATORY before any code is written** (including before any Step 3.5 `ui_mode` work). This step runs even when onboarding handed off a concrete scenario — the Step 1 skip applies only to *scenario matching*, not to capability presentation.

Each scenario file declares its own format. Open `knowledge-base/{scenario.file}` and follow its **「能力展示」** (form A) or **「能力展示与 coverage 选择」** (form B) section verbatim. See `knowledge-base/scenario-spec.md` for the two forms.

- **Form A (single complete capability set)**: render the file's "展示文案" to the user, then proceed to Step 2. Do NOT ask the user any coverage question — every slice in the scenario will be implemented.
- **Form B (主链路 + 可选增强)**: render the file's "展示文案", then use `AskUserQuestion` per the file's "AskUserQuestion 选项" table. Persist the user's pick to `.trtc-session.yaml`:
  ```yaml
  session_context:
    enhancement_level: minimal | complete   # minimal = P0 only; complete = P0 + P1
  ```

If the scenario file does not provide either section, fall back to: list every entry in its `index.yaml` `slices` array as one tier, ask "继续？" (yes/no), and treat it as form A with all slices included. Then file an issue against the scenario authoring spec.

**Skip Step 1.5 only if** the user explicitly said "完整版 / give me everything / all features" in their initial request — set `enhancement_level: complete` silently and continue. Do **not** skip just because onboarding handed off a scenario id; onboarding does not own this question.

`enhancement_level` is the contract for downstream steps — see Step 3 and Step 3.5. Form A scenarios may treat the field as `complete` by default since there is no "minimal" subset.



### Step 2: Check prerequisites

Present the scenario's prerequisites to the user. These are things like console configuration, SDK version requirements, or account setup that must be done before writing code.

Ask the user to confirm they're ready before diving into implementation. This prevents frustrating "it doesn't work" moments that are actually config issues.

### Step 3: Walk through each step

**Slice sequence depends on the scenario's form (see Step 1.5):**

- **Form A scenarios**: walk every slice the scenario file lists (in document order).
- **Form B scenarios**: walk slices filtered by `session_context.enhancement_level` — `minimal` = P0 only, `complete` = P0 + P1.

If `enhancement_level` is unset on a Form B scenario, you skipped Step 1.5 illegally. STOP and run Step 1.5 first. Silent skipping is forbidden.

For each step in the (filtered) scenario sequence:

1. **Explain what this step does and why** — one or two sentences of context
2. **Load the relevant slice**:
   - Read the product-level overview for the conceptual foundation
   - Read the platform-specific file for the actual code
3. **Present the code** — give a complete, runnable example for the user's platform. Include inline comments for anything non-obvious.

   **Code generation rules (MANDATORY for all code you produce):**

   - **G1: Copy from slices, don't improvise** — Always read the platform-specific slice file first and use its code examples as the foundation. Copy import statements, API signatures, and type annotations verbatim from the slice. Do NOT substitute SDK names or parameter types from memory.
   - **G2: No invented APIs** — Every class, method, property, and enum case you reference must either (a) come from the knowledge base slice, or (b) be standard platform API you're certain exists. When unsure, use a simpler but definitely-correct approach rather than guessing.
   - **G3: Self-validate before presenting** — Before showing or writing code, call `apply/SKILL.md` per the contract described in **"Calling apply"** below. Snippet-only answers can use `mode: quick` (5-point checklist). Code that will be written into the user's project MUST go through `mode: full` (constraint compliance → compilation → integration safety).
   - **G4: Modular structure** — Break implementations into separate files with clear single responsibilities. Don't put all logic into one massive file. Each file should be focused and manageable.
   - **G5: Compilable by default** — Generated code must be compilable when added to a project with the correct SDK installed. Include all necessary imports, type declarations, and protocol conformances. If something can't compile without additional context, note it with a `// TODO:` comment explaining what's needed.

4. **Highlight the gotchas** — surface the ALWAYS/NEVER rules that apply to this step. Frame them as "the common mistakes I've seen" rather than abstract rules.
5. **Auto-advance or pause** — follow the **Step 3 progression rules** below to decide whether to immediately continue to the next step or pause for user input.

### Step 3 progression rules

After each step's apply check completes, use the following rules to decide whether to auto-advance or pause:

| apply result | Action |
|---|---|
| `pass` | **Auto-advance.** Do NOT pause or ask the user. Immediately proceed to the next slice in the scenario sequence. Output the step's **Apply Evidence Block** (see below) and continue generating the next step's code in the same response. |
| `partial` (only `warning`/`info` severity) | **Auto-advance with note.** Same as `pass`, but append warnings after the evidence block. Continue to the next step. |
| `partial` (any `critical` severity) | **Pause.** Show the critical warnings and ask the user how to proceed (fix / skip / pause). |
| `fail` | **Pause.** Follow the retry rules in "Calling apply". If retry also fails (give-up), pause and inform the user. |

**Apply Evidence Block (MANDATORY for every step — no exceptions, even with auto-advance):**

Every step that passes apply MUST include the following visible block in the response. This is NOT optional. A step without this block is NOT completed, regardless of what the AI claims.

```
### Step {n}: {slice_name} ✅

**P1 Imports:** `{actual grep command executed}` → {result}
**P3 API check:** `{actual grep command executed}` → {result}
**P4 MUST rules:** {count} checked, {count} passed
**Compile:** `{actual compile command}` → exit {code}
```

**What each line requires (minimum viable evidence):**

| Line | What must actually happen | Fake = violation |
|---|---|---|
| P1 Imports | Execute `grep` or `ls` against `node_modules/` to confirm the import path resolves | Saying "import path is correct" without a command |
| P3 API check | Execute `grep` against SDK `.d.ts` or slice file to confirm at least the primary API exists (e.g. `useLoginState`) | Saying "API exists" from memory |
| P4 MUST rules | Read the slice's MUST rules, then `grep` the generated file for each required pattern; report count | Saying "all MUST rules satisfied" without grep |
| Compile | Execute the actual build command (`npx webpack --mode production` or equivalent) and show exit code | Not running the command |

**Minimum execution standard:**
- P1: At least 1 actual `grep` or `ls` command against `node_modules/` executed via Bash tool
- P3: At least 1 actual `grep` command against `.d.ts` or slice file executed via Bash tool
- P4: At least 1 actual `grep` command against the generated code file executed via Bash tool, checking for a pattern from the slice's MUST rules
- Compile: Actual `webpack` or `tsc` command executed via Bash tool

**If any Bash command cannot be executed** (no node_modules, no project): mark the line as `⚠️ NOT VERIFIED` instead of ✅. Never fake a ✅.

**Why this matters:** The Apply Evidence Block is the only proof that verification actually happened. Without executed commands and real output, "apply pass" is meaningless text. The user cannot distinguish real verification from hallucinated verification unless they see actual command → output pairs.

**Batch output for consecutive passes:** When multiple steps pass in sequence, each step still outputs its own Apply Evidence Block. They may appear consecutively in one response, but none may be omitted.

**Completion summary:** After all steps have auto-advanced through `pass`, present a single final summary table showing all steps, their apply status, and the overall compile result. This replaces the per-step "What would you like to do next?" menu.

**Override:** If the user explicitly asks to go step-by-step ("一步一步来", "pause between steps", "let me review each step"), respect that preference and pause after each `pass`. Otherwise, auto-advance is the default.

### Step 3.5: Apply `ui_mode` to code generation

When `.trtc-session.yaml` has `ui_mode` set (any product), the code-generation
strategy branches. Read this state ONCE at skill entry and cache it for the
whole session. This section applies to **any product** that has a reference HTML
and composable-bindings mapping — it is not limited to Conference.

**At skill entry, if `ui_mode = full-ui`, load these three files as spec input:**

1. `.claude/skills/trtc/room-builder/references/scenario-mapping.md` — maps the
   current scenario to a scene and a reference HTML file
2. `.claude/skills/trtc/room-builder/references/composable-bindings.md` — maps
   UIKit class names to composables and reactive Vue bindings
3. The reference HTML file named in scenario-mapping.md — used as visual spec
   (structure, class names, slot layout)

**If any of these files does not exist or has no entry for the current product/scenario:** degrade to `ui_mode = null` behavior for this run and warn the user (in their language): "I don't have a UI template for this scenario yet — I'll generate business code and you can apply your own UI layer."

**Pre-generation: UI-region-to-slice binding audit (MANDATORY for `full-ui`)**

Read the scenario file's **「UI 区域 / Slice 映射」** table (see `scenario-spec.md` §3.4). That table — authored per scenario — is the contract for which UI regions get wired vs hidden.

For each row in the table:

- **Form A scenario** (single column "对应 slice"): wire the slice per `composable-bindings.md`. If the slice has no composable-bindings entry, **block** — update `composable-bindings.md` first, then implement. Do not stub.
- **Form B scenario** (two columns "minimal" / "complete"): pick the column matching `session_context.enhancement_level`. The cell tells you literally what to do:
  - "显示" → wire the slice per `composable-bindings.md` (block on missing entry, same as form A).
  - "隐藏" → remove the element from `<template>`, OR keep with `v-if="false"` plus a comment naming the unselected slice. Do NOT render an inert button — that produces the "click does nothing" bug.

If the scenario file has no UI mapping table but the scenario is in `scenario-mapping.md` (i.e. has reference HTML), block and tell the user the scenario authoring is incomplete; do NOT improvise the mapping yourself. The mapping table is per-scenario judgement, not topic's.

Record the audit result as an inline comment at the top of the generated SFC, listing which slices were bound and which regions were hidden.

**Generation rules by mode:**

| `ui_mode` | Output shape | Strategy |
|---|---|---|
| `full-ui` | Vue SFC (template + script + style) | Run the UI-region-to-slice binding audit above first. Then mirror the reference HTML structure in `<template>`. Class names MUST come from the reference HTML or `uikit/references/component-catalog.md` — do NOT invent new class names. Replace static state classes (`.is-off`, `.is-open`) with reactive `:class` bindings per composable-bindings.md. Wire buttons with `@click` and lists with `v-for` against the mapped composables. In `<style>`, import the theme tokens and component CSS from the path specified in scenario-mapping.md. |
| `headless` | Composables + stores + types + README | Generate `src/trtc/composables/*.ts`, `src/trtc/types/index.ts`, and a top-level `README.md`. Do NOT generate any `.vue` files. Do NOT generate example components. The README documents each composable's return signature with a 3-line usage snippet. |
| `null` or unset | Topic's default strategy | Fall back to the per-slice code-example approach (pre-ui_mode behavior). Unchanged. |

**What "mirror" means concretely:**
- Copy the reference HTML's DOM hierarchy for each region (topbar, stage, bottombar, side-panel).
- Keep the original class names, slot structure, and nesting depth.
- Replace hardcoded data (names, avatars, messages) with `v-for` / `{{ }}` bindings.
- Replace static state classes with `:class` bindings per composable-bindings.md.
- Add `@click` handlers per composable-bindings.md.
- Do NOT restructure the HTML to "look simpler" or "be more readable" — the reference HTML IS the spec.

**If the reference HTML is too large for a single SFC:** split into multiple child components by region (e.g. `TopBar.vue`, `BottomBar.vue`, `SidePanel.vue`), but each child component still mirrors the corresponding section of the reference HTML with original class names intact.

**Apply gate — MANDATORY for `full-ui` (same weight as G3, not optional):**

After generating the complete SFC — **before writing any file to disk** — call
`apply/SKILL.md`. `full-ui` mode generates composite code covering multiple
slices at once; construct the apply request as follows:

```yaml
request:
  code:
    - path: {relative path, e.g. src/views/MeetingRoom.vue}
      content: {the full generated SFC}

  product:    {product from session, e.g. conference / live / call}
  platform:   {user's platform}
  capability: {first slice in the scenario sequence, e.g. "{product}/room-lifecycle"}

  related_capabilities:
    # list ALL other slices whose rules must be checked in this SFC:
    # (pull from the scenario's slice sequence in knowledge-base/{scenario.file})
    - {product}/login-auth
    - {product}/device-control
    - {product}/participant-list
    - {product}/room-chat
    # ... include every slice from the scenario's slice sequence

  project_context:
    root:              {absolute path if scanning available}
    modified_files:    [{generated SFC path}]
    has_existing_tests: false

  mode: full        # if project_context.root is set
        # static-only  # if no project root available
```

`related_capabilities` is how apply handles multi-slice composite code — it
runs Phase 2 constraint checks for every listed slice, not just `capability`.
This covers the full MUST/MUST NOT surface of a `full-ui` SFC.

**On apply response:**
- `pass` → write the file; continue normally.
- `partial` (only `warning`/`info`) → write the file; note warnings inline.
- `fail` → **do NOT write the file**. Follow the retry rules in "Calling apply"
  (max 2 attempts). If give-up: surface "I hit a snag generating the SFC" to
  the user; offer to regenerate or pause.

**If apply is skipped for ANY reason** (context overflow, tool unavailability,
missing project root when `mode: full` was required): the generated SFC MUST
include the following comment at the very top of `<script setup>` before being
written, and the step summary MUST include `⚠️ 编译未验证 — apply 未执行，请手动编译确认`:

```ts
// ⚠️ APPLY VERIFICATION SKIPPED — compile and verify manually before shipping
```

Never declare the full-ui SFC step done without either (a) apply `pass`/`partial`
evidence, or (b) the skip-disclosure comment visibly in the file.

**Internal asset policy:** `scenario-mapping.md` and `composable-bindings.md`
are read-only references. Topic does not write to room-builder. The user never
sees these files — they are internal generation spec.

**Respecting user UI customizations**: also read `ui_customizations` from the
session. If `layout_modified = true`, do not regenerate `layout.css` in
subsequent feature additions. If `theme_overridden = true`, do not regenerate
`overrides.css`. Preserve what the user has manually tuned.

**Fallback when `ui_mode = full-ui` has no mapping entry for the current
scenario:** degrade to `ui_mode = null` behavior for this run and warn the
user (in their language): "I don't have a UI template for this scenario yet —
I'll generate business code and you can apply your own UI layer."

The scenario file may reference slices with `status: planned`. When you hit one of these:
- Explain what this step conceptually does (from the index description)
- Give your best guidance based on the scenario file's description of the step
- Link to official docs if available
- Note that detailed guidance for this step is coming soon

### Step 4: Verify

After all steps are done, present the scenario's verification checklist. Walk through each item:

```markdown
## Verification Checklist

Let's make sure everything works:

- [ ] **Multi-device login works** — Log in from two devices. Both should stay online and receive messages.
- [ ] **Kick-offline handling** — Log in from enough devices to exceed the limit. The oldest session should get the onKickedOffline callback and show a dialog.
- [ ] **UserSig renewal** — Wait for UserSig to expire (or use a short-lived one for testing). The app should auto-renew without user intervention.
- [ ] **Page refresh recovery** (Web only) — Refresh the page. The app should automatically re-initialize and re-login.

Having trouble with any of these? Tell me which one fails and I'll help debug.
```

### Debugging during the guide

If the user hits a problem mid-scenario:
1. Don't abandon the step sequence — note where you paused
2. Load the relevant slice's troubleshooting section
3. Walk through the diagnostic flow from the troubleshooting tree
4. Once resolved, resume where you left off: "Great, that's fixed. Back to step N..."

### Calling apply (internal quality gate)

apply is invoked per step, not per file and not per session. It follows the I/O contract defined in `apply/SKILL.md` Phase 0. Construct each call explicitly — do not dump raw code and hope apply infers context.

**Request construction** (build before calling apply):

```yaml
request:
  code:
    - path: {relative path under project root}
      content: {full file content after this step's edits}
    # include every file this step created or modified

  product:     {scenario.product, e.g. live / conference / chat / call / rtc-engine}
  platform:    {user's platform}
  capability:  {slice_id of the current step, e.g. "live/coguest-apply"}

  project_context:
    root:              {absolute path if file scanning is available}
    modified_files:    {paths touched by this step}
    has_existing_tests: {true if the project has a test command configured, else false}

  related_capabilities:
    # list prerequisite slices so apply can verify cross-slice prerequisites
    # without re-inferring from code
    - {e.g. live/login-auth if this step needs login}
    - {e.g. the slice immediately before this one in the scenario sequence}

  mode: full | quick | static-only
```

**Mode selection rules:**

| Situation | mode |
|-----------|------|
| Code will be written into the user's project (Step 3 compile gate) | `full` |
| Snippet-only answer (user just wants to see code, not integrate it) | `quick` |
| No project scanning / no build env available | `static-only` |

**Response handling:**

| response.status | What to do |
|-----------------|------------|
| `pass` | Mark the step as done. In the step summary, include the compile command + exit code from `response.compile_check` as proof. Do not expose raw constraint-check details unless the user asks. |
| `partial` | Step done with non-blocking warnings. Note them in a single collapsed line, keep moving. Do NOT treat a `partial` with only `warning`/`info` severity as a blocker. |
| `fail` | Step NOT done. Do not present the code as if it works. Follow `response.retry_hint.strategy` below. |

**Acting on `retry_hint` when `status = fail`:**

| retry_hint.strategy | Action |
|---------------------|--------|
| `patch` | Apply the specific fixes from `response.constraint_check.issues[*].fix.code_diff`, re-call apply **once** with the updated code. |
| `regenerate` | Regenerate the step's code from scratch, guided by `retry_hint.focus_on`. Re-read the slice if needed (don't regenerate from memory). Call apply again. |
| `give-up` | Stop retrying. Tell the user "I hit a snag on step N, here's what I tried: ..." — never "apply skill said X". Offer three options: skip this step, pause the scenario, or provide more context. |
| `missing-field` | **Do NOT retry.** This signals the caller (topic skill itself) built a malformed request — typically forgot `capability`, `product`, or `platform`. The missing field names are listed in `retry_hint.focus_on`. Treat as a self-bug: tell the user "I hit an internal snag on step N" and offer to skip this step. Do not regenerate code — the code is not the problem. |

**Retry budget:** at most **2 apply calls per step**. Matches apply's own compile retry budget (Phase 3.2). If the second call returns `fail` with the **same `failure_signature`** as the first, treat it as `give-up` even if `retry_hint` says otherwise — the second call has proven that the current patch/regenerate strategy isn't converging.

**Planned-status slices:** if the current step references a slice with `status: planned`, apply's `capability` field still uses that slice id. apply will return `warning: slice_not_available` and fall back to compile-only verification. Topic skill should present the code with an extra note: "This step uses a slice still being documented — I verified it compiles, but the slice-level rules couldn't be checked."

**Never:**
- Never tell the user "I'm calling apply" or "apply says X". apply is silent infrastructure.
- Never show raw `request` / `response` yaml. Translate to the step summary template.
- Never skip apply to "move faster". A step without compile evidence is not a completed step.

### Adapting the pace

Pay attention to the user's experience level:
- **Experienced developers** who just need the TRTC-specific parts: focus on API calls, gotchas, and error handling. Skip general concepts.
- **Newer developers** who need more context: explain the underlying concepts from the product overview, give more complete code with surrounding context, and be more explicit about each step.

You can calibrate by how they respond to the first step.
