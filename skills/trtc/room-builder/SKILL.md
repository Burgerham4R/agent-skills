---
name: trtc-room-builder
description: "TRTC Room 产品搭建器。当用户需要搭建视频会议、语音房间、直播连麦、1v1通话、在线课堂等 room 类音视频产品的前端界面，或在既有 Vue3 应用中集成官方 RoomKit 会议能力时，此技能提供三条路径：有明确风格诉求时，优先使用 12 个精美模板或设计系统生成高风格感界面（Tailwind + 现代设计）；无明确风格诉求时，使用通用组件库（60 个组件 + Design Token）生成标准功能型界面；客户要快速接入/集成会议/官方 RoomKit 时，使用 @tencentcloud/roomkit-web-vue3 官方组件，并通过官方 API 进行界面微调。触发关键词：搭建 room、搭建会议、集成会议、接入会议、官方 RoomKit、TUIRoomKit、界面微调、搭建直播间、搭建语音房、音视频产品、TRTC 产品、room 类产品、视频会议界面、会议室设计。"
---

# TRTC Room Builder

从零搭建 room 类音视频产品的前端界面，或把官方 RoomKit 会议能力集成进现有
Vue 3 应用。提供三条路径，根据用户需求自动选择：

- **Styled 路径**：12 个精美模板 + 设计系统 → 高风格感、视觉精致的界面
- **Standard 路径**：60 个通用组件 + 5 种场景模板 → 功能完备、标准化的界面
- **Official RoomKit 集成模式**：官方 RoomKit 组件 + 官方 API → 快速接入现有业务应用，并通过官方扩展点微调界面

> 本 skill 是自包含的：所有模板、设计系统参考、60 组件的 UIKit 资产与工具脚本都在本目录内（`templates/`、`references/`、`uikit/`），无需外部依赖。

---

## Invocation entry points

本 skill 有两种被使用入口；主入口下支持 `official-roomkit` 与 `full-ui`
两种会议 UI 生成/集成模式：

### 1. 被 `../trtc-topic/SKILL.md` 消费（主路径，conference official-roomkit / full-ui 模式）

当用户在 onboarding A2-Q0.5 选择"官方 UI"时，
`${CLAUDE_PROJECT_DIR}/.trtc-session.yaml` 会写入
`ui_mode: official-roomkit`。topic 读取本 skill 的"官方 RoomKit 集成模式"
作为生成规范，集成官方组件并使用官方 API 微调界面。

当用户在 A2-Q0.5 选择"AI 生成完整会议 UI"时，session 会写入
`ui_mode: full-ui`。topic 读取本 skill 的以下资产作为生成规范，并**不会**
调用本 skill 的"核心决策流程"或 `scaffold.py`：

- `references/scenario-mapping.md` — onboarding scenario → Standard scene / 模板
- `references/composable-bindings.md` — UIKit class → AtomicXCore composable 绑定
- `uikit/assets/themes/meeting-classic/` — 组件 CSS + 图标资产
- `uikit/references/component-catalog.md` — 60 组件 HTML 范式

用户看不到本 skill 的参与——topic 拿这些资产作为内部生成规范，输出融合 Vue SFC。

### 2. 用户直接触发（fallback 入口，非主推路径）

下面的"核心决策流程"保留作为 fallback：当 harness 因为 description 关键词匹配
而自主触发本 skill 时（比如用户恰好说了"搭建会议界面"但未经过 onboarding），
就按"核心决策流程"走。

**推荐路径始终是 onboarding A2-Q0.5 → topic**——通过那条路径进来的用户要么得到
官方 RoomKit 集成代码，要么得到能跑的 Vue + AtomicXCore 自定义 UI 代码，而不是
孤立的 HTML demo。根 skill 不为本 skill 创建专用触发词；本路径是 harness 行为的
补充，不是主推的用户旅程。

---

## 官方 RoomKit 集成模式

