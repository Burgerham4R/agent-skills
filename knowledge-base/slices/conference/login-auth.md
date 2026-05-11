---
id: conference/login-auth
name: 登录与鉴权
product: conference
tags: [login, auth, sdkappid, usersig, useLoginState]
platforms: [web]
related: [conference/room-lifecycle, conference/device-control, conference/prejoin-check]
---

# 登录与鉴权

## 功能说明

登录与鉴权是 Conference 通用会议所有能力的共同入口，负责把业务身份映射成可被 Room UIKit 使用的登录态。它解决“用户是谁、凭什么入会、资料如何同步”这三个基础问题；创建房间、加入房间、采集设备、会中聊天等后续能力都应建立在稳定登录态之上。

## 核心概念

### 角色与操作

| 角色 | 关键操作 | 说明 |
|------|----------|------|
| 业务后端 | 签发 `UserSig` | 正式环境下由服务端签发登录凭证，不在前端硬编码长期有效凭证 |
| 客户端应用 | 调用 `login` | 使用 `SDKAppID / userId / userSig` 建立会议登录态 |
| 当前用户 | 设置资料 | 通过 `setSelfInfo` 同步昵称、头像等会中展示信息 |
| 后续会议能力 | 消费登录态 | `room-lifecycle`、`device-control`、`prejoin-check` 等能力都依赖已登录状态 |

### 事件流

| 阶段 | 参与方 | 关键动作 |
|------|--------|----------|
| 凭证准备 | 后端 → 客户端 | 后端根据业务身份生成 `userSig` 并下发给客户端 |
| 登录建链 | 客户端 | 客户端调用登录接口，建立 SDK 登录态 |
| 资料同步 | 客户端 | 登录成功后补充昵称、头像等用户展示信息 |
| 能力放行 | 客户端 → 会议能力 | 只有登录完成后，房间、设备、聊天等能力才开始工作 |
| 退出登录 | 客户端 | 登出或切换用户时清理旧会话，避免把旧状态带入下一场会议 |

### 状态与数据

| 数据 / 状态 | 说明 |
|-------------|------|
| `sdkAppId` | 当前会议应用的 SDK 应用标识 |
| `userId` | 当前登录用户的唯一身份标识 |
| `userSig` | 用于完成鉴权的动态签名，正式环境应由服务端签发 |
| `selfInfo` | 当前用户昵称、头像等会中展示信息 |
| 登录态 | 表示当前用户是否已可安全执行房间与设备相关操作 |

### 状态机

```text
idle
  → credential-ready
  → logging-in
  → logged-in
  → profile-synced
  → logged-out

logging-in
  → login-failed
  → credential-ready
```

## 最佳实践

### ✅ ALWAYS

1. **由业务后端签发正式环境 `UserSig`** —— 前端只负责消费凭证，不负责生成生产可用签名。
2. **把登录放在应用启动或进入会议主流程之前完成** —— 避免房间创建、设备采集、聊天绑定与登录竞态交错。
3. **登录成功后立即同步用户资料** —— 参会人列表、聊天头像、会控面板都依赖一致的用户展示信息。
4. **在切换账号或退出会议体系时显式清理旧登录态** —— 防止上一位用户的资料和房间上下文泄漏到下一次会话。

### ❌ NEVER

1. **不要在前端硬编码长期有效的生产 `UserSig`** —— 这会破坏鉴权边界，也不利于后续风控和吊销。
2. **不要在未登录完成前直接创建或加入房间** —— 很容易出现入房失败、资料缺失或后续状态无法收口的问题。
3. **不要让多个页面各自重复触发登录** —— 登录应尽量收敛到统一入口，避免并发登录与状态覆盖。

## 排障指南

### 常见问题

| 问题 | 表现 | 处理建议 |
|------|------|----------|
| 登录失败 | 调用登录后报错，后续房间与设备能力都无法使用 | 检查 `sdkAppId`、`userId`、`userSig` 是否匹配，确认 `UserSig` 未过期且由正确环境签发 |
| 用户资料未同步 | 已登录，但参会人列表或聊天区域昵称、头像不对 | 确认登录成功后已调用资料同步接口，并检查是否被旧本地缓存覆盖 |
| 后续能力报未鉴权 | 创建房间、设备采集或聊天初始化时报未登录 | 检查业务流程是否在登录完成前提前触发了 `room-lifecycle` 或 `device-control` |

### 排障流程

```text
发现 登录与鉴权 相关问题
├── 第 1 步：确认当前使用的 sdkAppId / userId / userSig 是否同属一个环境
├── 第 2 步：检查 userSig 是否过期、是否由后端按当前 userId 重新签发
├── 第 3 步：确认登录成功后是否立即同步了昵称、头像等 selfInfo
└── 第 4 步：若房间或设备能力仍异常，再回查 room-lifecycle / device-control 是否在登录前被提前触发
```

## 关联知识

- **[conference/room-lifecycle](room-lifecycle.md)** —— 登录完成后，真正承接创建房间、加入房间、离房和结束会议。
- **[conference/device-control](device-control.md)** —— 摄像头、麦克风等本地设备能力依赖稳定登录态。
- **[conference/prejoin-check](prejoin-check.md)** —— 会前检测通常在登录完成后进入，确保设备信息可被统一管理。
- **[conference/web/login-auth](web/login-auth.md)** —— Web 端的典型 hooks、初始化位置与资料同步方式。
