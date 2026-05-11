---
id: conference/video-layout
platform: web
api_docs:
  - title: 视频布局
    url: https://cloud.tencent.com/document/product/647/126921
---

# 视频布局 — Web 实现

## 前置条件
**通用依赖**：见 [login-auth 平台 slice](../login-auth.md)。

**额外依赖**：
- 已安装 `tuikit-atomicx-vue3@latest`

**前置状态**：
- 已阅读 `conference/video-layout`，明确当前能力的产品边界。
- 已完成 `conference/login-auth`，确保当前页面具备稳定登录态。
- 已根据业务流程接入会议上下文；需要进房状态时，优先通过 `conference/room-lifecycle` 统一承接。
- 承载 `RoomView` 的父容器必须具备明确宽高，否则视频区域无法正确计算布局。

## 最佳实践
### 1. 没给布局要求时直接用 `RoomView`，超出支持范围再切 `RoomParticipantView`
如果客户没有明确给到布局信息，或者只是提出常规会议布局诉求，最佳实践就是直接使用 `RoomView` 作为视频区域主容器。它已经承接了房间内参与者流的排序、播放、布局排版和缩放处理，成员列表、底部工具栏、聊天面板、业务弹窗等仍应由业务页面自行组合。

以下诉求通常**仍属于 `RoomView` 可覆盖范围**：
- 只是在 `GridLayout`、`CinemaLayout`、`SidebarLayout`、`MobileLayout` 之间选择或切换。
- 只是在画面上叠加昵称、角色、共享标识等挂件 UI。
- 只需要响应双击聚焦，或者根据共享状态、人数变化自动切换布局。

以下诉求通常可以判断为**超出 `RoomView` 支持范围**：
- 客户明确指定某一路流必须固定在某个区域，或要求每一路画面的大小、位置、层级都由业务自己决定。
- 视频区需要和白板、文档、字幕、AI 面板等业务模块做深度交错排版，而不是只在 `RoomView` 外围组合页面。
- 需要非标准布局编排，无法落在 `GridLayout`、`CinemaLayout`、`SidebarLayout`、`MobileLayout` 这些既有模板内。
- 需要业务侧自己接管主画面选择、排序或分区编排逻辑，而不是沿用 `RoomView` 的内置规则。

只有当客户明确提出了这类 `RoomView` 无法承接的布局诉求时，才建议切到 `RoomParticipantView` 这类单路播放原子组件逐路拼装。此时组件尺寸由外层布局决定，通常建议外层优先保持接近 `16:9` 的宽高比例，避免出现过度裁切或留白。

如果最终选择 `RoomParticipantView`，就需要在方案、文档或生成代码说明里**明确指明超出点**：至少写清楚是哪一条布局诉求超出了内置模板、挂件扩展或默认交互能力；如果说不清，默认就先用 `RoomView`。

### 2. 通用会议中让布局切换跟随共享和人数变化
- 有屏幕分享时，推荐自动切到 `RoomLayoutTemplate.SidebarLayout`，突出共享主画面。
- 没有屏幕分享，或者房间内仅有一个人的时候，推荐自动切回 `RoomLayoutTemplate.GridLayout`。
- 如果业务还提供手动切布局入口，建议让手动选择和这套默认回退规则保持一致。

### 3. PC 与 H5 使用不同布局策略
- PC Web 通用会议的常用布局主要是 `GridLayout`、`CinemaLayout`、`SidebarLayout`。
- H5 页面优先使用 `MobileLayout`，不要直接照搬桌面端布局。
- 屏幕共享开始时，PC 常见做法是切到 `SidebarLayout`；H5 通常继续使用 `MobileLayout`。

### 4. 把挂件定制放到 `participantViewUI`，并区分摄像头流与共享流
同一个挂件模板不应该机械复用于所有画面。共享流更适合展示“正在共享屏幕”等信息，摄像头流更适合展示昵称、角色和设备状态。

### 5. 避免挂件层拦截默认交互
如果挂件只是展示信息，优先给挂件容器设置 `pointer-events: none`，避免影响默认双击、拖拽或移动端手势。

## 布局能力矩阵

| 布局 | 枚举值 | 适用端 | 推荐场景 | 关键说明 |
|------|--------|--------|----------|----------|
| 宫格布局 | `RoomLayoutTemplate.GridLayout` | PC Web | 多人讨论、常规会议、视频面试 | 默认布局；单页通常最多展示 9 路，超过后通过翻页查看 |
| 顶部栏布局 | `RoomLayoutTemplate.CinemaLayout` | PC Web | 培训、演示、共享讲解 | 主画面居中突出，其他成员画面位于顶部 |
| 侧边栏布局 | `RoomLayoutTemplate.SidebarLayout` | PC Web | 主讲人模式、汇报场景 | 主画面居中突出，其他成员画面位于侧边 |
| 移动端布局 | `RoomLayoutTemplate.MobileLayout` | H5 | 移动端会议页 | 更强调主画面、滑动分页；共享场景下通常继续沿用该布局 |

