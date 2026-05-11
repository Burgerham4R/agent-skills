## Conference 通用会议场景（general-meeting）Slice 映射

## 结论

如果客户说的是 **常规会议 / 标准视频会议 / 多人会议 / 在线会议 / 团队会议 / 远程协作会议**，那么在当前 `conference` 体系里，优先命中的不应是某一个孤立能力，而应是一组围绕 **房间生命周期、参会人状态、画面布局、设备稳定性、会中协作** 展开的默认会议主链路 slices。

与医疗、教育这类行业场景不同，常规会议本身就是 `conference` 的默认问题域，因此更适合按 **“主链路优先，增强能力按需补齐”** 的方式来理解和命中。

同时要补一条明确的**识别失败兜底规则**：如果需求分析阶段**未能识别出教育场景、医疗场景或 webinar 场景**，但用户描述的仍然是多人实时音视频沟通、多人进房、参会人管理、画面布局、设备控制、网络稳定性、主持控场这类典型会议能力，那么应**统一回落到 `general-meeting`（通用会议）场景**，不要让这类需求悬空。

**第一优先级主命中**：

- `conference/login-auth`
- `conference/room-lifecycle`
- `conference/participant-list`
- `conference/video-layout`
- `conference/device-control`
- `conference/network-quality`

**第二优先级常见增强**：

- `conference/prejoin-check`
- `conference/room-config`
- `conference/participant-management`
- `conference/room-moderation`
- `conference/room-chat`
- `conference/screen-share`

**按显式需求补命中**：

- `conference/room-schedule`
- `conference/room-invite`
- `conference/beauty-effects`
- `conference/virtual-background`

---

## 为什么这些是通用会议的默认主命中

### 1. 通用会议的核心目标是“把一场会稳定地开起来并顺畅地开下去”

多数客户说“做一个会议场景”时，第一反应通常不是白板、考试、会诊台这类行业能力，而是：

- 用户怎么登录进入会议系统
- 主持人怎么创建会议，成员怎么进入会议
- 会议里有哪些人、谁在说话、角色怎么展示
- 画面怎么排布、共享时主画面怎么切换
- 摄像头、麦克风、扬声器怎么稳定使用
- 弱网、断线、重连时怎么提示和恢复

这决定了通用会议的第一层命中，应该始终围绕 **登录 → 房间生命周期 → 参会人状态 → 视频布局 → 设备与网络稳定性** 展开。

### 2. 通用会议更适合“默认骨架先成立，再叠加高级能力”

当用户说“做通用会议 / 做一个会议产品”时，最合理的命中方式应理解为：

- 先命中 **接入前提**：`login-auth`
- 再命中 **房间主链路**：`room-lifecycle`
- 再命中 **参会人和画面状态层**：`participant-list`、`video-layout`
- 再命中 **稳定性底座**：`device-control`、`network-quality`
- 最后再根据是否涉及会前检测、主持控制、屏幕共享、预约会议、会中补邀、视觉增强，补命中其他 slices

---

## 需求点到 Slice 的映射

