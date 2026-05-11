# Scenario 文件写作规范（Spec）

> 本文档定义 `knowledge-base/scenarios/{scenario-id}.md` 的标准结构。
> 新建场景文件按本规范写；老文件按本规范逐步对齐。
> 配套：`slice-spec.md`（slice 级规范）、`index.yaml`（场景索引）。

---

## 一、scenario 文件的角色

scenario 文件是 **topic skill 的场景剧本**。topic 接到一个场景 id 后，把这份文件当 ground truth，按它说的：

- 列出场景包含哪些能力（slice）
- 决定是否让用户在"主链路 / 完整版"之间选 coverage
- 在 ui_mode=full-ui 时决定 UI 哪些区域显示、哪些隐藏
- 走每一步 slice 集成

→ **写 scenario 文件 = 给 topic 提供执行剧本**，措辞应面向"AI 读这份文件后该做什么"。

---

## 二、两种场景形态：A vs B

每个场景按自身性质二选一形态，**不强制都要分层**。

| 形态 | 适用场景 | 特征 | 用户是否参与 coverage 选择 |
|---|---|---|---|
| **A：单一完整能力** | 所有 slice 缺一不可：1v1 通话、秀场直播间、电商直播等 | 能力不可拆，少一个就不成场景 | 否 |
| **B：主链路 + 可选增强** | 有清晰的"开箱可用最小集 + 推荐增强"边界：通用会议、协作工具等 | 主链路是默认，增强按需 | 是（minimal / complete） |

形态判断准则：
- 写 P1 之前先问自己——"如果不选这条增强，场景还能成立吗？" 能 → P1；不能 → P0。
- 整个场景全部 slice 都"少一个就不成立" → 直接走 A 形态，不必硬掰。

不确定时 default 走 A，将来发现确实有可选项再升级到 B。

---

## 三、必备章节

每个 active scenario 文件 **必须** 包含以下章节。命名可微调，章节角色和顺序不能动。带 (A) (B) 标记的章节按形态二选一写法。

### 1. `## 场景概述`

一段 2-4 行散文，回答三个问题：
- 这个场景对应什么真实业务（举 1-2 个具体例子）
- 用户做这种场景的核心诉求是什么
- 与其他相似场景如何区分（边界划清）

**用途**：topic Step 1.5 展示给用户的"我帮你定位到了什么场景"的依据。

### 2. `## 能力清单` (A) 或 `## 能力分层` (B)

**slice id 必须与 `index.yaml` 一致**。

#### 形态 A：能力清单

```markdown
## 能力清单

- `<product>/<slice-id>` —— {一句话功能描述（中文，UI 上能直接用做按钮 label / 设置项标题）}
- ...
```

#### 形态 B：能力分层

```markdown
## 能力分层

### P0 主链路（必装）

- `<product>/<slice-id>` —— {一句话}
- ...

### P1 常见增强（可选）

- `<product>/<slice-id>` —— {一句话}
  - UI 默认渲染：是 / 否
  - 推荐默认勾选：是 / 否
- ...
```

**P1 字段说明（仅形态 B）**：

| 字段 | 含义 | 取值 |
|---|---|---|
| `UI 默认渲染` | 在 ui_mode=full-ui 的 reference HTML 里，对应按钮/区域是否默认存在 | 是 / 否 |
| `推荐默认勾选` | minimal coverage 时是否仍当作必装；complete 时是否预选 | 是 / 否 |

**关键不变量（仅形态 B）**：

- `UI 默认渲染 = 是` **必须** `推荐默认勾选 = 是`。否则出现"按钮存在但点了没反应"的 bug（参见 todo 中 screen-share 案例）。
- `UI 默认渲染 = 否` 时，无论是否勾选，都不强制按钮在 UI 上显示。

### 3. `## 能力展示` (A) 或 `## 能力展示与 coverage 选择` (B)

**topic Step 1.5 直接照抄的展示模板**。包含展示文案 + (B 形态特有) AskUserQuestion 选项。

#### 形态 A：能力展示

```markdown
## 能力展示

### 展示文案

我帮你定位到「{场景中文名}」场景，包含以下 {总数} 项能力：

  • {slice 1 中文名} (`{slice id}`)
  • {slice 2 中文名} (`{slice id}`)
  ...

接下来开始集成。
```

A 形态不向用户提问 coverage，topic 展示完直接进 Step 2。