## 代码示例
### 基础接入：渲染 `RoomView` 并选择布局模板

```vue
<template>
  <div class="room-view-wrapper">
    <RoomView :layout-template="currentLayout" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { RoomLayoutTemplate, RoomView } from 'tuikit-atomicx-vue3/room';

const currentLayout = ref(RoomLayoutTemplate.GridLayout);
</script>

<style scoped>
.room-view-wrapper {
  width: 100%;
  height: 100%;
}
</style>
```

### 自定义挂件：通过 `participantViewUI` 展示昵称、角色和共享标识

```vue
<template>
  <div class="room-view-wrapper">
    <RoomView :layout-template="currentLayout">
      <template #participantViewUI="{ participant, streamType }">
        <div class="participant-view-ui">
          <span class="name">{{ participant.nameCard || participant.userName || participant.userId }}</span>
          <span v-if="streamType === VideoStreamType.Screen" class="tag">正在共享屏幕</span>
          <span v-else class="tag">{{ participant.role }}</span>
        </div>
      </template>
    </RoomView>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import {
  RoomLayoutTemplate,
  RoomView,
  VideoStreamType,
} from 'tuikit-atomicx-vue3/room';

const currentLayout = ref(RoomLayoutTemplate.GridLayout);
</script>

<style scoped>
.room-view-wrapper {
  width: 100%;
  height: 100%;
}

.participant-view-ui {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: flex-end;
  padding: 8px;
  gap: 8px;
  color: #fff;
  pointer-events: none;
}

.tag {
  padding: 2px 8px;
  border-radius: 999px;
  background: rgb(0 0 0 / 50%);
}
</style>
```

### 状态驱动：共享开始时切到侧边栏，无共享或单人时回到宫格

```ts
import { computed, ref, watch } from 'vue';
import {
  RoomLayoutTemplate,
  useRoomParticipantState,
} from 'tuikit-atomicx-vue3/room';

const currentLayout = ref(RoomLayoutTemplate.GridLayout);
const { participantList, participantWithScreen } = useRoomParticipantState();

const participantCount = computed(() => participantList.value.length);

watch(
  [participantWithScreen, participantCount],
  ([screenParticipant, count]) => {
    if (screenParticipant) {
      currentLayout.value = RoomLayoutTemplate.SidebarLayout;
      return;
    }

    if (count <= 1) {
      currentLayout.value = RoomLayoutTemplate.GridLayout;
      return;
    }

    currentLayout.value = RoomLayoutTemplate.GridLayout;
  },
  { immediate: true },
);
```

### 交互回调：监听 `stream-double-click` 同步业务 UI 状态

```vue
<template>
  <div class="room-view-wrapper">
    <RoomView
      :layout-template="currentLayout"
      @stream-double-click="handleStreamDoubleClick"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import {
  RoomLayoutTemplate,
  RoomView,
  type VideoStreamType,
  type RoomParticipant,
} from 'tuikit-atomicx-vue3/room';

const currentLayout = ref(RoomLayoutTemplate.SidebarLayout);
const focusedStream = ref<string>('');

function handleStreamDoubleClick(payload: {
  participant: RoomParticipant;
  streamType: VideoStreamType;
}) {
  focusedStream.value = `${payload.participant.userId}:${payload.streamType}`;
}
</script>

<style scoped>
.room-view-wrapper {
  width: 100%;
  height: 100%;
}
</style>
```

## 调用时序
```
完成 login-auth 并进入会议
   │
   ▼
为 RoomView 准备有明确宽高的父容器
   │
   ▼
根据当前平台选择初始 layoutTemplate
   │
   ├─ PC 常规会议 → GridLayout
   ├─ PC 共享 / 主讲场景 → SidebarLayout / CinemaLayout
   └─ H5 页面 → MobileLayout
   │
   ▼
渲染 RoomView，并按需接入 participantViewUI / stream-double-click
   │
   ▼
监听 participantWithScreen、成员状态和业务焦点变化
   │
   ├─ 共享开始 → 切主画面布局
   ├─ 共享结束 → 回退到默认布局
   └─ 双击画面 → 同步业务侧焦点态或辅助 UI
   │
   ▼
离房或销毁页面时清理布局相关本地状态
```

