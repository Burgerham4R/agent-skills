# 平台 Slice 模板

> **本文件是平台实现 slice 的标准模板。**
> 复制本文件到 `slices/{product}/{platform}/{ability}.md`，按 `<!-- 指引: ... -->` 批注填写内容，填完后删除所有批注。
>
> **填写范例**：请参考 [`slices/live/ios/coguest-apply.md`](slices/live/ios/coguest-apply.md) — 目前最完整的平台 slice，包含所有 section 的真实内容。

---

```yaml
---
id: {product}/{ability}       # [必填] 与 index.yaml 中的 id 一致
platform: {platform}          # [必填] ios / android / web / flutter / electron
api_docs:                      # [必填] 该平台对应的 API 参考文档链接，至少 1 条
  - title: {API 类名/模块名}
    url: https://...
---
```

<!-- 指引: Frontmatter 字段说明：
     - id: 与 index.yaml 中的 slice id 完全一致
     - platform: 当前平台标识
     - api_docs: 该功能在该平台的 API 参考文档链接（接口签名、参数类型、返回值等）。
       产品级概览已不再放文档链接，教程/指南类 URL 也不放在 api_docs 里。

       ✅ 必须精确到类/模块级的 URL（如 CoGuestStore 的 API 页面）
       ✅ 涉及多个类时可有多条（如 CoGuestStore + DeviceStore 各一条）
       ❌ 不要填 SDK 首页（AI 拿不到校验所需的签名信息）
       ❌ 不要填产品级教程页

     其余元数据（name、tags、platforms、related）在产品级概览中维护，此处不重复。
-->

# {名称} — {平台} 实现

## 前置条件 [必填]

<!-- 指引: 通用依赖（SDK 安装、基础权限）已在 login-auth 平台 slice 中统一描述，此处不要重复。
     本 section 只写两类内容：

     1. 增量依赖 — 本 slice 额外需要的库/权限（如美颜 SDK、蓝牙权限）。
        如果没有额外依赖，写「无额外依赖」即可。
     2. 前置状态 — 本功能依赖哪些 Store 已初始化/哪些操作已完成，引用对应 slice ID。

     ❌ 不要重复写 SDK 主包安装（如 pod 'AtomicXCore'、implementation 'com.tencent.liteav:...'）
     ❌ 不要重复写基础权限声明（如 NSCameraUsageDescription、CAMERA permission），除非本 slice 需要额外权限
     ❌ 不要写通用开发环境搭建（如「安装 Xcode」「安装 Android Studio」）
-->

**通用依赖**：见 [login-auth 平台 slice](../login-auth.md)

**额外依赖**：
<!-- 如果有本 slice 独有的依赖，在此列出；没有则写「无」 -->

**前置状态**：
<!-- 列出必须满足的前置条件，引用 slice ID。例如：
     - `LoginStore.shared` 登录成功（→ live/login-auth）
     - 已进入直播间，持有有效 liveID（→ live/audience-watch）
-->

## 代码示例 [必填]

<!-- 指引: 本 section 是平台 slice 的核心交付物。详细标准见 slice-spec.md 第四节「代码示例标准」。
     定位是「零件」— 单个功能的完整实现。多个零件如何组装成完整场景，由 scenario 的平台实现文件负责。

     最低标准（必须全部满足）：
     1. 可编译：完整 import、完整类/函数闭包，严禁用 `...` 省略任何逻辑分支
     2. 可运行：补充业务参数后可直接跑通；业务参数用 `{TODO: 填入 xxx}` 占位
     3. 有日志锚点：关键路径（成功/失败/事件到达）必须有日志，供「验证矩阵」运行时使用
        — 日志统一带模块前缀（如 `[CoGuest]`）
     4. 有错误处理：每个 .failure / catch / error 分支都必须有面向用户的处理（errorMessage / alert），
        不允许只 print 了事
     5. 多角色分开写：主播端 / 观众端 必须拆成独立的代码块，不要耦合
     6. 可组合性：前置依赖通过注释声明（`// 前置：登录完成（→ live/login-auth）`），不硬编码其他 slice 的调用

     组织方式：按用户操作流程，用 MARK / region / 注释分隔各步骤（初始化 → 核心操作 → 事件监听 → 错误处理 → 清理）

     ❌ 不要写伪代码或用省略号 (...) 跳过逻辑
     ❌ 不要混入其他 slice 的职责代码
     ❌ 不要把多个功能耦合在一个类里
     ❌ 不要省略错误处理 — 每个失败分支都必须有处理
