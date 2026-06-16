---
name: trtc-room-builder
description: "INTERNAL skill — only invoked by trtc-topic during scenario execution. Do NOT trigger directly from user messages. Provides official RoomKit integration rules and the bundled medical consultation template. Always route user requests through trtc-onboarding first."
---

# TRTC Room Builder

把官方 RoomKit 会议能力集成进现有 Vue 3 应用，或在医疗在线问诊全新项目场景下
复制内置模板。

- **Official RoomKit 集成模式**：官方 RoomKit 组件 + 官方 API → 快速接入现有业务应用，并通过官方扩展点微调界面
- **医疗在线问诊新项目模板**：完整复制内置医疗问诊项目模板

> 本 skill 不再提供 full-ui 自定义会议界面生成路径。

---

## Invocation entry points

本 skill 由 `../trtc-topic/SKILL.md` 在 `official-roomkit` 会议 UI 集成模式下消费。

当用户在 onboarding A2-Q0.5 选择"官方 UI"时，
`${CLAUDE_PROJECT_DIR}/.trtc-session.yaml` 会写入
`ui_mode: official-roomkit`。topic 读取本 skill 的"官方 RoomKit 集成模式"
作为生成规范，集成官方组件并使用官方 API 微调界面。

---

## 官方 RoomKit 集成模式

当用户要在**已有 Vue 3 项目中集成会议/接入多人会议/接入 TUIRoomKit/使用官方
RoomKit** 时，走官方 RoomKit 集成模式。

### 触发关键词

- 中文：集成会议、接入会议、多人会议 SDK、视频会议 SDK、官方 RoomKit、
  TUIRoomKit、含 UI 集成、快速接入、界面微调
- 英文：integrate meeting, add conference, official RoomKit, TUIRoomKit,
  Web&H5 Vue3, customize RoomKit UI

### 实施规则

1. 使用官方 Web RoomKit 包；如果要使用界面微调 API，必须确认 lockfile 中实际解析到的
   `@tencentcloud/roomkit-web-vue3` 版本 `>=5.4.3`。安装
   `@tencentcloud/roomkit-web-vue3@5` 可以作为官方大版本入口，但不能接受解析到
   `<5.4.3` 的既有依赖。并按官方快速接入文档安装相关包：
   `tuikit-atomicx-vue3`、`@tencentcloud/uikit-base-component-vue3`、
   `@tencentcloud/universal-api`。
2. 页面层渲染官方组件：PC 使用 `ConferenceMainView`，H5 使用
   `ConferenceMainViewH5`（二者从 `@tencentcloud/roomkit-web-vue3` 导入），
   外层包裹 `UIKitProvider`（从 `@tencentcloud/uikit-base-component-vue3` 导入），
   并根据业务需要设置 `theme="light" | "dark"`、`language="zh-CN" | "en-US"`。
3. 登录与房间生命周期使用官方 `conference` API：`conference.login()`、
   `conference.setSelfInfo()`、`conference.createAndJoinRoom()`、
   `conference.joinRoom()`、`conference.leaveRoom()`、`conference.endRoom()`、
   `RoomEvent` 监听。
4. 房间号 `roomId` 必须来自业务系统或由业务系统保证唯一；在线问诊、1v1 客服等
   双方不确定谁先建房的场景，可统一用业务单据号作为 `roomId` 并调用
   `conference.createAndJoinRoom()`。
5. UserSig 处理必须复用 `skills/trtc-onboarding/reference/usersig-handling.md`
   的规则：生成占位符 `userSig` + 引导用户去 TRTC 控制台获取测试 UserSig 填入
   (skill 不自动签发)，正式环境由业务后端签发；前端只保留
   `SDKAppID / userId / userSig` 输入项或占位。
   不要生成 `src/utils/usersig.ts`，不要在前端依赖 `SecretKey`，不要用 `crypto-js`、
   `pako`、`HmacSHA256` 或 `tls-sig-api-v2` 在浏览器端签名。
