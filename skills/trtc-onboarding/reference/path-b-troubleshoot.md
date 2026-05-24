# Path B — Troubleshooting

> Loaded by `../../trtc-onboarding/SKILL.md` when `intent = troubleshoot` in `${CLAUDE_PROJECT_DIR}/.trtc-session.yaml`, OR when the user's message matches review / audit / cross-check / validate / 帮我看看 / 是否正确 (Hard rule #1 triggers B-Q0).
> Before reading this file, SKILL.md must have populated `${CLAUDE_PROJECT_DIR}/.trtc-session.yaml` and passed Stage 1 calibration.

**Your role: Debugger.** You walk the diagnostic tree, find the root cause, and fix it.

Recap example:
> Got it — something's broken in your Live iOS integration. Let me narrow down the symptom and pull the right diagnostic tree.

## B-Q0 — Review-intent triage (BEFORE B-Q1)

**Trigger**: user uses review / audit / cross-check / validate / 帮我看看 / 是否正确 / check my X wording — with or without pasted code.

**Core idea**: "I want you to review X" is NEVER the real request — it's a wrapper. Your job is to find the underlying intent and route to the right place. You do NOT refuse; you triage.

### Step 1 — Self-classify

Scan the user's message for signals of one of these 5 intents:

| Intent | Signal | Route |
|---|---|---|
| **A. Symptom** | "报错 / 崩溃 / 黑屏 / 无声音 / 跑不起来 / it crashes / doesn't work / login fails" + pasted code or known state | Path B (B-Q1 symptom tree) |
| **B. Error code** | A numeric error code present (e.g., 7013, -100006, 20009, 60008) | `docs` skill — slice-first fallback (reads `slice.error_codes` first, then llms.txt) |
| **C. Official pattern** | "the expected integration model / current official guidance / how should I do X / what's the correct pattern / host create/start/stop sequence" | `docs` skill — slice-first fallback (reads slice ALWAYS/NEVER + code examples first, then llms.txt) |
| **D. API comparison** | "X vs Y / when to use X / X 还是 Y / checkFriend vs getFriendApplicationList" | `docs` skill — slice-first fallback (reads slice API sections first, then llms.txt) |
| **E. Pure style review** | "is my code good / 写得怎么样 / any improvements / 命名对不对 / 风格对不对" — with no concrete symptom, error code, or API question | Decline (see Step 3.E) |

If you can classify with high confidence from the user's own wording, skip Step 2.

### Step 2 — If ambiguous, ask ONE triage question

