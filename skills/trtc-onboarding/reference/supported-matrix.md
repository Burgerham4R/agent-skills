# TRTC Skill — Supported Matrix (一期)

> Single source of truth for which (product × platform × scenario)
> combinations the skill currently covers, broken down by path. Update
> this file when adding new platforms, products, or scenarios; no other
> file should encode per-pair support state.

## Integration path — write code into user project

> Used by onboarding Path A2 (intent = integrate-scenario / integrate-feature)
> and Path C (expand). Onboarding hard-blocks combinations marked ⏳; topic
> assumes any session reaching it has already passed all three gates
> (product, platform, scenario).

### Product × Platform

| Product    | Web | iOS | Android | Flutter | Electron |
|------------|:---:|:---:|:-------:|:-------:|:--------:|
| Conference | ✅  | ⏳  | ⏳      | ⏳      | ⏳       |
| Live       | ⏳  | ⏳  | ⏳      | ⏳      | ⏳       |
| Call       | ⏳  | ⏳  | ⏳      | ⏳      | ⏳       |
| Chat       | ⏳  | ⏳  | ⏳      | ⏳      | ⏳       |
| RTC Engine | ⏳  | ⏳  | ⏳      | ⏳      | ⏳       |

✅ supported · ⏳ coming soon

### Conference Web — Scenarios

Within (Conference, Web), only these scenarios are integration-supported in v1:

| Scenario id                        | Display name           | Support |
|------------------------------------|------------------------|:-------:|
| `general-conference`               | 通用会议               | ✅      |
| `1v1-video-consultation`           | 1v1 视频问诊（医疗）   | ✅      |
| `webinar-conference`               | 研讨会 / 宣讲会        | ⏳      |
| `medical-multidoctor-consultation` | 医疗会诊（多医生）     | ⏳      |

A2-Q0's conference scenario menu MUST list only the ✅ rows above. Other
`status: active` scenarios in `index.yaml` are hidden from the user-facing
menu in v1 — they remain in the index as content, but onboarding does not
expose them as integration entry points.

## Demo path — clone & run official demo

All combinations supported. Demo source is the official open-source repo;
no skill-side code generation, so platform / product / scenario matrix
does not apply.

## Docs path — fact / decision / error-code lookups

All combinations supported. Backed by llms.txt
(`${CLAUDE_PLUGIN_ROOT}/llms/{product}/{platform}.txt`) and slice files
where available; falls back to official trtc.io docs when slice is missing.

## Troubleshoot path — error diagnosis

- **Diagnose** (B-Q0 / B-Q1, root cause analysis): all combinations.
- **Write fix code** (Path B Step 4 — apply diff or full corrected code):
  ✅ Conference Web only (any scenario). Other combinations get root cause +
  slice rule citation + official docs link; no Edit/Write to user files.

  Note: scenario gating does not apply here — fix-write is gated on
  (product, platform) only. Fixes are slice/error-level edits, not
  scenario-level scaffolding.

## When to update this file

- A new platform's Conference slice content lands → flip the platform cell
  to ✅ and remove the integration-intent narrowing in Stage 1B Q3 for that
  platform.
- A new conference scenario gets full coverage → add a ✅ row to the
  Scenarios table and add it to A2-Q0's conference menu in
  `path-a2-integrate.md`.
- A new product launches with full slice content for some platform → flip
  that cell.