-->

## 调用时序 [条件必填：多角色异步交互 或 回调嵌套 ≥3 层]

<!-- 指引: 【条件必填】— 触发条件任一满足即必须画：
     — 多角色交互（主播/观众/服务端三方时序不容易从单段代码看出）
     — 异步回调链路特别深（3 层以上嵌套回调）
     — 有隐含的时序依赖不写出来容易踩坑（如「必须先订阅再操作」）

     如果代码示例已经足够清晰（单角色、同步或浅回调），可以跳过此 section 并整段删除。

     格式：用 ``` 包裹的 ASCII 文本流程图。
-->

## 平台特有注意事项 [必填：至少 1 条]

<!-- 指引: 本 section 是平台 slice 区别于产品级概览的核心价值所在。
     只写该平台独有的坑，产品级概览的通用最佳实践不要重复。

     每条注意事项的格式：
     ### {编号}. {一句话标题}
     — 先说现象/问题（开发者会遇到什么）
     — 再说原因（为什么会这样）

     什么内容该写在这里：
     - 该平台的类型陷阱（如 iOS 的 Int32 vs Int、Android 的 Int vs Long）
     - 该平台的生命周期问题（如 Android Activity 重建、iOS 后台挂起）
     - 该平台的内存/线程问题（如 iOS [weak self]、Android 主线程更新 UI）
     - 该平台的权限行为差异（如 iOS 崩溃 vs Android 返回错误码）
     - 该平台特有的错误码或异常行为

     什么内容不该写：
     ❌ 跨平台通用的业务逻辑（如「先登录再操作」→ 产品级概览已覆盖）
     ❌ API 用法说明（→ 代码示例已覆盖）
     ❌ 通用排障流程（→ 产品级概览已覆盖）

     质量标准：每条都应该是「不写出来，研发大概率会踩坑」的内容。
     如果一条注意事项对于有经验的该平台开发者来说是常识，就不用写。
-->

## 代码生成约束 [必填]

<!-- 指引: 本 section 供 AI 在生成/验证代码时使用，是给机器读的硬性规则。
     与「平台特有注意事项」互补：
     — 注意事项 = 给人读的经验提醒
     — 代码生成约束 = 给 AI 读的可检查规则

     所有规则必须基于实际 SDK 行为，不允许凭经验推测。
     ⚠️ 核心要求：每条 MUST / MUST NOT 使用 **prose + backtick** 格式：
        N. **<动作> `符号`** — <违反后果>。
           **Verify**: 检查是否存在 `符号`。
     backtick 里的符号 = apply 唯一会 grep 的东西；规则文字其他词 apply 不验。
     完整原则与红旗词表见 slice-spec.md 第四节「MUST 规则的维度对齐原则」。
-->

### 编译必要条件 [必填]

<!-- 指引: 本 slice 代码能编译通过的最小条件。
     只写增量条件（通用条件见 login-auth slice）。
     — 必须导入的模块/包（精确到包名）
     — 本 slice 额外需要的 SDK 版本要求（如果高于基础要求）
     — 本 slice 额外需要的权限声明或配置

     如果没有增量条件，写「同 login-auth，无额外要求」
-->

### 生成规则 [必填]

#### MUST（生成时必须包含）

<!-- 指引: 每条格式：

     N. **<动作> `符号`** — <违反后果>。
        **Verify**: 检查是否存在 `符号`。

     重要原则（详细规则见 slice-spec.md 第四节「MUST 规则的维度对齐原则」）：
     — backtick 里的符号 = apply 唯一会 grep 的东西
     — 规则文字描述的判断 / 选择 / 等价 / 条件分支，apply 全部不验
     — 多 backtick 的规则可以接受，apply 解析为「全部都要出现」（all-of）

     ⚠️ 红旗词：以下写法说明 MUST 写错了，要么拆分要么下沉到软规则区
     — 「或 / 任一」、「等价 / 或类似」、「按业务 / 根据场景」
     — 「留给 / 负责」、「多 backtick 但 Verify 只提一个」

     示例（复制修改）：
     1. **必须导入 `useRoomState`** — 否则状态与 UI 无法收口。
        **Verify**: 检查是否存在 `useRoomState`。

     2. **必须从 `tuikit-atomicx-vue3/room` 导入** — 错包的同名 hook 不会跑通。
        **Verify**: 检查是否存在 `tuikit-atomicx-vue3/room` 与 `useRoomState`
        同时出现在同一 import 语句。

     只写本 slice 独有的规则。跨 slice 通用规则如果在多个 slice 中反复出现，
     考虑提到产品级概览或 base-setup 中。
-->

#### MUST NOT（生成时绝不能出现）

<!-- 指引: 同上格式，每条 = 一个禁现的具体符号或符号组合。
     重点写「看起来能跑但逻辑错误」的写法 — 这类问题编译器抓不到，只有了解业务语义才能避免。

     示例：
     1. **不要把 `leaveRoom()` 当成解散会议** — 会导致房主离开后房间仍在。
        **Verify**: 检查 `leaveRoom` 不与房主路径并列出现，房主收口必须用 `endRoom`。

     注：MUST NOT 的 Verify 同样依赖 backtick 符号 + apply 的「all-of」grep；
     避免用「不应该 / 不要」+ 抽象描述这种 grep 无法验证的写法。
-->

### 集成检查点 [必填]

<!-- 指引: 假设目标是已有项目（不是从零开始的 demo），列出集成时需要确认的事项：
     — 是否与项目中已有的 SDK 初始化冲突
     — 是否需要合并到已有的生命周期方法中（而非新建）
     — 是否依赖其他 slice 的前置状态（引用具体 slice ID）
     — 对已有代码的侵入性（新增文件 vs 修改已有文件）
-->

## 验证矩阵 [必填]

<!-- 指引: 平台 slice 的统一验收出口。AI 生成代码后或人工 review 时，自上而下跑一遍就能完成验收。

     4 个层级：
     — 1. 编译级：能编译、依赖齐全（CI / AI 自动）
     — 2. 静态规则级：纯静态扫描 / grep 可查（CI / AI 自动）
     — 3. 运行时级：跑起来通过日志锚点可观察（AI 半自动 / 人工）
     — 4. 业务行为级：人眼看 UI / 硬件状态（人工）

     要求：
     — 每条「代码生成约束」的 MUST / MUST NOT 都要在矩阵中有对应行（层级 1 或 2）
     — 至少 1 条层级 3 的检查，证明代码真能跑
     — 至少 1 条层级 4 的检查，证明业务语义正确（通常是 ALWAYS / NEVER 的运行时体现）
-->

| 层级 | 检查项 | 验证手段 | 预期结果 |
|------|--------|----------|---------|
| 1. 编译级 | {模块导入齐全} | {xcodebuild build / ./gradlew assembleDebug / tsc --noEmit} | exit code 0 |
| 1. 编译级 | {最低版本达标} | {查项目 deployment target} | ≥ {版本} |
| 2. 静态规则级 | {对应 MUST 规则 1} | {grep 正则} | {匹配条件} |
| 2. 静态规则级 | {对应 MUST NOT 规则 1} | {grep 正则} | {不应匹配} |
| 3. 运行时级 | {关键路径日志} | {触发操作 → 查日志} | {日志内容} |
| 4. 业务行为级 | {业务语义观察} | {操作步骤} | {UI / 硬件状态} |

---

## DoD 自查（提交前删除此 section）

提交前对照 `slice-spec.md` 第五节「平台实现文件 DoD」逐条打勾。任何一项不满足 = 未完成。

---

> **填写范例**：请参考 [`slices/live/ios/coguest-apply.md`](slices/live/ios/coguest-apply.md) — 这是目前最完整的平台 slice 实现，包含所有 section 的真实内容。
