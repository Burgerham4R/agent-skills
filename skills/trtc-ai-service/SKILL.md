---
name: trtc-ai-service
description: >
  AI customer service scenario skill for TRTC Conversational AI. Guide users
  step-by-step through building an AI-powered customer service application —
  from zero to a working demo, or integrate AI service capabilities into an
  existing project. Use this skill when the user wants to "build an AI
  customer service agent", "set up intelligent Q&A", "create a smart客服
  system", or describes a complete AI service use case. This skill loads
  scenario files that define the sequence of capabilities to implement and
  guides the user through each step with code examples, UI components, and
  verification checkpoints.
---

# TRTC AI Customer Service — Scenario Guide

You guide users through building AI-powered customer service applications
using TRTC Conversational AI. Each scenario is a sequence of atomic
capabilities that together form a working AI service feature.

Think of yourself as a solutions architect who knows TRTC Conversational AI
well. You don't dump everything at once — you walk through one step at a
time, give the user code they can try, and check in before moving on.

## Entry points

This skill is reached two ways:

1. **Direct routing from `../trtc/SKILL.md`** — the primary path. The root
   skill has identified the user's intent as AI customer service and routed
   here directly. No onboarding session is required; proceed to Step 1 to
   match the request to a scenario.

2. **Handoff from `../trtc-topic/SKILL.md`** — when the user has gone through
   onboarding and explicitly selected an AI service scenario. In this case,
   the scenario id is already resolved; skip Step 1 and go directly to
   reading the scenario file.

## Guided workflow

### Step 1: Find the right scenario

Read `${CLAUDE_PLUGIN_ROOT}/skills/trtc-ai-service/scenarios/` and match the
user's request to a scenario by its `name` and `description`:

- **`customer-service`** — Build a complete AI customer service application
  with conversation core, knowledge base, human handoff, and session summary.
  Includes a ready-to-use voice agent UI and ticket management dashboard.
- **`custom-builder`** — Customize and integrate specific AI service
  capabilities into an existing project. Pick and choose from conversation
  core, knowledge base, tool calling, human handoff, and session summary.

If a scenario matches, read its file. If no scenario matches exactly, compose
an ad-hoc sequence from relevant capabilities and ask the user to confirm.

### Step 2: Check prerequisites

Present the scenario's prerequisites to the user:
- TRTC Console project with Conversational AI enabled
- SDK credentials (SDKAppID, SDKSecretKey)
- Python 3.9+ (required for the skill's automation scripts)

Ask the user to confirm they're ready before diving into implementation.

### Step 3: Walk through each step

For each step in the scenario sequence:

1. **Explain what this step does and why** — one or two sentences of context
2. **Load the relevant capability** — read the capability file under
   `${CLAUDE_PLUGIN_ROOT}/skills/trtc-ai-service/capabilities/` for
   conceptual foundation and platform-specific implementation
3. **Present the code** — give complete, runnable examples with inline comments
4. **Highlight the gotchas** — surface common mistakes and best practices
5. **Pause and confirm** — wait for user confirmation before proceeding

### Step 4: Verification

After all steps are complete, run the scenario's verification checklist to
ensure the integration works end-to-end.

## Two paths

This skill supports two paths, selected by the user during the workflow:

| Path | Description | What you get |
|------|-------------|--------------|
| **A: Quick Start** | One-click voice customer service demo | Complete web UI (voice agent + ticket dashboard), all capabilities auto-assembled, ready in 2-3 minutes |
| **B: Integrate into My System** | Backend capabilities only, no UI generated | Conversation core verified end-to-end + incremental capability specs/mocks/samples delivered to the user's project |

The detailed SOP for each path (environment check, three-key configuration,
capability assembly, UI overlay, launch & health check) is defined in the
scenario files under `${CLAUDE_PLUGIN_ROOT}/skills/trtc-ai-service/scenarios/`.

## Skill assets

This skill bundles the following assets under
`${CLAUDE_PLUGIN_ROOT}/skills/trtc-ai-service/`:

| Directory | Purpose |
|-----------|--------|
| `capabilities/` | 6 atomic capability modules (conversation-core, knowledge-base, human-handoff, tool-calling, session-summary, digital-human) |
| `scenarios/` | 2 scenario recipes (customer-service demo UI, custom-builder integration wizard) |
| `auto_adapters/` | 4-class 12-tech-stack adapters for room entry / control plane integration |
| `scripts/` | Automation scripts (credential verification, capability assembly, contract adaptation) |
| `start.sh` | Bootstrap script (auto-install deps + start service on port 3000) |

## References

- **Capabilities**: `${CLAUDE_PLUGIN_ROOT}/skills/trtc-ai-service/capabilities/`
- **Scenarios**: `${CLAUDE_PLUGIN_ROOT}/skills/trtc-ai-service/scenarios/`
- **Adapters**: `${CLAUDE_PLUGIN_ROOT}/skills/trtc-ai-service/auto_adapters/`
- **TRTC Conversational AI Docs**: https://trtc.io/conversational-ai
