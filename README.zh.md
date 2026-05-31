# TRTC AI Integration

由 [TRTC](https://trtc.io)（腾讯实时音视频）提供的 Agent Skill，帮助开发者将实时音视频、直播、即时通信能力集成到应用中——从零开始到可上线的代码。

不需要翻文档，用自然语言描述你要做什么，Skill 会自动匹配对应知识、问几个关键问题，然后一步步带你完成集成。

可以用来构建视频会议、直播间、1v1 视频问诊、在线教室、客服会话等场景，支持 Web、iOS、Android、Flutter 等平台。

---

## 安装

**Claude Code**

```bash
# 第一步 — 添加 TRTC 插件市场
/plugin marketplace add Tencent-RTC/agent-skills

# 第二步 — 安装插件
/plugin install trtc-agent-skills@trtc-marketplace

# 第三步 — 无需重启，直接激活
/reload-plugins
```

**Cursor**

克隆仓库并创建符号链接到 Cursor 本地插件目录：

```bash
git clone https://github.com/Tencent-RTC/agent-skills.git
ln -s "$(pwd)/agent-skills" ~/.cursor/plugins/local/trtc-agent-skills
```

然后按 **`Cmd+Shift+P`** → 输入 `Reload Window` 回车（或直接重启 Cursor）。

**Codex CLI**

```bash
# 第一步 — 添加 TRTC 插件市场
codex plugin marketplace add Tencent-RTC/agent-skills

# 第二步 — 打开插件浏览器，搜索 "trtc-agent-skills" 并安装
# 在 Codex CLI 中运行：
/plugins
```

**CodeBuddy**

```bash
# 第一步 — 添加 TRTC 插件市场
/plugin marketplace add Tencent-RTC/agent-skills

# 第二步 — 安装插件
/plugin install trtc-agent-skills@trtc-marketplace

# 第三步 — 无需重启，直接激活
/reload-plugins
```

## 配置 MCP

本 Skill 需要配合 [Tencent RTC MCP Server](https://trtc.io/document/78382) 使用。Skill 负责集成引导，MCP 负责提供最新 API 文档和生成测试用 `userSig`。

**Claude Code**

```bash
claude mcp add tencent-rtc -e SDKAPPID=YOUR_SDKAPPID -e SECRETKEY=YOUR_SECRET_KEY -- npx -y @tencentcloud/sdk-mcp@1.4.3
```

**Cursor** — 添加到 `.cursor/mcp.json`：

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

**CodeBuddy** — 通过 设置 → 添加 MCP 配置：

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

## 功能

当你提到 TRTC 或描述一个实时通信场景时，Skill 会自动触发，无需任何斜杠命令，直接用自然语言提问即可。

| | 功能说明 | 示例 |
|---|---|---|
| **快速上手** | 引导你跑通 Demo、从零集成、排查错误或添加新功能 | *"我想在 Web 应用里加视频会议"* · *"用户进房报错 6206"* · *"会议已接入，现在想加屏幕共享"* |
| **场景引导** | 加载完整场景，按顺序逐步实现每个能力，每步附代码和验证 | *"带我一步步搭一个完整的会议室"* · *"引导我实现 1v1 视频问诊的完整流程"* |
| **文档查询** | 从官方知识库检索事实性问题，每个答案附来源引用 | *"错误码 6206 是什么意思？"* · *"Conference 按分钟怎么计费？"* · *"会议室最多支持多少人？"* |

Skill 会在项目中保存你的进度。关掉工具下次回来，可以从上次中断的地方继续，不需要重新解释你在做什么。

---

## 支持的产品与平台

| 产品 | 说明 | 可用状态 |
|------|------|---------|
| **Conference** | 视频会议——多人会议、屏幕共享、会中聊天 | Web ✅ |
| **Live** | 互动直播——主播/观众、连麦、弹幕、礼物、美颜 | 即将支持 |
| **Chat** | 即时通信——消息、会话、群组、用户资料 | 即将支持 |
| **Call** | 音视频通话——1v1 和群组通话 | 即将支持 |
| **RTC Engine** | 实时音视频引擎——进房、推流、拉流 | 即将支持 |

> Skill 也能识别隐含实时通信需求的业务场景——"在线问诊"、"网课"、"视频面试"——并自动匹配对应的 TRTC 产品。

---

## 工作原理

当你描述要做什么时，Skill 会：

- **识别**你的 TRTC 产品和平台——从你的描述或项目文件中推断
- **询问**你的意图：跑通 Demo、从零集成、排查错误，还是在已有项目上扩展功能
- 对于集成任务，从知识库**匹配场景**，展示完整的能力清单——要实现什么、按什么顺序——确认后再开始
- **逐步推进**，每次只处理一个能力，给出可用代码，等你确认成功后再继续
- **保存进度**到项目根目录的 `.trtc-session.yaml`（自动加入 `.gitignore`），支持跨 session 续接

集成引导目前仅支持 **Conference Web**。文档查询、错误码搜索、计费咨询全产品可用（Conference、Live、Chat、Call、RTC Engine）。

### 知识库：Slice 与 Scenario

Skill 的知识分两层：

**Slice** 是原子能力单元——每个功能对应一个 Slice，如 `conference/join-room`、`conference/screen-share`、`live/barrage`。每个 Slice 分两层：
- 产品级概览：功能说明、核心概念、最佳实践、排障指南（跨平台通用）
- 平台实现细节：具体 API、代码示例、平台特有注意事项

**Scenario** 是面向完整场景的 Slice 串联。例如「会议室」Scenario 按顺序链接多个 Slice——从鉴权、创建房间，到屏幕共享、成员管理、退出清理——以真实集成顺序排列。

---

## 相关链接

- [TRTC 文档](https://trtc.io/document)
- [控制台（国际站）](https://console.trtc.io)
- [控制台（中国站）](https://console.cloud.tencent.com)
- [下载 SDK](https://trtc.io/download)
- [提交问题](https://github.com/Tencent-RTC/agent-skills/issues)
