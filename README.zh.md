# TRTC AI Integration

**[English](README.md)** | 简体中文

由 [TRTC](https://trtc.io)（腾讯实时音视频）提供的 Agent Skill，帮助开发者将实时音视频、直播、即时通信能力集成到应用中——从零开始到可上线的代码。

不需要翻文档，用自然语言描述你要做什么，Skill 会自动匹配对应知识、问几个关键问题，然后一步步带你完成集成。

可以用来构建视频会议、直播间、1v1 视频问诊、在线教室、客服会话等场景，支持 Web、iOS、Android、Flutter 等平台。

---

### 安装

如果你所在的 IDE 没有插件市场，或者你希望把安装范围限定在某个具体项目里，可以用 npx 安装器。在项目根目录执行：

```bash
# 默认 — 自动检测已安装的 IDE（~/.{claude,cursor,codebuddy,codex}/）
# 为每一个检测到的 IDE 都安装好；都没检测到时回退到 claude
npx -y @tencent-rtc/trtc-agent-skills add

# 强制为所有支持的 IDE 都装一份（即使你本机没装那个 IDE）
npx -y @tencent-rtc/trtc-agent-skills add --ide all

# 只为某个指定的 IDE 安装
npx -y @tencent-rtc/trtc-agent-skills add --ide cursor

# 重装前先清理旧的安装
npx -y @tencent-rtc/trtc-agent-skills add --clean
```

---

## 能做什么

当你提到 TRTC 或描述一个实时通信场景时，Skill 会自动触发，无需任何斜杠命令，直接用自然语言提问即可。

| | 功能说明 | 示例 |
|---|---|---|
| **快速上手** | 引导你跑通 Demo、从零集成、排查错误或添加新功能 | *"我想在 Web 应用里加视频会议"* · *"用户进房报错 6206"* · *"会议已接入，现在想加屏幕共享"* |
| **场景引导** | 加载完整场景，按顺序逐步实现每个能力，每步附代码和验证 | *"我想搭建一个会议应用"* · *"我想用 Conference 搭建一个医疗问诊场景"* |
| **文档查询** | 从官方知识库检索事实性问题，每个答案附来源引用 | *"错误码 6206 是什么意思？"* · *"Conference 按分钟怎么计费？"* · *"会议室最多支持多少人？"* |

Skill 会在项目中保存你的进度。关掉工具下次回来，可以从上次中断的地方继续，不需要重新复述你在做什么。

---

## 支持的产品与平台

| 产品 | 说明 | 可用状态 |
|------|------|---------|
| **Conference** | 视频会议——多人会议、屏幕共享、会中聊天 | Web ✅ |
| **Conversational AI** | TRTC 对话式 AI——AI 语音助手、智能问答、人工转接、会话摘要 | Web ✅ |
| **Live** | 互动直播——主播/观众、连麦、弹幕、礼物、美颜 | 即将支持 |
| **Chat** | 即时通信——消息、会话、群组、用户资料 | 即将支持 |
| **Call** | 音视频通话——1v1 和群组通话 | 即将支持 |
| **RTC Engine** | 实时音视频引擎——进房、推流、拉流 | 即将支持 |

### Conversational AI — 支持的场景

Conversational AI 是基于 TRTC 语音和 LLM 能力构建的独立产品。`trtc-ai-service` 技能目前支持以下场景：

| 场景 | 说明 |
|------|------|
| **AI 客服** | 搭建完整的 AI 智能客服应用——语音助手、知识库、人工转接、会话摘要。包含开箱即用的 Web Demo UI。 |
| **自定义构建** | 将对话式 AI 的各项能力（对话核心、工具调用、知识库等）集成到你自己的项目中。 |


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
