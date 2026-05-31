# TRTC AI Integration

An agent skill provided by [TRTC](https://trtc.io) (Tencent Real-Time Communication) to help developers integrate real-time audio/video, live streaming, and instant messaging into their apps — from first setup to production-ready code.

Instead of reading through long documentation, you describe what you want to build in plain language. The skill routes your request to the right knowledge, asks a few clarifying questions, and walks you through the integration step by step.

You can use it to build scenarios like video conferencing, live streaming rooms, 1-on-1 video consultations, online classrooms, or customer support chat — across Web, iOS, Android, Flutter, and more.

---

## Installation

**Claude Code**

```bash
# Step 1 — add the TRTC plugin marketplace
/plugin marketplace add Tencent-RTC/agent-skills

# Step 2 — install the plugin
/plugin install trtc-agent-skills@trtc-marketplace

# Step 3 — activate without restarting
/reload-plugins
```

**Cursor**

Clone the repo and symlink it into Cursor's local plugin directory:

```bash
git clone https://github.com/Tencent-RTC/agent-skills.git
ln -s "$(pwd)/agent-skills" ~/.cursor/plugins/local/trtc-agent-skills
```

Then in Cursor run **`Cmd+Shift+P`** → `Reload Window` (or restart Cursor).

**Codex CLI**

```bash
# Step 1 — add the TRTC plugin marketplace
codex plugin marketplace add Tencent-RTC/agent-skills

# Step 2 — open the plugin browser, search "trtc-agent-skills" and install
# Run inside Codex CLI:
/plugins
```

**CodeBuddy**

```bash
# Step 1 — add the TRTC plugin marketplace
/plugin marketplace add Tencent-RTC/agent-skills

# Step 2 — install the plugin
/plugin install trtc-agent-skills@trtc-marketplace

# Step 3 — activate without restarting
/reload-plugins
```

## Using with MCP

This skill is designed to work alongside the [Tencent RTC MCP server](https://trtc.io/document/78382). The skill provides behavioral guidance on how to integrate TRTC, while MCP provides up-to-date API docs and `userSig` generation.

**Claude Code**

```bash
claude mcp add tencent-rtc -e SDKAPPID=YOUR_SDKAPPID -e SECRETKEY=YOUR_SECRET_KEY -- npx -y @tencentcloud/sdk-mcp@1.4.3
```

**Cursor** — add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "tencent-rtc": {
      "command": "npx",
      "args": ["-y", "@tencentcloud/sdk-mcp@1.4.3"],
      "env": {
        "SDKAPPID": "YOUR_SDKAPPID",
        "SECRETKEY": "YOUR_SECRET_KEY"
      }
    }
  }
}
```

**Codex CLI**

```bash
codex mcp add tencent-rtc --env SDKAPPID=YOUR_SDKAPPID --env SECRETKEY=YOUR_SECRET_KEY -- npx -y @tencentcloud/sdk-mcp@1.4.3
```

**CodeBuddy** — add via Settings → Add MCP:

```json
{
  "mcpServers": {
    "tencent-rtc": {
      "command": "npx",
      "args": ["-y", "@tencentcloud/sdk-mcp@1.4.3"],
      "env": {
        "SDKAPPID": "YOUR_SDKAPPID",
        "SECRETKEY": "YOUR_SECRET_KEY"
      }
    }
  }
}
```

---

The skill activates automatically when you mention TRTC or describe a real-time communication use case. No slash commands needed — just ask in plain language.

| | What it does | Example prompts |
|---|---|---|
| **Get started** | Guides you through demo setup, SDK integration, troubleshooting, or adding a new feature — step by step | *"I want to add video conferencing to my web app"* · *"I'm getting error 6206 when users join"* · *"Conference is working — now I want to add screen sharing"* |
| **Scenario walkthrough** | Loads a complete feature scenario and walks you through each capability in order, with code and checkpoints | *"Walk me through building a complete conference room from scratch"* · *"Guide me through a 1-on-1 video consultation end to end"* |
| **Docs & lookup** | Answers factual questions from the official knowledge base with cited sources | *"What does error code 6206 mean?"* · *"How much does Conference cost per participant minute?"* · *"What's the max number of participants?"* |

The skill saves your progress in the project. If you close the tool and come back later, it picks up where you left off.

---

## Supported Products & Platforms

| Product | Description | Availability |
|---------|-------------|--------------|
| **Conference** | Video conferencing — multi-party meetings, screen sharing, in-meeting chat | Web ✅ |
| **Live** | Interactive live streaming — anchor/audience roles, co-hosting, barrage, gifts, beauty filters | Coming soon |
| **Chat** | Instant messaging — messages, conversations, groups, user profiles | Coming soon |
| **Call** | Audio/video calling — 1-on-1 and group calls | Coming soon |
| **RTC Engine** | Low-level real-time audio/video engine — room management, publishing, subscribing | Coming soon |

> The skill also recognizes business scenarios that imply real-time communication — "telemedicine app", "online classroom", "video interview platform" — and maps them to the right TRTC product automatically.

---

## How It Works

When you describe what you want to build, the skill:

- **Identifies** your TRTC product and platform — from your message or by reading your project files
- **Asks** what you're trying to do: run a demo, start a new integration, troubleshoot an error, or add a feature to an existing project
- For integrations, **picks a scenario** from the knowledge base that matches your use case and shows you the full capability list — what will be implemented, in what order — before starting
- **Walks through** one capability at a time with production-ready code, waits for you to confirm it works, then moves to the next step
- **Saves your progress** to `.trtc-session.yaml` in your project root (auto-added to `.gitignore`) so you can resume in a later session without re-explaining what you're building

Step-by-step integration is currently available for **Conference on Web**. Docs lookup, error code search, and pricing questions work across all TRTC products (Conference, Live, Chat, Call, RTC Engine).

### Knowledge base: Slices and Scenarios

The skill's knowledge is structured into two layers:

**Slices** are atomic capability units — one slice per feature, such as `conference/join-room`, `conference/screen-share`, or `live/barrage`. Each slice has two levels:
- A product-level overview (concepts, best practices, troubleshooting, cross-platform notes)
- A platform-level implementation (exact APIs, code samples, platform-specific gotchas)

**Scenarios** are curated sequences of slices for complete use cases. For example, the *Conference Room* scenario chains multiple slices — from authentication and room creation through screen sharing, member management, and cleanup — in the order a real implementation would follow.

---

## Links

- [TRTC Documentation](https://trtc.io/document)
- [TRTC Console (International)](https://console.trtc.io)
- [TRTC Console (China)](https://console.cloud.tencent.com)
- [Report an issue](https://github.com/Tencent-RTC/agent-skills/issues)
