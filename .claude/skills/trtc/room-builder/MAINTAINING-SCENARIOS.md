# 维护 UI 场景

本文档面向 trtc-ai-integration 知识库的**维护者**。终端用户不会读这份文件——他们看到的是渲染后的 `scenario-mapping.md` 和 SKILL 路由层。

## 一句话总结

新增一个有主题的场景（比如 `telemedicine` → 临床风格 UI 主题）：

1. 在 `uikit/assets/themes/<slug>/` 下做主题资产。
2. 改 `references/scenarios.yaml` —— 把对应场景的 `theme: ~` 替换为五字段的 theme block。
3. 跑 `python3 .claude/skills/trtc/room-builder/tools/render_scenario_mapping.py`（或者 `./bootstrap.sh`）。
4. 跑 `pytest tests/unit/ -v` 确认 registry 链路没坏。
5. **注意**：onboarding 的 A2-Q0 选择菜单是写死在 `path-a2-integrate.md` 里的。如果想让新场景出现在选择菜单中，要单独改那个文件。registry 不负责菜单选项。

完工。**不需要改任何 Python 代码。**

## 数据流

```
                    scenarios.yaml      ← 单一真理源
                          │
                ┌─────────┼──────────┐
                ▼                    ▼
         theme_registry.py      render_scenario_mapping.py
                │                    │
        ┌───────┴────────┐           ▼
        ▼                ▼      scenario-mapping.md  ← 派生文件，禁止手改
trtc_prepare_ui.py  trtc_verify_ui.py        │
        │                │                   ▼
        ▼                ▼          被 topic SKILL.md Step 3.5 消费
  cp 主题目录       校验主题契约
  改 main.ts
  改 index.html
```

## 该改哪些文件、不该改哪些文件

| 文件 | 状态 | 内容 |
|---|---|---|
| `references/scenarios.yaml` | **改这里** | 场景 id、path、template、reference HTML、theme block |
| `uikit/assets/themes/<slug>/` | **改这里** | 主题 CSS、组件、图标、index.html |
| `references/scenario-mapping.md` | **不要改** | 由 scenarios.yaml 渲染生成 |
| `.claude/skills/trtc/room-builder/guardrails/lib/theme_registry.py` | 极少改 | yaml 加载器；只在 Theme 契约本身要变时才改 |
| `.claude/skills/trtc/room-builder/tools/render_scenario_mapping.py` | 极少改 | yaml→md 渲染器 |
| `.claude/skills/trtc/room-builder/guardrails/trtc_prepare_ui.py` | 极少改 | 读 registry；改用户项目 |
| `.claude/skills/trtc/room-builder/guardrails/trtc_verify_ui.py` | 极少改 | 读 registry；校验用户项目 |

如果不小心改了 `scenario-mapping.md`，下次 `./bootstrap.sh`（或者跑渲染器）会把改动覆盖掉。CI 的 `--check` 模式也会拦截这种漂移。

## 新增带主题场景 —— 完整示例（telemedicine）

### Step 1：做主题资产

照着 `meeting-classic/` 的目录结构镜像一份：

```bash
THEME_ROOT=.claude/skills/trtc/room-builder/uikit/assets/themes
cp -R "$THEME_ROOT/meeting-classic" "$THEME_ROOT/telemed-clinical"
# 然后改副本里的文件：调色板、组件、图标等
```

一份完整主题目录至少包含：
- `index.css` —— 顶层入口，引入所有子 CSS
- `index.html` —— 参考 HTML（被 topic SKILL.md 当成视觉规格使用）
- `tokens.css` / `tokens.dark.css` —— 设计 token
- `components/` 子目录（atoms / molecules / organisms）

### Step 2：在 `scenarios.yaml` 里接线

找到 `telemedicine` 那一项。把 `theme: ~` 替换成五字段 theme block。同时把 `template:` 和 `reference_html:` 字段也填上 —— 渲染后的 `.md` 和 topic SKILL.md 都会读这两个字段。

```yaml
  - id: telemedicine
    path: telemedicine/
    template: telemed-clinical
    reference_html: telemed-clinical/index.html
    notes: ""
    theme:
      slug: telemed-clinical
      source_dir: .claude/skills/trtc/room-builder/uikit/assets/themes/telemed-clinical
      data_theme: tc
      import_path: "@/themes/telemed-clinical/index.css"
      target_dir: src/themes/telemed-clinical
```

五个 theme 字段对应的作用：

| 字段 | 控制什么 | 典型取值 |
|---|---|---|
| `slug` | 日志、stderr 文案 | `telemed-clinical` |
| `source_dir` | prepare 从哪里读（相对 KB 根） | `.claude/skills/trtc/room-builder/uikit/assets/themes/<slug>` |
| `data_theme` | `<html data-theme="...">` 属性值 | 2-4 字符短 slug，比如 `tc` |
| `import_path` | main.ts 里写入的字面 `import '...'` | `@/themes/<slug>/index.css` |
| `target_dir` | prepare 写入哪里（相对用户项目根） | `src/themes/<slug>` |