#### 形态 B：能力展示 + coverage

```markdown
## 能力展示与 coverage 选择

### 展示文案

我帮你定位到「{场景中文名}」场景，包含以下能力：

📋 主链路（必装，{P0 count} 项）
  • {P0 slice 1 中文名} (`{slice id}`)
  • {P0 slice 2 中文名} (`{slice id}`)
  ...

➕ 增强能力（可选，{P1 count} 项）
  • {P1 slice 1 中文名} (`{slice id}`) {如"推荐默认勾选 = 是"，加 ✓}
  ...

集成哪种？
1) 主链路（最快，开箱可用基础{场景类型}）
2) 完整版（含全部 {总数} 项能力，推荐）

### AskUserQuestion 选项

| 选项 | label | 写入 session |
|---|---|---|
| 1 | 主链路 | `enhancement_level: minimal` |
| 2 | 完整版 | `enhancement_level: complete` |
```

### 4. `## UI 区域 / Slice 映射`（仅 ui_mode=full-ui 场景必需）

只在场景于 `scenario-mapping.md` 有 reference HTML 时才需要这一节。无 UI 模板的场景跳过。

列出 reference HTML 里所有可见 UI 区域，标注对应 slice 与显隐处理。

#### 形态 A：UI 映射（无 minimal/complete 分支）

```markdown
| UI 区域（class） | 对应 slice |
|---|---|
| `.ui-stage` | `<product>/video-layout` |
| `.ui-bottombar [data-action="mic"]` | `<product>/device-control` |
| ... | ... |
```

A 形态所有列出的区域都"显示"，不需要分支。

#### 形态 B：UI 映射（按 coverage 分支）

```markdown
| UI 区域（class） | 对应 slice | minimal | complete |
|---|---|---|---|
| `.ui-topbar` | `<product>/login-auth` + `<product>/room-lifecycle` | 显示 | 显示 |
| `.ui-stage` | `<product>/video-layout` | 显示 | 显示 |
| `.ui-bottombar [data-action="share"]` | `<product>/screen-share` | 隐藏（v-if="false" 加注释） | 显示并接 composable |
| ... | ... | ... | ... |
```

**作用**：topic Step 3.5 binding-audit 直接读这张表决定 UI 显隐。决策表 per-scenario 显式列出，SKILL.md 不必写。

### 5. `## 前置条件`

集成前用户必须做的事（控制台配置、SDK 版本、账号开通、平台权限等）。topic Step 2 展示给用户。

```markdown
- 已开通 TRTC 服务并获取 SDKAppID 和 SecretKey
- {平台} SDK 版本 ≥ {version}
- {权限 / 配置 / 其他}
```

### 6. `## 验收 Checklist`

集成完成后用户用来自检"我这套真的跑起来了吗"的清单。topic Step 完成后展示。

```markdown
- [ ] 用户能登录并进入会议
- [ ] 摄像头 / 麦克风可以正常打开关闭
- [ ] {针对本场景的特有验收点}
- [ ] {...}
```

### 7. `## 排障速查`（可选但强烈建议）

把场景下高频出错的 3-5 个症状 → 排查路径列出。**不重复 slice 内的排障**，只列**跨 slice、属于场景级的**问题。

例如通用会议场景：
- "进得去房但是看不到别人画面" → 检查推流 + 拉流 + 视频布局三个 slice 的状态
- "聊天发不出去" → 检查会控秩序是否禁聊 + room-chat slice 状态

---

## 四、可选章节

按需写，不强制：

- `## 子场景命中差异` —— 同一场景下不同子形态（如"日常团队会议" vs "培训会议"）的 slice 增减建议
- `## 跨产品依赖` —— 本场景依赖其他产品 SDK 时的说明
- `## 设计取舍` —— 为什么这个场景这么拆、和兄弟场景的边界（给后续 scenario 作者看的设计笔记）

---

## 五、字段一致性检查

写完 scenario 文件，检查：

| 检查项 | 哪两处必须一致 |
|---|---|
| slice id 列表 | `index.yaml` `scenarios.<id>.slices` 数组 ↔ 本文件「能力清单」(A) 或 「能力分层」(B) 总和 |
| 中文名 | 「能力清单 / 能力分层」中的 slice 名 ↔ 「能力展示」展示文案中的 slice 名 |
| `推荐默认勾选 = 是`（仅 B） | 必须在「能力展示」展示文案的 ✓ 标记列表 |
| `UI 默认渲染 = 是`（仅 B） | 必须在「UI 区域 / Slice 映射」中标注 minimal 时也"显示" |

