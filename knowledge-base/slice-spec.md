# TRTC 原子能力（Slice）定义规范

> 本文档定义了 TRTC AI 知识库中 Slice 的拆分标准、编写规范和规划方法论。
> 所有 slice 的创建和维护都应遵循本规范。

---

## 一、什么是 Slice

Slice（原子能力）是 TRTC AI 知识库的最小知识单元。每个 slice 描述一个**独立的功能点**，包含：这个功能是什么、怎么用、常见的坑、出了问题怎么排查。

**类比**：如果 TRTC SDK 是一台车，slice 就是驾驶手册里的一个章节——"怎么启动"、"怎么倒车"、"怎么用定速巡航"，每一章独立可读，合在一起就是完整手册。

---

## 二、Slice 拆分标准

### 核心原则

> **一个 slice = 用户遇到一个具体问题时，我们能一次性讲清楚的内容。**

### 判断方法：三个问题

#### 问题 1：「能不能一次讲清楚？」

如果客户来问这个问题，技术支持能不能在**一次沟通**中完整解决？

| 判断 | 举例 | 说明 |
|------|------|------|
| ✅ 合适 | "多端登录老是互踢怎么办？" | 讲清楚策略配置 + 回调处理 + 常见错误码就行 |
| ✅ 合适 | "消息发不出去" | 讲清楚发送流程 + 权限检查 + 错误码就行 |
| ❌ 太大了 | "消息功能怎么做？" | 发送、接收、历史记录、撤回、已读... 一次说不完 |
| ❌ 太小了 | "怎么设置消息的优先级字段？" | 就一个参数，不值得单独做 |

**简单判断**：想象客户发来一条微信问这个问题，你用**一段话或一个截图**能不能回答？能 → 合适的粒度。需要连续发好几屏 → 太大。回复一句话就搞定 → 太小，可以合并到相关功能里。

#### 问题 2：「出问题时，排查方向一样吗？」

如果两个功能出问题后，排查思路完全不同，就应该拆成两个 slice。

| 场景 | 排查方向 | 结论 |
|------|---------|------|
| "消息发不出去" vs "收不到消息" | 发送查网络/权限/格式，接收查监听/登录状态/群设置 | → **拆成两个** |
| "发文本消息" vs "发图片消息" | 都是查消息格式和网络 | → **合成一个**（发送消息） |
| "主播无法开播" vs "连麦布局不对" | 开播查权限/配置，布局查模板参数 | → **拆成两个** |

**简单判断**：客户报这两个问题的时候，你会不会分给同一个人处理？如果是，多半可以合并；如果你本能想找不同的人来看，就该拆开。

#### 问题 3：「是独立的用户动作吗？」

一个 slice 应该对应一个用户能感知到的**独立操作步骤**。

| 场景 | 用户动作 | 结论 |
|------|---------|------|
| 配置准备页 → 点开播 → 进入直播间 | 这是一个连贯动作 | → **一个** slice（主播开播） |
| 选择连麦布局模板 | 独立的配置决策 | → **单独一个** slice |
| 隐藏某个按钮 + 改文案 + 换图标 | 都是"改 UI 外观"这一个动作 | → **合成一个** slice（UI 定制） |

### 粒度对比示例

以「消息」为例：

```
❌ 太粗 → 一个"消息"slice 包含发送+接收+历史+撤回+转发+已读+推送
   问题：客户说"消息收不到"，要在几千字里找相关部分

❌ 太细 → 把发文本消息、发图片、发视频、发文件各做一个 slice
   问题：它们的用法和排障方式几乎一样，重复内容太多

✅ 合适 → 拆成：发送消息 / 接收消息 / 历史消息 / 消息撤回 / 离线推送
   每个都能一次讲清，排查方向各不相同
```

---

## 三、Slice 两层架构：主线 + 反馈