### Step 3：重新渲染 .md

```bash
python3 .claude/skills/trtc/room-builder/tools/render_scenario_mapping.py
```

`references/scenario-mapping.md` 表格里就会出现新场景了。

### Step 4：跑测试套件

```bash
pytest tests/unit/ -v
```

multi-theme 测试套件挂了说明你打破了 registry 契约。检查一下改了什么。

### Step 5：用一个新建项目做 smoke 测试

新建一个空临时项目，在它的 `.trtc-session.yaml` 里写 `scenario: telemedicine`。跑 `python3 .claude/skills/trtc/room-builder/guardrails/trtc_prepare_ui.py` —— 应该把新主题复制到 `src/themes/telemed-clinical/` 下。跑 `python3 .claude/skills/trtc/room-builder/guardrails/trtc_verify_ui.py --total-min 5` —— V1/V2/V3 应该过；V4 可能挂，要等 AI 用主题的 `ui-*` class 写出 `.vue` 文件后才能过（那是 AI 的活，不是 scaffold 的活）。

### Step 6：（可选）把场景加到 onboarding 选择菜单

`path-a2-integrate.md` 把 A2-Q0 菜单选项写死了。打开文件、找到选项列表、加一行 `telemedicine`。这是单独的一步，**故意分离**——registry 管主题映射，菜单管用户选择，职责清楚。

### Step 7：提交

把所有改动一起 stage：

```bash
git add \
  .claude/skills/trtc/room-builder/uikit/assets/themes/telemed-clinical \
  .claude/skills/trtc/room-builder/references/scenarios.yaml \
  .claude/skills/trtc/room-builder/references/scenario-mapping.md
```

yaml + 主题资产 + 重新渲染的 md **必须一起提交**。这样 `--check` 从第一个 commit 起就是绿的。如果 yaml 提交了但忘了重新渲染 md，下一个 contributor 会被 CI 卡住。

## 验证清单（直接复制粘贴）

```bash
# Registry / 渲染管线
pytest tests/unit/test_theme_registry.py -v
pytest tests/unit/test_render_scenario_mapping.py -v

# 确认 .md 跟 yaml 同步
python3 .claude/skills/trtc/room-builder/tools/render_scenario_mapping.py --check
echo "exit=$?  # 必须是 0"

# 确认 prepare/verify 对原有 2 个主题场景仍然工作
pytest tests/unit/test_trtc_prepare_ui.py tests/unit/test_trtc_verify_ui.py -v
```

## 常见坑

**「我改了 scenario-mapping.md，但每次改完都被还原。」**

那个文件是自动生成的。改 `scenarios.yaml` 然后跑 `python3 .claude/skills/trtc/room-builder/tools/render_scenario_mapping.py`。

**「我在 scenarios.yaml 加了场景，但 onboarding 的菜单里没有。」**

菜单在 `path-a2-integrate.md` Q0，不在 scenarios.yaml 里。registry 管主题映射，菜单管用户选择，是故意分开的。两个文件都要改才能完整覆盖。

**「我以为 trtc_verify_ui.py 应该挂的，但它一声不吭。」**

检查 session 文件的 `current_step` 字段。如果是 `*-complete`，**lifecycle gate 已关闭** —— onboarding 完成后用户接管代码，hook 故意 exit 0。要重新触发 hook，要么把 `current_step` 临时改回进行中的值（如 `A2.4`），要么新建一个测试项目。

**「两个场景想共用同一个主题。」**

完全支持。让两个 scenario 的 `theme:` block 指向同一个 `slug` / `source_dir` / `target_dir`（实例：`webinar-large` 和 `general-meeting` 都用 `meeting-classic`）。`shutil.copytree(dirs_exist_ok=True)` 处理 target 路径碰撞。

**「我想加一个场景，暂时还没主题，但要在选择菜单里出现。」**

yaml 里保留 `theme: ~`。渲染器会在 .md 那行写 `(TODO)`；registry 对该场景返回 `None`；`in_scope()` 返回 False；hook 静默 no-op。等以后填好 theme block，同一行 yaml 自动「上线」。

## 交叉引用

- `scenarios.yaml` —— 单一真理源
- `scenario-mapping.md` —— 派生文件，禁止手改
- `.claude/skills/trtc/room-builder/guardrails/lib/theme_registry.py` —— 加载器 + `Theme` dataclass
- `.claude/skills/trtc/room-builder/tools/render_scenario_mapping.py --check` —— CI 守门
- `.claude/skills/trtc/room-builder/guardrails/trtc_prepare_ui.py` / `trtc_verify_ui.py` —— hook 实现
- `.claude/skills/trtc/onboarding/reference/path-a2-integrate.md` —— A2-Q0 菜单（独立于 registry）
- `.claude/skills/trtc/room-builder/guardrails/trtc_verify_ui.py` 顶部 docstring —— hook 三道闸门的设计原理（lifecycle / scope / readiness）
