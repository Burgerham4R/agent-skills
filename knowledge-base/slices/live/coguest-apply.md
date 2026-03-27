---
id: live/coguest-apply
name: 观众申请连麦
product: live
tags: [coguest, apply, seat, mic, CoGuestStore, connect]
platforms: [ios, android, web, flutter]
related: [live/coguest-invite, live/device-control, live/beauty, live/audience-watch]
docs:
  - title: 观众申请连麦
    url: https://trtc.io/zh/document/74598
---

# 观众申请连麦

## 功能说明

观众申请连麦（Apply-for-Seat）是直播场景中观众主动发起、主播审批的连麦流程。`CoGuestStore` 负责完整的信令管理，包含申请、审批、拒绝、取消和断开连麦等操作。整个流程通过 `hostEventPublisher` 和 `guestEventPublisher` 进行事件分发，视频渲染由 `VideoViewDelegate` 的 `createCoGuestView` 提供。

## 核心概念

| 方法 / 属性 | 说明 |
|-------------|------|
| `CoGuestStore` | 管理连麦信令完整生命周期的核心类，通过 `create(liveID:)` 初始化 |
| `applyForSeat(timeout:extraInfo:completion:)` | 观众发起连麦申请；`timeout` 控制等待审批的超时时长（秒） |
| `cancelApplication(completion:)` | 观众在主播响应前撤回申请 |
| `acceptApplication(userID:completion:)` | 主播同意指定观众的连麦申请 |
| `rejectApplication(userID:completion:)` | 主播拒绝指定观众的连麦申请 |
| `disConnect(completion:)` | 连麦中的参与方主动断开连麦 |
| `hostEventPublisher` | 主播端事件流；含 `onGuestApplicationReceived`（收到申请）等事件 |
| `guestEventPublisher` | 观众端事件流；含 `onGuestApplicationResponded`（申请被响应）等事件 |
| `VideoViewDelegate` | 连麦视频渲染代理；`createCoGuestView(seatInfo:viewLayer:)` 提供视图 |
| `CoGuestState.connected` | 当前连麦中的用户列表 |
| `CoGuestState.applicants` | 待审批的申请者列表 |

### CoGuestStore 状态机

```
观众端：        idle → applying → connected → idle
主播端：        idle → reviewing（收到申请）→ idle（同意/拒绝后）
```

## 最佳实践

### ✅ ALWAYS

1. **申请超时设置合理值（推荐 30 秒）** — `applyForSeat(timeout:)` 的超时决定了观众等待审批的最长时间。超时过短（<10 秒）会导致主播来不及响应；过长（>60 秒）会让观众长时间等待。推荐默认值 30 秒，并在 UI 上展示倒计时。
2. **申请通过后立即打开设备** — 收到 `onGuestApplicationResponded(.accepted)` 回调后，立刻调用 `openLocalCamera` 和 `openLocalMicrophone`，减少连麦延迟。设备开启成功后画面才能被其他人看到。
3. **断开连麦后立即关闭设备** — 调用 `disConnect` 或收到断开回调后，立即调用 `closeLocalCamera()` 与 `closeLocalMicrophone()`，避免摄像头指示灯常亮、耗电及隐私问题。
4. **主播端监听 `hostEventPublisher`** — 主播必须订阅 `hostEventPublisher` 才能收到观众的申请通知。若主播界面未订阅，观众申请会超时无响应。

### ❌ NEVER

1. **通过前开设备** — 在 `applyForSeat` 发出后、收到 `accepted` 回调前就开启摄像头或麦克风，会导致观众在未获批时就推流，消耗流量且影响体验。必须等待 `accepted` 回调。
2. **忽略超时拒绝回调** — `applyForSeat` 的 `completion` 中的 `.failure` 分支（超时场景）必须处理，向用户展示"申请超时，请重试"的提示，否则观众界面卡在"申请中"状态。
3. **超过麦位上限仍继续申请** — 错误码 `-2340` 表示麦位已满。收到此错误时，应提示用户"当前连麦人数已达上限"，而非静默失败或重试。

## 排障指南

### 常见错误码

| 错误码 | 描述 | 处理建议 |
|--------|------|----------|
| `-2340` | 麦位已满，无法再接受新的连麦申请 | 提示观众"当前连麦人数已达上限，请稍后再试" |
| 超时（无特定错误码）| `applyForSeat` timeout 到期后主播未响应 | UI 展示"申请超时"，恢复申请按钮允许重试 |
| 主播无响应 | 主播端未订阅 `hostEventPublisher` | 检查主播 ViewController 是否正确订阅并持有 cancellable |

### 排障流程

```
观众申请后无响应（一直等待）
├── 主播是否订阅了 hostEventPublisher？
│       └─ 否 → 检查主播端订阅代码，确认 cancellable 未被提前释放
├── timeout 值是否太短？
│       └─ 调整为 30 秒或更长
└── 网络是否正常？
        └─ 检查信令通道连通性

观众申请被拒绝（错误码 -2340）
└─ 麦位已满 → 提示用户稍后重试，不要自动循环重试

连麦中断开后设备仍在运行
└─ 确认 disConnect 回调后调用了 closeLocalCamera + closeLocalMicrophone

连麦后画面黑屏
├── 是否在 accepted 回调后才开设备？
│       └─ 否 → 移至 accepted 回调内调用
└── createCoGuestView 是否正确返回并 addSubview？
        └─ 检查 VideoViewDelegate 实现
```

## 关联知识

- **[live/coguest-invite](live/coguest-invite.md)** — 主播主动邀请观众连麦的反向流程
- **[live/device-control](live/device-control.md)** — 连麦通过后开设备、断开后关设备的具体操作
- **[live/beauty](live/beauty.md)** — 连麦中主播/观众可叠加美颜效果
- **[live/audience-watch](live/audience-watch.md)** — 非连麦观众观看连麦画面的拉流场景