| 通用会议需求点 | 主要命中 slices | 判断原因 |
|---|---|---|
| 用户登录并进入会议系统 | `conference/login-auth` | 所有会议能力都建立在统一鉴权和会话有效性的前提上。 |
| 创建会议、加入会议、离开会议、结束会议 | `conference/room-lifecycle` | 通用会议最核心的主链路就是房间生命周期；它已经统一覆盖创建、加入、离开、恢复和结束。 |
| 服务端预创建会议、会后统一解散会议 | `conference/room-lifecycle`, `conference/room-schedule` | REST API 代创建 / 代解散本质仍属于房间生命周期；若涉及未来时间排期，则与 `room-schedule` 组合命中。 |
| 显示参会人列表、角色、发言态、设备态 | `conference/participant-list` | 会议内“谁在场、谁是什么状态”都汇总在这里。 |
| 宫格布局、主讲视图、共享时主画面切换 | `conference/video-layout`, `conference/screen-share` | 画面呈现由 `video-layout` 承担，共享状态由 `screen-share` 提供并驱动画面切换。 |
| 摄像头、麦克风、扬声器的开关、切换和异常恢复 | `conference/device-control` | 会中设备控制属于通用会议的基础底座能力。 |
| 弱网提示、超时告警、断线恢复建议 | `conference/network-quality`, `conference/room-lifecycle` | 一个负责网络稳定性观测，一个负责真正的离房收口和重入恢复。 |
| 入会前做设备检测和本地预览 | `conference/prejoin-check` | 会前设备自检是常见增强能力，但不是所有通用会议都必须强展示。 |
| 设置会议主题、密码、默认禁麦等初始规则 | `conference/room-config` | 这是会议在发起前被定义的配置层。 |
| 房主管理成员、踢人、设管理员、角色治理 | `conference/participant-management` | 这是“谁能留在会里、谁能做什么”的治理问题。 |
| 会中全员禁麦、禁摄、禁聊、禁共享 | `conference/room-moderation` | 通用会议的主持与秩序控制由它承接。 |
| 会中聊天、消息互动、历史消息和禁聊联动 | `conference/room-chat` | 会议里的文本协作入口落在这里。 |
| 屏幕共享、演示文档、汇报讲解 | `conference/screen-share`, `conference/video-layout`, `conference/room-moderation` | 共享是媒体能力，布局负责响应，会控负责约束共享权限。 |
| 预约会议、会议排期、到点提醒 | `conference/room-schedule`, `conference/room-lifecycle` | 排期属于未来时间维度；到点后真正进房和结束仍回到房间生命周期。 |
| 会中临时补邀、拉人入会 | `conference/room-invite`, `conference/participant-management`, `conference/room-lifecycle` | 邀请是信令链路，谁有权发起由成员治理约束，真正进房回到房间生命周期。 |
| 未识别出教育、医疗或 webinar 专属场景，但需求仍是多人音视频会议 | `conference/login-auth`, `conference/room-lifecycle`, `conference/participant-list`, `conference/video-layout`, `conference/device-control`, `conference/network-quality` | 这类需求本质仍是通用会议主链路，只是上层场景分类没有命中，应统一回落到通用会议骨架。 |
| 美颜、虚化、背景替换等体验增强 | `conference/beauty-effects`, `conference/virtual-background`, `conference/device-control` | 这些是通用会议里的常见增强项，但不属于默认主链路。 |

---

## 主命中分层建议

### P0 默认会议骨架

这些 slice 足以支撑大多数“通用会议产品”的第一层理解：

- `conference/login-auth`
- `conference/room-lifecycle`
- `conference/participant-list`
- `conference/video-layout`
- `conference/device-control`
- `conference/network-quality`

### P0 常见增强能力

这些 slice 在正式会议产品里非常常见，但是否前置命中，要看用户是否明确提到对应动作：

- `conference/prejoin-check`
- `conference/room-config`
- `conference/participant-management`
- `conference/room-moderation`
- `conference/room-chat`
- `conference/screen-share`

### P1 按需补命中

这些 slice 更依赖会议形态或业务流程是否明确：

- `conference/room-schedule`：预约会议、未来会议、到点提醒
- `conference/room-invite`：会中补邀、拉人入会
- `conference/beauty-effects`：本地美颜增强
- `conference/virtual-background`：背景虚化与替换

---

## 典型通用会议子场景的命中差异

### 1. 日常团队会议

优先命中：

- `conference/login-auth`
- `conference/room-lifecycle`
- `conference/participant-list`
- `conference/video-layout`
- `conference/device-control`
- `conference/network-quality`
- `conference/room-chat`

这类场景更强调默认主链路、稳定性和轻协作。

### 2. 主持型宣讲 / 培训会议

