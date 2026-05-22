---
id: conference/room-lifecycle
platform: web
api_docs:
  - title: 房间管理
    url: https://cloud.tencent.com/document/product/647/126919
---

# 房间创建、加入、离开与结束 — Web 实现

## 前置条件
**通用依赖**：见 [login-auth 平台 slice](../login-auth.md)。

**额外依赖**：
- 已安装 `tuikit-atomicx-vue3@latest`

**前置状态**：
- 已阅读 `conference/room-lifecycle`，明确当前能力的产品边界。
- 已完成 `conference/login-auth`，确保当前页面具备稳定登录态。
- 已根据业务流程接入会议上下文；需要房间状态时，优先通过当前 slice 统一承接。

## 代码示例
### 场景一：房主 / 发起人直接创建并进入快速会议

```ts
import { useRoomState } from 'tuikit-atomicx-vue3/room';

const { createAndJoinRoom, currentRoom } = useRoomState();

await createAndJoinRoom({
  roomId: 'demo_room',
  options: { roomName: '演示会议' },
});

console.log(currentRoom.value?.roomId);
```

### 场景二：已知房间已经存在，直接加入

```ts
import { useRoomState } from 'tuikit-atomicx-vue3/room';

const { joinRoom, currentRoom } = useRoomState();

await joinRoom({
  roomId: 'demo_room',
});

console.log(currentRoom.value?.roomId);
```

### 场景三：只知道 `roomId`，但不确定房间是否已经存在

```ts
import { useRoomState } from 'tuikit-atomicx-vue3/room';

const { createAndJoinRoom, currentRoom } = useRoomState();

await createAndJoinRoom({
  roomId: 'demo_room',
  options: { roomName: '业务沟通房间' },
});

console.log(currentRoom.value?.roomId);
```

### 场景四：会议结束前正确收口

```ts
import { useRoomState } from 'tuikit-atomicx-vue3/room';

const { leaveRoom, endRoom } = useRoomState();

await leaveRoom();
// 房主结束会议：await endRoom();
```

### 处理房间结束与被动退房：监听房间被解散、被踢和异常退出

```ts
import { onMounted, onUnmounted } from 'vue';
import {
  useRoomParticipantState,
  useRoomState,
  RoomEvent,
  RoomParticipantEvent,
  KickedOutOfRoomReason,
} from 'tuikit-atomicx-vue3/room';

const { subscribeEvent, unsubscribeEvent } = useRoomState();
const {
  subscribeEvent: subscribeParticipantEvent,
  unsubscribeEvent: unsubscribeParticipantEvent,
} = useRoomParticipantState();

function onRoomEnded() {
  console.log('房主已结束会议');
}

function onKickedFromRoom({ reason }: { reason: KickedOutOfRoomReason; message: string }) {
  switch (reason) {
    case KickedOutOfRoomReason.KickedByAdmin:
      console.log('当前用户被房主或管理员移出房间');
      break;
    case KickedOutOfRoomReason.ReplacedByAnotherDevice:
      console.log('当前账号已在其他设备进入会议');
      break;
    case KickedOutOfRoomReason.ConnectionTimeout:
      console.log('网络连接超时，当前会议状态需要重新确认');
      break;
    default:
      console.log('当前用户已退出房间');
      break;
  }
}

onMounted(() => {
  subscribeEvent(RoomEvent.onRoomEnded, onRoomEnded);
  subscribeParticipantEvent(RoomParticipantEvent.onKickedFromRoom, onKickedFromRoom);
});

onUnmounted(() => {
  unsubscribeEvent(RoomEvent.onRoomEnded, onRoomEnded);
  unsubscribeParticipantEvent(RoomParticipantEvent.onKickedFromRoom, onKickedFromRoom);
});
```

## 调用时序
```
完成 login-auth
   │
   ▼
决定当前路径：创建会议 或 加入已有会议
   │
   ├─ 房主端 → createAndJoinRoom({ roomId, options })
   └─ 成员端 → joinRoom({ roomId })
   │
   ▼
以 currentRoom 作为会议内真实状态来源
   │
   ├─ 普通离开 → leaveRoom()
   ├─ 房主结束 → endRoom()
   └─ 会议被结束 → 通过事件和 currentRoom 变化收口 UI
```