当用户要在**已有 Vue 3 项目中集成会议/接入多人会议/接入 TUIRoomKit/使用官方
RoomKit**，且没有明确要求“完全重做会议 UI / 生成定制全屏会议界面”时，优先走
官方 RoomKit 集成模式，而不是 Styled / Standard 路径。

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
5. UserSig 生成必须复用 `skills/trtc-onboarding/reference/mcp-usersig-generation.md`
   的规则：优先使用 MCP / 当前本地签名能力生成测试 `userSig`，正式环境由业务后端
   签发；没有签名能力时，前端只保留 `SDKAppID / userId / userSig` 输入项或占位。
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

- 不要为官方 RoomKit 集成模式运行 `trtc_prepare_ui.py` 或
  `trtc_verify_ui.py`。
- 不要复制 `uikit/assets/themes/meeting-classic/` 到客户项目，也不要要求生成的
  Vue 组件满足 `ui-*` class 数量规则。
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
- 快速接入 Web&H5 (Vue3)：https://cloud.tencent.com/document/product/647/81962
- 界面微调 (Web)：https://cloud.tencent.com/document/product/647/129842

---

## 医疗在线问诊新项目直拷规则

当用户需求落在医疗在线问诊（例如 `1v1-video-consultation`、远程问诊、
医生/患者视频问诊、在线诊疗）并且明确是**生成全新项目**，不要进入 Styled
路径、Standard 路径、theme-copy、手写 Vue SFC 或任何 verifier 流程。

直接把本 skill 内置模板目录完整复制到用户指定的本地项目目录：

```bash
skills/trtc/room-builder/templates/scenarios/medical-consultation/
```

复制时保留模板项目的文件结构、路由、样式、服务适配器、mock 数据和文档。
交付或接入说明中必须提醒客户使用 `pnpm install` 安装依赖，并使用
`pnpm dev` 启动本地开发服务；不要推荐 `npm install` / `npm run dev`，因为
该医疗模板使用 npm 启动会明显变慢，首屏可能白屏一段时间。
本规则只适用于全新医疗问诊项目；对既有项目做集成/改造时，继续按后续
scenario / official-roomkit / full-ui / UIKit 规则处理。

## 核心决策流程

```
用户提出 room 类界面需求
          │
          ▼
是否是已有 Vue 3 项目集成会议 / 官方 RoomKit？
          │
    ┌─────┴──────┐
    ▼            ▼
   YES          NO
    │            │
    ▼            ▼
Official   用户是否有明确的风格/视觉诉求？
RoomKit          │
集成模式   ┌─────┴──────┐
          ▼            ▼
         YES          NO
          │            │
          ▼            ▼
     Styled 路径   Standard 路径
     (精美模板)    (通用组件)
```

### 判断标准——何时走 Styled 路径

当用户描述中包含以下**任一**特征时，走 Styled 路径：

- 提到具体视觉风格：暗色、毛玻璃、渐变、极光、高级感、商务风、清新、扁平
- 提到品牌色/配色方案：紫色调、深色金、森林绿、天蓝系等
- 提到设计参考：像 Zoom/Teams/Google Meet、Dribbble 风格、现代感
- 提到模板/精美/好看/showcase/展示/demo/高颜值
- 明确说"有风格要求"或指定了字体偏好
- 目标用途是展示/演示/客户 demo 而非生产环境

### 判断标准——何时走 Standard 路径

当用户描述中**没有**上述风格诉求，且更关注功能完备性时，走 Standard 路径：

- 只描述功能需求：视频会议、语音房、直播、通话等
- 关注功能区域：麦克风控制、成员列表、聊天、设置面板
- 目标是可交互的原型或直接生产使用
- 需要与 TRTC SDK / TUIRoom 对接的标准界面

---

## Styled 路径（精美模板 + 设计系统）

### Phase S1：选择模板

读取 `references/templates-index.md` 匹配用户需求。12 个模板速查：