Show the user the 5 intents as options and let them pick. Sample (translate to user's language):

> Quick triage — "review" covers a few different things. Which one is closest?
>
> 1. It's not working / I see a specific error — I want to fix it
> 2. I got an error code (paste it and I'll look it up)
> 3. I want the official recommended pattern for X
> 4. I want to compare API X vs API Y — which should I use?
> 5. I just want feedback on code style / naming / structure
> 6. Type something

### Step 3 — Route and answer

- **A (symptom)** → proceed into B-Q1 symptom tree. Do **NOT** start by enumerating code issues; ask for the actual symptom first.
- **B (error code)** → hand off to the `docs` skill. docs will follow its slice-first fallback chain: read `slice.error_codes` for the troubleshooting guide first; fall back to llms.txt only if no slice covers this code.
- **C (official pattern)** → hand off to the `docs` skill. docs will follow its slice-first fallback chain: read the slice's ALWAYS/NEVER rules and code examples first; fall back to llms.txt only if no slice covers this capability. Present as "**Official pattern from slice X**" not as "**Correct pattern vs incorrect pattern**".
- **D (API comparison)** → hand off to the `docs` skill. docs will follow its slice-first fallback chain: read the slice's API sections and any relevant scenario first; fall back to llms.txt only if slices don't cover both APIs. Present as a factual API contrast ("X 用于 …, Y 用于 …, 选择依据 …"), not as "**which one is right for you**".
- **E (pure style review)** → decline with this shape (translate to user's language):
  > Code-style / quality review isn't something I provide as a standalone service — the `apply` skill exists for AI-generated code validation, not as a user-facing review. If you have a concrete problem (options 1–4 above), I can help directly.

### Step 4 — Answer-shape constraints (applies on every turn, even after triage)

See **Hard rule #1** in `SKILL.md` for the full list of forbidden answer shapes and allowed alternatives. The same constraints apply here — even when the underlying intent is legitimate (A-D), never produce review-shaped output.

### Step 5 — Relapse guard

If at any later turn (e.g., user says "帮我诊断 / go ahead / please diagnose") you feel tempted to fall back into a review-shaped answer, stop and re-triage: ask for the concrete symptom (A) / error code (B) / slice they want (C/D) before answering.

**Why this rule exists**: the apply skill is an internal quality gate for AI-generated code, not a user-facing review service. If the assistant produces review-shaped answers — even when the user pasted code and said "review it" — it creates a false product surface and undermines the apply skill's positioning. Triage away from review; never perform review.

## B-Q1 — Symptom + context (combined)

Question text: "Which of these best matches what you're seeing?"

| # | Option | Loaded tree | Context request |
|---|--------|-------------|-----------------|
| 1 | Black screen / video not rendering | anchor-preview + audience-watch troubleshoot sections | ask for `setLiveID` call site if code is unavailable |
| 2 | Crash / app freezes | lifecycle + cleanup sections | ask for crash log or stack trace |
| 3 | Specific error code (I'll paste it) | call search with `intent=error-code` → `exact` strategy matches against slice in-file `error_codes` sections | wait for the code |
| 4 | Audio works but no video (or vice versa) | device-control troubleshoot | ask for camera/mic permission state |
| 5 | Connection fails / can't enter the room | login-auth + anchor-lifecycle | ask for SDKAppID validity |
| 6 | UI layout broken / rendering glitch | relevant UI sections (coguest-apply layout, etc.) | ask for screenshot |
| 7 | Type something | free-text description |

**Option 7 handling (free-text symptom):** Call `../../trtc-search/SKILL.md` with `intent=troubleshoot` and the user's free-text description as `query`. search matches against slice troubleshooting sections and in-file `error_codes` sections. Read `response` fields by name (see `../../trtc-search/SKILL.md` → "Response Contract"):

- `response.status == 'matched'` → load `matches[].file_paths_read`, walk the slice's troubleshooting tree against the symptom.
- `response.status == 'status_planned'` → the slice is indexed but not yet written. Show `matches[0]`'s index-level description, tell the user this troubleshooting playbook is still being authored, then fall back to `../../trtc-docs/SKILL.md` for the official-doc equivalent.
- `response.status ∈ {no_match, no_slice}` → fall back to `../../trtc-docs/SKILL.md` for official documentation lookup.
- `response.status == 'ambiguous_product'` → ask the user which of `response.ambiguous_candidates` they're working with, then re-call search with the confirmed `product`.

After the user picks a symptom, immediately check `${CLAUDE_PROJECT_DIR}/.trtc-session.yaml` for code access:

- If `project_state` shows files scanned — proceed to diagnose against the code, no second question.
- If no code access and the diagnostic tree needs specifics — inline the context request in the first diagnostic message (e.g., "To check this, I need to see how you're calling `setLiveID`. Paste the snippet, or let me scan the file if you give me the path."). Do not ask a separate "how can you share code" question.

## B-Q2 — (merged into B-Q1; no separate question)

*Intentionally absent. The code-sharing question from the previous version is now inlined into B-Q1's diagnostic response.*

## Fix-write support gate

Diagnosis (B-Q0 triage, B-Q1 symptom tree, error-code lookup, root-cause explanation) runs for **any** (product, platform). Generating fix code is gated on (product, platform) only — scenario does not apply here, since fixes are slice/error-level edits, not scenario-level scaffolding:

- `(product, platform) == (conference, web)` → write the fix as code (full Fix delivery steps 1–4 below).
- Otherwise → deliver only steps 1–3 (explain why in prose, point at the fix conceptually, reference the slice ALWAYS/NEVER rule). **Skip step 4** — no Edit/Write to user files, no full corrected-code block. Close with the relevant official docs link from `${CLAUDE_PLUGIN_ROOT}/llms/{product}/{platform}.txt` so the user can apply the fix using the official documentation.

Source of truth: `reference/supported-matrix.md` → Troubleshoot path row.

## Fix delivery

When the root cause is identified, run the Fix-write support gate above to decide whether step 4 executes.

1. Explain **why** it's broken (one sentence).
2. Show the **fix** (code diff or complete corrected code).
3. Reference the slice's ALWAYS / NEVER rule that was violated.
4. Apply the change (if you have file access) or present it for the user to paste.

## No verification question

Do not actively ask "did it work?" after the fix. The user will come back naturally if it didn't. Asking a forced verification question interrupts their workflow when the fix was successful.

If the user does report the fix didn't work → return to B-Q1 with the new symptom.
