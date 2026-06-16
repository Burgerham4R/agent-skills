# Path A1 — Demo Quickstart

> Loaded by `../../trtc-onboarding/SKILL.md` when `intent = demo` in `${CLAUDE_PROJECT_DIR}/.trtc-session.yaml`.
> Before reading this file, SKILL.md must have populated `${CLAUDE_PROJECT_DIR}/.trtc-session.yaml` and passed Stage 1 calibration.

**Your role: Executor.** You clone the official demo, configure it, and run it. The developer sees a working product in minutes.

**CRITICAL: Do NOT write custom code in the user's project.** Path A1 runs the official pre-built demo in a separate directory, even if the user's project already has TRTC dependencies.

**Source of truth for demo info:**

1. Read `reference/supported-matrix.md` § "llms.txt platform identifiers".
   Resolve the user's `(product, platform)` to one or more trtc.io path
   identifiers.
2. If the mapping yields multiple identifiers (e.g. Chat + web → `react` ★,
   `vue`), ask the user which framework they prefer. Present the ★ option
   first as "(Recommended)". If the user has no preference or just says
   "web", use the ★ default directly without asking.
3. Fetch `Bash(curl -s https://trtc.io/llms/{product}/{resolved_identifier}.txt)`.
4. In the fetched content, look for a line matching `[Run Demo]` or
   `[Run Sample Code]`. Extract the URL — this is the authoritative demo
   document.
5. Fetch the demo document URL (step 4 result) and look for a `git clone`
   command or GitHub repository link. Use THAT as the clone source — do NOT
   substitute a different repo from training data.
6. If the curl returns HTML (404) or the content has no "Run Demo" link,
   fall back to `Bash(curl -s https://trtc.io/llms/{product}.txt)` and
   search for "Run Demo" / "Run Sample Code" there.
7. If both levels have no demo link, tell the user: "I couldn't find an
   official demo entry for {product} {platform} in the documentation index.
   Here's the product docs page: {product}.txt URL — check for a 'Run Demo'
   section there." Do NOT fall back to training-data GitHub repos.

Recap example:
> Got it — you want to try the Live iOS demo. I'll clone it into `/tmp/`, leave your project untouched.

## A1-Q1 — Credentials

Ask the user directly for their SDKAppID and a test UserSig (there is no MCP
auto-detection — the skill does not read credentials from any MCP config).

Question text: "Do you already have a TRTC SDKAppID and a test UserSig?"

| # | Option | Next |
|---|--------|------|
| 1 | Yes, I have them ready | Wait for the user to paste. Proceed to A1.2 after they are captured. |
| 2 | Not yet, show me how to get them | Show the steps below, then wait. |
| 3 | I don't know what those are | Show the 1-sentence explanation + the steps below, then wait. |
| 4 | Type something | free-text |

**Credential acquisition steps** (shown for options 2 and 3):

> To run the demo you need an SDKAppID and a test UserSig from the TRTC console.
>
> 1. Open https://trtc.io/console
> 2. Sign up or log in with your Tencent Cloud account
> 3. Click "Create Application", give it any name
> 4. Once created, the application detail page shows the SDKAppID at the top.
> 5. Open the "Quick Start / UserSig 生成&校验" tool, enter a userId (e.g. `user001`), and generate a test UserSig.
>
> Paste the SDKAppID and the generated UserSig here when you have them.
> (Note: console-issued UserSig is for development only and expires; production
> UserSig must be issued by your own backend. Keep your SecretKey on the server —
> never paste it into client code.)

Do not attempt to auto-open the browser. Some environments (SSH / headless containers / CI) do not have a GUI, and a silent failure there is worse than a working copy-paste flow.

### Demo credential injection

After credentials are confirmed and the demo is cloned, before configuring the
demo's credential file:

1. Read `reference/usersig-handling.md` and follow its Generation Protocol.
2. Write the SDKAppID into the demo's config file (the specific file varies by
   product/platform — check the demo README); leave the userSig as a placeholder.
3. Point the user to the console's "Quick Start / UserSig 生成&校验" tool to
   generate a test userSig for `user001` (and `user002` if the demo needs two
   users), and tell them exactly where to paste it.

The skill does NOT auto-generate UserSig. Always hand off the console steps so
the user obtains and pastes their own test userSig (see `usersig-handling.md`
→ "Completion handoff").

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