## 平台特有注意事项
### 1. 父容器尺寸是 `RoomView` 正常工作的前提
如果外层容器宽高为 `0`，布局和画面渲染都会异常；这通常不是 SDK 本身的问题，而是页面容器没有被正确撑开。

### 2. `RoomView` 不负责进房和开关设备
如果页面没有画面，先检查是否已经进房，以及本地 / 远端是否真的存在可展示的视频或共享流，而不是只盯着布局组件本身。

### 3. 布局切换必须使用 `RoomLayoutTemplate` 枚举
不要手写字符串，也不要让 PC 使用 `MobileLayout`，或让 H5 强行复用桌面端宫格 / 顶部栏 / 侧边栏布局。

### 4. 共享画面和摄像头画面的挂件语义不同
共享流更适合展示“正在共享屏幕”等状态；摄像头流更适合展示昵称、角色、设备态和业务标签。

### 5. 只有明确超出 `RoomView` 能力边界时，才改用 `RoomParticipantView`
如果客户没有提出特殊布局要求，或者需求本身仍可落在 `RoomView` 的既有布局能力里，就不要过早切到单路播放器方案。只有在业务明确要求自己决定每一路流放在哪里、占多大区域、如何与其他业务模块交错排布时，才更适合使用 `RoomParticipantView` 这类单路播放组件逐路拼装。此时建议优先由外层容器控制宽高比例，通常保持接近 `16:9` 更利于常规摄像头和共享画面的展示。

### 6. 不要破坏 `RoomView` 的可视区域判断
多路画面场景下，非可视区域通常按需渲染，小画面也会采用更轻量的展示策略；自定义样式不应破坏其容器尺寸和可视区域计算。

### 7. H5 重点关注移动端手势和分页体验
`MobileLayout` 更关注主画面可读性、滑动分页和共享场景适配；移动端页面不建议强行复用桌面端的宫格或主讲布局思路。

## RoomView 内置行为

### 默认排序参考

| 优先级 | 排序因素 | 说明 |
|--------|----------|------|
| 1 | 屏幕共享流 | 有共享时，共享画面通常优先进入视频流列表 |
| 2 | 房主 | 房主画面优先级较高 |
| 3 | 本地用户 | 本地用户通常具有较高展示优先级 |
| 4 | 管理员 | 管理员画面优先于普通成员 |
| 5 | 摄像头和麦克风都开启 | 音视频都活跃的成员优先 |
| 6 | 仅开启摄像头 | 有视频画面的成员优先于仅音频成员 |
| 7 | 仅开启麦克风 | 只有音频状态的成员次之 |

> `RoomView` 会基于这些规则继续处理房间内参与者流的播放、布局排版和缩放。通用会议通常不需要业务侧自行重排；如果客户没有明确提出超出其能力边界的布局诉求，就应优先继续使用 `RoomView`。只有布局要求已经超出其支持范围时，才更适合改用 `RoomParticipantView` 一类单路组件自行组织。

### 主画面选择参考

| 场景 | 选择规则 |
|------|----------|
| 宫格布局 | 通常不强调单独主画面，而是按分页展示当前页画面 |
| 顶部栏 / 侧边栏布局 | 优先展示用户双击聚焦的画面；否则展示屏幕共享；再否则展示首个适合放大的视频画面；最后兜底本地用户 |
| 移动端布局 | 优先保障共享或主要画面的可读性，多人场景通过分页组织其余画面 |

### 渲染策略
- 非可视区域的远端画面通常按需渲染，不需要误判为播放异常。
- 小窗口和边栏画面通常会采用更轻量的展示策略，主画面和共享画面优先保证体验。

## 代码生成约束
### 编译必要条件
- **通用条件**：见 [login-auth 平台 slice](../login-auth.md)。
- **额外导入**：常规场景至少需要导入 `RoomView` 与 `RoomLayoutTemplate`；按需导入 `VideoStreamType`、`useRoomParticipantState`；只有在明确超出 `RoomView` 布局能力时，才额外导入 `RoomParticipantView`。
- **运行前提**：页面已经进入会议流程，且 `RoomView` 父容器具备明确宽高。

### 生成规则
#### MUST（生成时必须包含）

1. **客户未明确提出特殊布局时，默认以 `RoomView` 作为视频区域主容器** — 这是通用会议和常规布局诉求的最佳实践。  
   **Verify**: 检查常规会议场景是否优先存在 `RoomView` 渲染节点。
2. **显式为 `RoomView` 的父容器设置宽高** — 否则布局无法正常计算。  
   **Verify**: 检查外层容器是否存在 `width` / `height` 样式。