## 平台特有注意事项
### 1. 登录真正就绪后再调用房间生命周期接口
`login()` 是异步动作。单页应用里更适合监听 `loginUserInfo.value?.userId` 或等价登录完成信号，确认用户身份已就绪后再调用 `createAndJoinRoom()`、`joinRoom()`、`leaveRoom()`、`endRoom()`。

### 2. `useRoomState` 是单例，同一时刻只承接一个房间上下文
同一用户同一时间通常只能处于一个有效房间内。切房前应先完成上一场会议的离房或结束收口，避免多个房间状态并存。

### 3. 按业务目标区分 `createAndJoinRoom()` 与 `joinRoom()`
如果当前用户就是房主 / 发起人，需要立即创建并进入一场新会议，应使用 `createAndJoinRoom()`；如果房间已经由发起人、会议列表、预约系统或服务端预先创建好，应使用 `joinRoom()`；如果双方只知道同一个 `roomId`，但无法预先判断房间是否存在，也更适合使用 `createAndJoinRoom()` 承接“存在则加入，不存在则创建”的场景。

调用 `joinRoom()` 时只需要传入 `roomId`；如果是密码房，再额外传入顶层 `password` 字段，例如 `joinRoom({ roomId, password })`。不要把密码或空对象包进 `options`，当前 Web API 的加入房间签名并不接收 `options`。

### 4. `leaveRoom()` 与 `endRoom()` 是两类不同动作
普通成员离开会议应调用 `leaveRoom()`；房主若要真正解散会议，需要调用 `endRoom()`，两者语义不能混用。

### 5. `currentRoom` 是会中真实状态源
即使房间由服务端预创建、预销毁或通过其他链路调度，前端仍要以 `currentRoom` 和实际入会流程作为最终真实状态来源。

### 6. 密码房和入会错误需要业务侧自行承接
加入密码房时，要准备好对 `ERR_NEED_PASSWORD`、`ERR_WRONG_PASSWORD` 等结果做输入与重试处理；若出现房间不存在、人数已满等错误，也应给出明确反馈，而不是只在控制台报错。

### 7. 被动退房最好通过事件与页面收口统一处理
房主结束会议、成员被踢、异地登录顶替、网络超时等情况，本质上都属于“被动离开当前房间”。业务层最好统一监听房间事件并收口页面，而不是分别在多个组件里零散兜底。

### 8. `roomId` 应由业务侧保证唯一性
建议由业务后端生成全局唯一 `roomId`，避免测试环境与正式环境、不同会议之间发生 ID 冲突或复用歧义。

### 9. 建房时传入的 `options` 更适合来自 `conference/room-config`
`room-lifecycle` 负责选择 `createAndJoinRoom()` 还是 `joinRoom()`，以及处理进入、离开和结束；`roomName`、`password`、默认规则等字段的维护与解释，更适合收口到 `conference/room-config`，避免在生命周期页面里再维护第二套配置语义。

## 常见错误与场景对照

| 错误 / 场景 | 常见触发时机 | 建议处理方式 |
|-------------|--------------|--------------|
| `ERR_NEED_PASSWORD` | 加入密码房但未传密码 | 弹出密码输入框，输入后再次调用 `joinRoom({ roomId, password })` |
| `ERR_WRONG_PASSWORD` | 输入的入会密码错误 | 提示密码错误，并允许用户修正顶层 `password` 后重试 |
| `ERR_ROOM_ID_NOT_EXIST` | 对不存在的房间调用 `joinRoom({ roomId })` | 提示房间不存在；若属于对等发起场景可改走 `createAndJoinRoom()` |
| `ERR_ROOM_USER_FULL` | 房间人数达到上限 | 提示房间已满，引导稍后重试或联系房主 |
| `ERR_ROOM_ID_OCCUPIED` | 创建时 `roomId` 已被占用 | 检查 `roomId` 生成策略；若允许“存在则加入”，优先使用 `createAndJoinRoom()` |
| `RoomEvent.onRoomEnded` | 房主结束当前会议 | 提示会议已结束，并退出会中页面 |
| `RoomParticipantEvent.onKickedFromRoom` | 当前用户被移出、被顶替或重连失败 | 根据 `reason` 区分提示文案，并回收当前会中状态 |