在默认会议骨架基础上补命中：

- `conference/room-config`
- `conference/room-moderation`
- `conference/screen-share`
- `conference/participant-management`

这类场景更依赖主持秩序、共享展示和参会人治理。

### 3. 预约式正式会议

在默认会议骨架之外补命中：

- `conference/room-schedule`
- `conference/room-config`
- `conference/room-lifecycle`

如果业务由后台通过 REST API 先建房、到点后用户再进入，这仍然属于 `room-schedule + room-lifecycle` 的组合，不需要单独再拆服务端 slice。

### 4. 会中补邀的协作会议

补命中：

- `conference/room-invite`
- `conference/participant-management`
- `conference/room-lifecycle`

这类场景强调“邀请确认”和“真正进房”是两段链路。

### 5. 对视觉体验要求较高的会议

补命中：

- `conference/beauty-effects`
- `conference/virtual-background`
- `conference/device-control`

这类场景更关注本地视频前处理与展示体验，而不是会议骨架本身。

---

## 当前体系判断

通用会议场景基本就是当前 `conference` 目录的默认落点，因此：

- 不需要再单独补一个“通用会议专属底层 slice”
- 更重要的是把默认命中顺序排清楚，避免一开始就把预约、补邀、美颜、虚拟背景这些次级能力抬成主入口
- 如果未来要增强“通用会议产品感”，更适合补的是装配层或样板工程，而不是重新拆分底层问题域

---

## 触发"`general-meeting` 场景"时的推荐命中策略

### 用户出现以下意图时，优先命中 P0 默认会议骨架

- 通用会议场景
- 标准视频会议
- 多人会议
- 在线会议
- 团队会议
- 远程协作会议
- 做一个会议产品
- 创建会议并加入
- 开一个多人视频会
- 实现会议功能

### 未识别出教育 / 医疗 / webinar 场景时的兜底处理

- 如果场景识别阶段没有稳定命中教育场景、医疗场景或 webinar 场景，不要直接丢失这类需求。
- 只要用户描述仍然落在"多人实时音视频开会"这条主线上，就应统一回落到 `general-meeting` 场景。
- 这里的"多人实时音视频开会"可包含：多人进房、主持控场、参会人列表、宫格 / 主讲布局、设备切换、网络质量、会中聊天、共享演示等通用会议能力。

### 再按显式词补命中增强 slices

- 提到“会前检测 / 麦克风测试 / 摄像头测试” → `conference/prejoin-check`
- 提到“密码会议 / 默认禁麦 / 会议主题 / 初始规则” → `conference/room-config`
- 提到“踢人 / 设管理员 / 成员管理” → `conference/participant-management`
- 提到“禁麦 / 禁摄 / 禁聊 / 主持人控场” → `conference/room-moderation`
- 提到“聊天 / 会中消息 / 文本协作” → `conference/room-chat`
- 提到“共享屏幕 / 演示 / 汇报” → `conference/screen-share`, `conference/video-layout`
- 提到“预约 / 排期 / 到点入会” → `conference/room-schedule`
- 提到“补邀 / 拉人入会 / 邀请在线用户” → `conference/room-invite`
- 提到“美颜 / 背景虚化 / 背景替换” → `conference/beauty-effects`, `conference/virtual-background`
- 提到“后台创建房间 / 服务端解散房间 / REST API 建房” → `conference/room-lifecycle`, `conference/room-schedule`

---

## 一句话判断

**如果客户说要做通用会议场景，或者需求本来属于教育、医疗、webinar 等上层场景但当前没有被稳定识别出来，只要核心诉求仍是多人实时音视频会议，就应优先回落到一组以 `login-auth`、`room-lifecycle`、`participant-list`、`video-layout`、`device-control`、`network-quality` 为中心的默认会议骨架 slices；其他如会前检测、主持控制、共享、预约、补邀、美颜、虚拟背景等能力，再按显式需求补命中即可。**