| # | 文件 | 风格 | 主色 | 适用场景 |
|---|---|---|---|---|
| 01 | skyblue-dashboard | 友好 SaaS 仪表盘 | #38BDF8 | 产品化视频 + 任务管理 |
| 02 | forest-realestate | 编辑风 / 衬线 / 专业 | #2D6A4F | 房产/法律/咨询 |
| 03 | purple-trackly-ai | 现代创业公司 | #7C5CFC | AI 项目管理 |
| 04 | mindcare-sprint | Sprint 三栏布局 | #2563FF | 迭代计划/站会 |
| 05 | finance-daily | 明亮薄荷绿 | #00C48A | 日会 + 字幕翻译 |
| 06 | evo-ia-aiassistant | AI 助手风 | #00C9A7 | AI 转写/摘要 |
| 07 | green-initiative-grid | 大地色 2×2 等分 | #2D6A4F | 4人站会 |
| 08 | q4-strategy-dark-gold | 暗黑高级金 | #C9A96E | 高管董事会 |
| 09 | aurora-grid-9 | 极光动态 3×3 | #667eea | 9+人 gallery view |
| 10 | glass-design-review | 毛玻璃/粉彩 | #6366f1 | 设计评审 |
| 11 | culture-workshop | 陶土色 Workshop | #E07A5F | 工作坊/团建 |
| 12 | social-design-review | 清爽靛蓝 | #4F6EF7 | 社交/营销评审 |

每个模板另附 `-lobby.html` 变体（会议前大厅/进入页），用于完整的"入会前 → 会议中"双屏体验。

### Phase S2：交付或定制

**匹配度 80%+**：直接使用模板文件 `templates/<NN-name>.html`
- 可直接浏览器预览
- 可修改标题、颜色、成员姓名等内容

**匹配度不足**：用设计系统从零生成
1. 读取 `references/design-system.md` — 颜色/字体/间距 token + 6 条铁律 + 质量检查清单
2. 读取 `references/layout-recipes.md` — 6 种布局骨架 + 决策树
3. 读取 `references/component-library.md` — 复制粘贴 HTML 组件片段
4. 按质量清单（14 项 yes/no）验证产出

**混合模式**：可以从一个模板取视频区，从另一个取聊天面板，拼接组合。

### Phase S3：预览

使用 `preview_url` 打开生成的 HTML 文件让用户实时预览。

---

## 全局约束（双路径共用）

以下规则对所有场景、所有路径生效：

### 最小宽度约束

所有生成的会议界面必须设置 **最小宽度 1200px**。当浏览器视口窄于 1200px 时，页面内容不压缩、不重排，而是出现横向滚动条。

**Standard 路径**：已内置在 `layout.css` 中（通过 `--layout-min-width: 1200px` token 控制），无需额外操作。

**Styled 路径**：生成页面时必须包含以下 CSS：
```css
body { min-width: 1200px; }
@media (max-width: 1199px) { html { overflow-x: auto; } }
```

---

## Standard 路径（通用组件库）

### 内部组件库资产（`uikit/`）

Standard 路径依赖本目录下的 `uikit/` 子目录（原独立 `trtc-room-uikit` 技能，已合并到本 skill）：
- 组件目录：`uikit/references/component-catalog.md`（60 个组件的 HTML 范式）
- Token 契约：`uikit/references/token-contract.md`（~100 个 Design Token + 暗色模式）
- 组件资产：`uikit/assets/themes/meeting-classic/`（CSS + 暗色 token + SVG 图标集）
- 风格脚本：`uikit/scripts/generate-theme-overrides.py`（L1 token 覆盖生成）
- 图标换色：`uikit/scripts/recolor-icons.py`（SVG 图标品牌色替换）

详细说明见 `uikit/README.md`。

### Phase G1：场景判断

读取 `references/scene-templates.md` 中的决策树：

| 场景 | 关键特征 |
|---|---|
| **meeting** | 多人视频/语音 + 屏幕共享 + 成员管理 |
| **voice-room** | 主持人 + 多人语音连麦 + 无视频 |
| **live-stream** | 1 主播 + 大量观众 + 连麦互动 |
| **one-on-one** | 两人视频/语音通话 |
| **classroom** | 老师讲课 + 学生举手提问 |

如果用户描述模糊，展示以上 5 种选项让用户选择。

### Phase G2：搜集需求

确定场景后确认：
1. 页面标题
2. 需要的功能区域
3. 风格偏好（品牌色/圆角/暗色模式）
4. 额外需求

### Phase G3：准备资产