未来可加 `scripts/validate_scenario.py` 自动跑这些检查。

---

## 六、模板骨架

### A 形态模板（单一完整能力）

适合：1v1-video-call、entertainment-live-room 等场景所有 slice 缺一不可的情况。

```markdown
# {场景中文名}（{scenario-id}）

## 场景概述

{2-4 行散文}

## 能力清单

- `{product}/{slice-id-1}` —— {一句话}
- `{product}/{slice-id-2}` —— {一句话}
- ...

## 能力展示

### 展示文案

我帮你定位到「{场景中文名}」场景，包含以下 {总数} 项能力：

  • {slice 1 中文名} (`{slice id}`)
  • {slice 2 中文名} (`{slice id}`)
  • ...

接下来开始集成。

## UI 区域 / Slice 映射

| UI 区域（class） | 对应 slice |
|---|---|
| `.ui-stage` | ... |
| ... | ... |

## 前置条件

- {条件 1}
- {条件 2}

## 验收 Checklist

- [ ] {验收点 1}
- [ ] {验收点 2}

## 排障速查

| 症状 | 可能原因 | 排查方向 |
|---|---|---|
| {症状 1} | {原因} | {slice / 配置项} |
```

### B 形态模板（主链路 + 可选增强）

适合：general-meeting、协作工具等有清晰 P0/P1 边界的场景。

```markdown
# {场景中文名}（{scenario-id}）

## 场景概述

{2-4 行散文}

## 能力分层

### P0 主链路（必装）

- `{product}/{slice-id-1}` —— {一句话}
- `{product}/{slice-id-2}` —— {一句话}

### P1 常见增强（可选）

- `{product}/{slice-id-3}` —— {一句话}
  - UI 默认渲染：是
  - 推荐默认勾选：是
- `{product}/{slice-id-4}` —— {一句话}
  - UI 默认渲染：否
  - 推荐默认勾选：否

## 能力展示与 coverage 选择

### 展示文案

我帮你定位到「{场景中文名}」场景，包含以下能力：

📋 主链路（必装，{P0 count} 项）
  • {P0 slice 1 中文名} (`{slice id}`)
  • ...

➕ 增强能力（可选，{P1 count} 项）
  • {P1 slice 1 中文名} (`{slice id}`) ✓
  • {P1 slice 2 中文名} (`{slice id}`)
  • ...

集成哪种？
1) 主链路（最快，开箱可用基础{场景类型}）
2) 完整版（含全部 {总数} 项能力，推荐）

### AskUserQuestion 选项

| 选项 | label | 写入 session |
|---|---|---|
| 1 | 主链路 | `enhancement_level: minimal` |
| 2 | 完整版 | `enhancement_level: complete` |

## UI 区域 / Slice 映射

| UI 区域（class） | 对应 slice | minimal | complete |
|---|---|---|---|
| `.ui-topbar` | ... | 显示 | 显示 |
| `.ui-bottombar [data-action="share"]` | `{product}/screen-share` | 隐藏 | 显示 |

## 前置条件

- {条件 1}
- {条件 2}

## 验收 Checklist

- [ ] {验收点 1}
- [ ] {验收点 2}

## 排障速查

| 症状 | 可能原因 | 排查方向 |
|---|---|---|
| {症状 1} | {原因} | {slice / 配置项} |
```

---

## 七、对老文件的迁移建议

老文件不强制立刻按 spec 重写。建议路径：

1. **`general-meeting.md`** → 走 B 形态。原文里已有"P0 默认会议骨架 / P1 按需补命中"分层结构，只需补「能力展示与 coverage 选择」「UI 区域 / Slice 映射」「验收 Checklist」三节，其他内容可移到「设计取舍」可选章节。

2. **`entertainment-live-room.md`** → 走 A 形态。原文按"主播端流程 / 观众端流程 / 阶段一 / 阶段二"组织，先按 spec 改为「能力清单」「能力展示」+ 验收 Checklist；流程描述可保留为「子场景命中差异」可选章节。

3. **新建场景** → 直接走 spec，按形态选 A 或 B 模板。