6. 按钮、工具栏、内置按钮点击前拦截只使用官方界面微调 API：
   `conference.setWidgetVisible()` 隐藏/恢复内置按钮，
   `conference.registerWidget()` 添加自定义业务按钮或侧边面板，
   `conference.onWill()` 拦截内置按钮点击前的操作。
7. `setWidgetVisible()`、`registerWidget()`、`onWill()` 尽量放在
   `conference.login()` 成功之后、`conference.createAndJoinRoom()` /
   `conference.joinRoom()` 之前，避免按钮闪烁或拦截器漏掉早期操作。
8. `conference.setFeatureConfig()` 只用于官方文档定义的特性配置。尤其是
   `shareLink` 必须在 `conference.createAndJoinRoom()` / `conference.joinRoom()`
   成功后立即设置，确保使用最终确定的 `roomId`。
9. `registerWidget()` 和 `onWill()` 返回的注销函数必须统一收集，并在
   `RoomEvent.ROOM_LEAVE` 和 `RoomEvent.ROOM_DISMISS` 两个事件里清理，避免多次进出
   房间后重复注册。

### 禁止事项

- 不要复制已移除的 full-ui 主题资产到客户项目，也不要要求生成的 Vue 组件满足
  `ui-*` class 数量规则。
- 不要手写一套替代 RoomKit 主界面的会议 SFC；官方组件承担会议主界面，业务侧只
  负责外层路由、登录、房间号、事件监听和官方 UI 微调 API。
- 不要生成前端 UserSig 签名器，尤其不要生成 `src/utils/usersig.ts`、不要把
  `SecretKey` 放进 `src/config.ts`、不要新增 `crypto-js` / `pako` / `tls-sig-api-v2`
  这类仅用于浏览器端签名的依赖。
- 不要用 CSS 选择器或 DOM hack 修改 RoomKit 内部按钮显隐、点击前权限和工具栏
  扩展；这些需求必须使用 `setWidgetVisible()`、`registerWidget()`、`onWill()`。
- 不要在进房前写死 `setFeatureConfig({ shareLink })`；分享链接依赖最终 `roomId`，
  应在 `createAndJoinRoom()` / `joinRoom()` 成功后设置。

### API 签名与代码示例

> **所有 `conference` 适配层 API 的完整签名、枚举定义和集成示例已移至
> `knowledge-base/slices/conference/web/official-roomkit-api.md`。**
>
> 生成 official-roomkit 模式代码前，**必须先 Read 该 slice 文件**，
> 使用其中经过源码验证的签名，不得自行推测参数。

参考文档：

- 快速接入 Web&H5 (Vue3)：<https://cloud.tencent.com/document/product/647/81962>
- 界面微调 (Web)：<https://cloud.tencent.com/document/product/647/129842>

---

## 医疗在线问诊新项目直拷规则

当用户需求落在医疗在线问诊（例如 `1v1-video-consultation`、远程问诊、
医生/患者视频问诊、在线诊疗）并且明确是**生成全新项目**，不要进入 full-ui
自定义界面生成、theme-copy、手写 Vue SFC 或任何 verifier 流程。

直接把本 skill 内置模板目录完整复制到用户指定的本地项目目录：

```text
skills/trtc/room-builder/templates/scenarios/medical-consultation/
```

复制时保留模板项目的文件结构、路由、样式、服务适配器、mock 数据和文档。
交付或接入说明中必须提醒客户使用 `pnpm install` 安装依赖，并使用
`pnpm dev` 启动本地开发服务；不要推荐 `npm install` / `npm run dev`，因为
该医疗模板使用 npm 启动会明显变慢，首屏可能白屏一段时间。
本规则只适用于全新医疗问诊项目；对既有项目做集成/改造时，继续按
scenario / official-roomkit 规则处理。

## 资源目录

```text
trtc/room-builder/
├── SKILL.md
├── templates/
│   └── scenarios/
│       └── medical-consultation/
└── tools/
    └── render_ai_instructions.py
```