```bash
# 复制组件库到目标项目
cp -R {skill_dir}/uikit/assets/themes/meeting-classic {project}/themes/meeting-classic

# 生成页面骨架
python3 {skill_dir}/scripts/scaffold.py --scene {type} --title "{title}" --output {project}/

# 风格定制（可选）
python3 {skill_dir}/uikit/scripts/generate-theme-overrides.py --primary "{color}" --output {project}/themes/overrides.css

# 图标换色（可选）
python3 {skill_dir}/uikit/scripts/recolor-icons.py --accent "{color}" --dir {project}/themes/meeting-classic/assets
```

> `{skill_dir}` 表示本 skill 的安装目录。所有脚本都在本 skill 内部，路径相对统一。

### Phase G4：填充内容

在骨架的 TODO 位置填入具体组件 HTML。

**必读参考**：
1. `uikit/references/component-catalog.md` — 60 个组件 HTML 范式
2. `references/scene-templates.md` — 当前场景的推荐组件配置
3. `uikit/assets/themes/meeting-classic/index.html` — 完整参考实现

**填充规则**：
1. 组件 HTML 结构严格遵循 component-catalog.md
2. 图标优先使用 `uikit/assets/themes/meeting-classic/assets/` 下内置 SVG
3. 状态通过 `.is-*` class 切换
4. CSS 引入顺序：tokens.css → (tokens.dark.css) → layout.css → atoms → molecules → organisms

### Phase G5：预览与迭代

使用 `preview_url` 预览，根据反馈调整。

---

## 场景速查

| 场景 | Standard 路径组件 | Styled 路径推荐模板 |
|---|---|---|
| 多人视频会议 | topbar, stage, bottombar, side-panel, modal, popover | 01/04/07/09 |
| 高管/正式会议 | 同上 | 08(暗金) |
| AI 增强会议 | topbar, stage, bottombar + AI 面板 | 03/06 |
| 设计评审 | topbar, stage, bottombar, side-panel(chat/files) | 10/12 |
| 工作坊/培训 | topbar, stage, bottombar, side-panel(agenda) | 05/11 |
| 语音房间 | topbar, bottombar, avatar(麦位), chat-message | — (Standard only) |
| 直播连麦 | topbar, stage, bottombar, chat-message, video-badge | — (Standard only) |
| 1v1 通话 | stage, bottombar, video-badge | — (Standard only) |
| 在线课堂 | topbar, stage, bottombar, side-panel | 05 |

---

## 资源目录

```
trtc/room-builder/                    ← 自包含 skill 根目录
├── SKILL.md                          ← 本文件（统一入口 + 决策流程）
├── scripts/
│   └── scaffold.py                   ← Standard 路径：5 场景骨架生成器
├── references/                       ← Styled 路径 + 场景决策参考
│   ├── scene-templates.md            ← Standard 路径：场景决策树 + 页面模板
│   ├── templates-index.md            ← Styled 路径：12 模板元数据 + 选择指南
│   ├── design-system.md              ← Styled 路径：设计系统规范 + 质量清单
│   ├── component-library.md          ← Styled 路径：Tailwind 组件代码片段
│   ├── layout-recipes.md             ← Styled 路径：6 种布局骨架
│   └── usage-guide.md                ← Styled 路径：框架集成指南
├── templates/                        ← 12 个精美 HTML 模板 + 12 个 lobby 变体
│   ├── 01-skyblue-dashboard.html
│   ├── 01-skyblue-dashboard-lobby.html
│   ├── ... (共 24 个)
│   └── 12-social-design-review-lobby.html
├── assets/
│   └── gallery.html                  ← 模板可视化索引页
└── uikit/                            ← Standard 路径组件库（内部依赖）
    ├── README.md                     ← UIKit 内部说明
    ├── scripts/
    │   ├── generate-theme-overrides.py  ← Token 覆盖生成
    │   └── recolor-icons.py             ← SVG 图标换色
    ├── references/
    │   ├── component-catalog.md         ← 60 组件 HTML 范式
    │   └── token-contract.md            ← ~100 Design Token + 暗色模式
    └── assets/
        └── themes/meeting-classic/      ← 组件 CSS + 暗色 token + SVG 图标集
```
