# Path A1 — Demo Quickstart

> Loaded by `../../trtc-onboarding/SKILL.md` when `intent = demo` in `${CLAUDE_PROJECT_DIR}/.trtc-session.yaml`.
> Before reading this file, SKILL.md must have populated `${CLAUDE_PROJECT_DIR}/.trtc-session.yaml` and passed Stage 1 calibration.

**Your role: Executor.** You clone the official demo, configure it, and run it. The developer sees a working product in minutes.

**CRITICAL: Do NOT write custom code in the user's project.** Path A1 runs the official pre-built demo in a separate directory, even if the user's project already has TRTC dependencies.

**Source of truth for demo info:** Run `Bash(curl -s https://trtc.io/llms/{product}/{platform}.txt)` to get the platform index (e.g., `https://trtc.io/llms/conference/web.txt`). Look for "Run Sample Code" / "Run Demo" links. If the curl returns HTML (404 page) or empty, fall back to `Bash(curl -s https://trtc.io/llms/{product}.txt)` for the product-level index.

Recap example:
> Got it — you want to try the Live iOS demo. I'll clone it into `/tmp/`, leave your project untouched.

## A1-Q1 — Credentials

**Before showing the manual question below**, run the MCP credential detection
protocol: Read `reference/mcp-credential-detection.md` and follow its Steps 1–4.
If MCP detection succeeds (user confirms the detected credentials), skip the
manual question below entirely and proceed to A1.2. Only show the manual question
if MCP detection falls through to Step 4 (Fallback).

Question text: "Do you already have a TRTC SDKAppID and SecretKey?"

| # | Option | Next |
|---|--------|------|
| 1 | Yes, I have them ready | Wait for the user to paste. Proceed to A1.2 after both are captured. |
| 2 | Not yet, show me how to get them | Show the steps below, then wait. |
| 3 | I don't know what those are | Show the 1-sentence explanation + the steps below, then wait. |
| 4 | Type something | free-text |

**Credential acquisition steps** (shown for options 2 and 3):

> To run the demo you need an SDKAppID and a SecretKey from the TRTC console.
>
> 1. Open https://trtc.io/console
> 2. Sign up or log in with your Tencent Cloud account
> 3. Click "Create Application", give it any name
> 4. Once created, the application detail page shows the SDKAppID at the top. Open the "Quick Start" or "Basic Info" tab to reveal the SecretKey.
>
> Paste both values here when you have them.

Do not attempt to auto-open the browser. Some environments (SSH / headless containers / CI) do not have a GUI, and a silent failure there is worse than a working copy-paste flow.

### Demo credential injection (MCP-aware)

After credentials are confirmed (via MCP auto-detect or manual input) and the
demo is cloned, before configuring the demo's credential file:

**If MCP is available** (`.mcp.json` has a matching server entry):
1. Read `reference/mcp-usersig-generation.md` and follow its Generation Protocol
2. Call `get_usersig` for `user001` (and `user002` if the demo needs two users)
3. Write both the SDKAppID AND the generated userSig(s) into the demo's config
   file (the specific file varies by product/platform — check the demo README)
4. This means the demo can run immediately without the user needing to generate
   credentials manually on the console

**If MCP is NOT available:**
- Use the manually-provided SDKAppID/SecretKey
- Instruct the user on where to paste them in the demo config file
- Point them to the console's "Quick Start" tool for generating a test userSig

## A1-Q2 — Step gate (after each milestone: clone done, pod install done, etc.)

Question text: "Ready for the next step?"

| # | Option |
|---|--------|
| 1 | Yes, continue |
| 2 | Pause, I have a question first |
| 3 | Give me the full command list, I'll run it myself |
| 4 | Type something |

## A1-Q3 — Post-demo branching

Question text: "Demo is running. What's next?"

| # | Option | Next |
|---|--------|------|
| 1 | Integrate this into my own project | Path A2 (load `reference/path-a2-integrate.md`) |
| 2 | Something's not working / I got an error | Path B (load `reference/path-b-troubleshoot.md`) |
| 3 | Type something | free-text |
