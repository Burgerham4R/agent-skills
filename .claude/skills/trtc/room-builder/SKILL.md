---
name: trtc-room-builder
description: "TRTC Room 产品搭建器。当用户需要搭建视频会议、语音房间、直播连麦、1v1通话、在线课堂等 room 类音视频产品的前端界面时，此技能提供两条路径：有明确风格诉求时，优先使用 12 个精美模板或设计系统生成高风格感界面（Tailwind + 现代设计）；无明确风格诉求时，使用通用组件库（60 个组件 + Design Token）生成标准功能型界面。最终交付完整可运行的 HTML 页面。触发关键词：搭建 room、搭建会议、搭建直播间、搭建语音房、音视频产品、TRTC 产品、room 类产品、视频会议界面、会议室设计。"
---

# TRTC Room Builder

从零搭建 room 类音视频产品的前端界面。提供两条路径，根据用户需求自动选择：

- **Styled 路径**：12 个精美模板 + 设计系统 → 高风格感、视觉精致的界面
- **Standard 路径**：60 个通用组件 + 5 种场景模板 → 功能完备、标准化的界面

> 本 skill 是自包含的：所有模板、设计系统参考、60 组件的 UIKit 资产与工具脚本都在本目录内（`templates/`、`references/`、`uikit/`），无需外部依赖。

---

## Invocation entry points

本 skill 有两种被使用的方式：

### 1. 被 `topic/SKILL.md` 消费（主路径，conference full-ui 模式）

当用户在 onboarding A2-Q0.5 选择"业务代码 + 完整 UI"时，`.trtc-session.yaml`
会写入 `ui_mode: full-ui`。topic 读取本 skill 的以下资产作为生成规范，并**不会**
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

**推荐路径始终是 onboarding A2-Q0.5 → topic**——通过那条路径进来的用户得到的
是能跑的 Vue + AtomicXCore 集成代码，而不是孤立的 HTML demo。根 skill 不为
本 skill 创建专用触发词；本路径是 harness 行为的补充，不是主推的用户旅程。

---

## 核心决策流程

```
用户提出 room 类界面需求
          │
          ▼
    用户是否有明确的风格/视觉诉求？
          │
    ┌─────┴──────┐
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
trtc-room-builder/                    ← 自包含 skill 根目录
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