3. **使用 `RoomLayoutTemplate` 枚举管理布局模板** — 这样 PC 与 H5 的布局策略才可控。  
   **Verify**: 检查是否存在 `RoomLayoutTemplate.GridLayout` / `SidebarLayout` / `CinemaLayout` / `MobileLayout`。
4. **挂件扩展优先走 `participantViewUI` 插槽** — 这样挂件能跟随成员和流类型状态同步更新。  
   **Verify**: 检查是否存在 `participantViewUI` 插槽或等价扩展点。
5. **需要响应画面交互时，优先监听 `stream-double-click`** — 用于同步业务侧焦点态或辅助交互。  
   **Verify**: 检查是否绑定了 `@stream-double-click` 或等价处理逻辑。
6. **共享场景下通过 `participantWithScreen`、成员人数等状态驱动布局切换** — 不要用硬编码定时器或手工 DOM 调整主画面。  
   **Verify**: 检查是否读取共享状态和成员数量，并在共享时切到 `SidebarLayout`、无共享或单人时回到 `GridLayout`。
7. **只有明确超出 `RoomView` 支持范围时，才切到单路播放组件** — 当业务不再采用通用会议布局容器，而是要自行决定每一路画面的尺寸、比例和排布时，再由外层接管布局。  
   **Verify**: 检查自定义布局方案是否先说明了 `RoomView` 不能满足的点，并补充单路组件的尺寸约束，且优先保持接近 `16:9` 的画面比例。

#### MUST NOT（生成时绝不能出现）

1. **不要把 `RoomView` 当成完整会议页面组件** — 它不承载成员列表、会控面板或聊天区域。  
   **Verify**: 检查实现是否仍保留页面装配层。
2. **不要手写布局枚举字符串或跨平台误用布局模板** — 会直接导致布局行为偏离官方能力。  
   **Verify**: 检查模板切换是否全部基于 `RoomLayoutTemplate`。
3. **不要让纯展示型挂件默认拦截交互** — 会影响双击、拖拽或移动端手势。  
   **Verify**: 检查挂件层是否使用 `pointer-events: none` 或把点击区限制在局部元素上。
4. **不要在客户没提特殊布局时绕开 `RoomView` 自己手工编排全部视频 DOM** — 除非业务明确提出 `RoomView` 无法覆盖的布局诉求，并接受逐路管理播放区域和尺寸约束。  
   **Verify**: 检查通用会议或常规布局场景是否仍以 `RoomView` 作为主容器。
5. **不要在自定义单路布局里放任画面比例失控** — 过窄、过高或随内容抖动的容器会明显影响播放体验。  
   **Verify**: 检查单路播放器外层是否具备稳定尺寸，且优先保持接近 `16:9`。
6. **不要把“非可视区域按需渲染”误判为流异常** — 先确认是否属于布局容器的正常策略。  
   **Verify**: 检查排障说明是否区分布局策略与真实故障。

### 集成检查点
- 当前 slice 常与 `conference/room-lifecycle`、`conference/screen-share`、`conference/participant-list`、`conference/device-control` 联动。
- 集成方式通常是在会议主页面中先新增一个 `RoomView` 容器，再按需扩展挂件和布局切换逻辑；只有当客户明确提出 `RoomView` 之外的布局诉求时，再切到 `RoomParticipantView` 逐路拼装。
- 如果业务已有完整自定义会议 UI，仍建议优先保留“页面装配层 / RoomView 布局层 / 挂件层”三层分工；只有布局能力明确不匹配时，再升级为单路播放器方案。

## 验证矩阵
| 层级 | 检查项 | 验证手段 | 预期结果 |
|------|--------|----------|---------|
| 1. 编译级 | 已导入 `RoomView`、`RoomLayoutTemplate` 等核心依赖 | 检查 `import` 语句 | 布局组件与枚举可正常解析 |
| 2. 静态规则级 | 组件选型、布局模板、父容器尺寸、插槽与事件都配置完整 | 搜索 `RoomView`、`RoomParticipantView`、`participantViewUI`、`stream-double-click`、容器样式 | 常规场景优先使用 `RoomView`，超出能力边界时才切单路组件 |
| 3. 运行时级 | 共享开始、布局切换、双击交互都能生效 | 在会议中触发共享和双击画面 | 主画面与布局行为符合预期 |
| 4. 业务行为级 | 会议页面画面层清晰、挂件不挡交互、移动端策略正确 | 在 PC / H5 页面分别验证 | 视频区域可读、可控且与官方能力一致 |