## 代码生成约束
### 编译必要条件
- **通用条件**：见 [login-auth 平台 slice](../login-auth.md)。
- **额外导入**：至少需要导入 `useRoomState`。
- **运行前提**：页面已具备有效登录态，且拿到可用的 `roomId`。

### 生成规则
#### MUST（生成时必须包含）

1. **通过 `useRoomState` 承接创建、加入、离开和结束会议的主链路** — 才能让状态与 UI 从同一来源收口。  
   **Verify**: 检查是否存在 `useRoomState()` 与生命周期 API 调用。
2. **在登录真正就绪后再触发房间生命周期动作** — 未确认登录完成时抢跑调用很容易导致状态异常。  
   **Verify**: 检查是否存在登录完成判断，例如监听 `loginUserInfo.value?.userId` 或等价登录完成信号。
3. **按业务目标选择 `createAndJoinRoom()` 或 `joinRoom()`** — 房主快速创建并入会、以及无法确认房间是否存在时，都更适合 `createAndJoinRoom()`；只有已知房间已存在时才直接使用 `joinRoom()`。  
   **Verify**: 检查是否把“房主创建并入会”“已知房间存在直接加入”“存在性未知时尝试进入”这三类路径明确区分。
4. **把 `currentRoom` 作为会中状态锚点** — 能避免页面层与房间真实状态漂移。  
   **Verify**: 检查是否读取 `currentRoom` 或围绕其变化更新页面。
5. **为密码房和常见入会错误预留业务反馈** — 无 UI 接入时，密码输入、重试和错误提示都需要页面自行承接。  
   **Verify**: 检查加入流程是否处理 `ERR_NEED_PASSWORD`、`ERR_WRONG_PASSWORD` 或等价失败提示。

#### MUST NOT（生成时绝不能出现）

1. **不要把 `leaveRoom()` 当成解散会议** — 会导致房主离开后房间仍在。  
   **Verify**: 检查房主结束逻辑是否明确调用 `endRoom()`。
2. **不要只信任服务端预创建结果而跳过前端真实入会状态判断** — 页面可能显示“已在会中”但底层并未入房。  
   **Verify**: 检查是否仍通过 `joinRoom()` / `createAndJoinRoom()` 与 `currentRoom` 收口。

### 集成检查点
- 当前 slice 是 `conference/web` 大多数能力的房间状态基座。
- 集成方式通常是新增页面路由状态或 ViewModel，不需要改 SDK 底层。
- 若业务同时存在预约会议、呼叫入会或服务端预创建房间，需要统一约定 `roomId` 和入会入口。

## 验证矩阵
| 层级 | 检查项 | 验证手段 | 预期结果 |
|------|--------|----------|---------|
| 1. 编译级 | 已导入 `useRoomState` | 检查 `import` 语句 | 房间生命周期 Hook 可解析 |
| 2. 静态规则级 | 进房路径、离开与结束动作分层明确 | 搜索 `joinRoom` / `createAndJoinRoom` / `leaveRoom` / `endRoom` | 进入、离开、结束职责清晰 |
| 3. 运行时级 | 创建 / 加入会议后 `currentRoom` 可用 | 进房并查看调试状态 | 可读取有效 `roomId` |
| 4. 业务行为级 | 密码房与错误提示、离开与结束后的页面状态正确收口 | 分别测试密码入会、离会与结束会议 | UI 与房间真实状态一致，失败时有明确反馈 |

---

> **official-roomkit 模式用户注意**：如果 `ui_mode = official-roomkit`，
> 房间操作通过 `conference` 对象而非直接 composable。
> 完整的 `conference` API 签名、枚举定义和代码示例见
> **[`conference/web/official-roomkit-api.md`](./official-roomkit-api.md)**。