| 层级 | 名称 | 来源 | 用途 |
|------|------|------|------|
| 🅰️ **主线 Slice** | 骨架 | 按 SDK 能力域系统规划（来自官方文档+研发经验） | 保证每个核心功能都有覆盖 |
| 🅱️ **反馈 Slice** | 血肉 | 从产品/销售收集的用户高频问题中提炼 | 补充真实的坑和边缘场景 |

### 两者的关系
- **主线是骨架**：每个开发者都要走的路（初始化 → 登录 → 发消息 → ...）
- **反馈是血肉**：开发者最容易摔跤的坑（互踢死循环、推送不到达、...）
- 反馈 slice 可以是主线 slice 的深度补充，也可以是全新的边缘场景

### 在 index.yaml 中的标记

```yaml
- id: chat/multi-instance
  name: 多端登录与互踢
  tags: [multi-instance, kick-offline, login]
  platforms: [web, android, ios, flutter]
  file: slices/chat/multi-instance.md
  description: 多端登录策略配置、互踢回调处理、常见错误码
  status: active          # active | planned
```

---

## 四、Slice 文件结构规范

每个 slice 文件是一个 Markdown 文件，包含 YAML frontmatter 和固定的内容结构。

### 文件位置

```
knowledge-base/slices/{product}/{ability}.md          # 产品级概览（跨平台通用）
knowledge-base/slices/{product}/{platform}/{ability}.md  # 平台实现细节
```

### Frontmatter 字段

```yaml
---
id: chat/msg-send           # Slice ID，与 index.yaml 中的 id 一致
name: 发送消息               # Slice 名称
product: chat               # 所属产品
tags: [message, send, ...]  # 搜索标签
platforms: [web, android, ios, flutter]  # 支持的平台
related:                    # 关联的 slice
  - chat/msg-receive
  - chat/msg-custom
docs:                       # 参考的官方文档
  - title: 发送消息文档
    url: https://trtc.io/zh/document/xxx
---
```

### 内容结构

```markdown
# {名称}（产品级概览）

## 功能说明
[功能描述、典型场景、版本要求]

## 核心概念
[核心概念解释，使用表格和代码块辅助说明]

## 最佳实践
### ✅ ALWAYS（必须做的）
### ❌ NEVER（绝不要做的）

## 排障指南
### 常见错误码
[错误码表格]
### 排障流程
[树状排查流程]

## 关联知识
[引用相关 slice]
```

---

## 五、能力域划分（Chat 产品）

| 能力域 ID | 名称 | 主线 Slice | 反馈 Slice |
|-----------|------|-----------|-----------|
| foundation | 初始化与认证 | init, login, multi-instance, event-listener | network-status |
| message | 消息 | msg-send, msg-receive, msg-history, msg-offline-push | msg-recall, msg-read-receipt, msg-forward, msg-reaction, msg-custom |
| conversation | 会话 | conv-list, conv-unread | conv-pin, conv-draft, conv-delete, conv-mark |
| group | 群组 | group-create, group-join, group-manage, group-msg | group-avchatroom, group-attribute, group-counter |
| user-relation | 用户与关系链 | user-profile | user-status, friend-manage, friend-group |
| signaling | 信令 | — | signaling |
| advanced | 进阶能力 | — | translation, moderation, community |

### 汇总

| 类型 | 数量 | 占比 |
|------|------|------|
| 🅰️ 主线 Slice | 15 个 | 43% |
| 🅱️ 反馈 Slice | 20 个 | 57% |
| **合计** | **35 个** | 100% |

---

## 六、实施顺序

### Phase 1：主线骨架（15 个 slice）

```
init → login → event-listener → multi-instance
  → msg-send → msg-receive → msg-history → msg-offline-push
  → conv-list → conv-unread
  → group-create → group-join → group-manage → group-msg
  → user-profile
```

### Phase 2：反馈血肉

根据信息收集表格的频次排序，逐步补充反馈 slice。
优先级排序：(两者都是 > 出错 > 使用) × (高 > 中 > 低)

### Phase 3：场景组合

每积累 3-5 个相关 slice 后，编写一个 scenario（场景引导）。
