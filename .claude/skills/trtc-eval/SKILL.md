---
name: trtc-eval
description: >
  Evaluates the quality of the trtc skill and its knowledge base by
  running AI-generated code against a curated eval set and scoring both
  static constraint compliance and runtime SDK behavior. Use when the
  user mentions 跑分, 评测, eval, benchmark, 回归, quality check, or
  asks to compare skill versions. Internal-only tool for TRTC knowledge
  maintainers.
---

# TRTC 评测工具

## 触发条件
- 用户 prompt 中出现：跑分 / 评测 / eval / benchmark / 回归 / 看看效果 / 质量对比
- 如果含过滤条件（如 "只跑 iOS 的"、"只跑 smoke"），记录下来并在 Step 1 应用到用例筛选

## 执行步骤（你，主 Agent，严格按顺序执行）

### Step 1：加载 eval set
- 执行 `python scripts/selfcheck.py --phase=pre-run` 校验环境
  - 校验失败 → 停止，把 selfcheck.json 摘要给用户，让用户修
- 读取 `tests/benchmark/cases.json`
- 按用户过滤条件筛出要跑的用例列表
- 创建本次运行目录 `.codebuddy/eval-runs/{ISO8601}/`，写 run.manifest.json

### Step 2：串行调用 orchestrator 跑每条用例
对筛出的每条用例（**串行，不并发**），用 `execute_command` 工具调用 orchestrator：

```bash
python scripts/case_runner_orchestrator.py \
  --case-id={test_id} \
  --run-dir=.codebuddy/eval-runs/{ts}
```

**关键约束**：
- 一次只跑一条用例，串行执行（首版避免并发导致真机资源冲突）
- orchestrator 内部串联 7 个步骤（run_ai → evaluator → demo_build → log_stream_start → demo_run → log_stream_stop → runtime_monitor），它是 `trace.jsonl` 的唯一写入者
- orchestrator 的 stdout 只输出**一行 JSON**：`{"test_id":"...","exit_code":0,"summary_path":"<相对路径>"}`。你只读这一行即可。
- **绝对不要 `cat` 或读取** `ai_raw_output.md` / `runtime.log` / `compile.log` —— 这是上下文污染源。
- 如果你需要看分数，**只读** `{run_dir}/cases/{test_id}/summary.json`。

### Step 3：汇总 & 出报告
- 所有用例跑完后，执行 `python scripts/report.py build --run-dir=.codebuddy/eval-runs/{ts}`
- （可选）如果用户要求 diff：`python scripts/report.py diff --baseline=<旧 run_dir> --current=<新 run_dir>`
- 执行 `python scripts/selfcheck.py --phase=post-run --run-dir=.codebuddy/eval-runs/{ts}` 再次自查
- 把 `report.md` 路径和 `selfcheck.json` 中的 `verdict` 字段一起给用户

## 你（主 Agent）的铁律

> **类别说明（重要）**：以下 4 条是 **Prompt 软约束**，依赖 LLM 自觉遵守。
> 真正的结构防御在 orchestrator 独家写 trace、nonce 校验和 AST 扫描。
> 这一段的违反**不会**让 selfcheck 自动判 TAINTED，只会被事后审计登记。

1. 你**只读 `run.manifest.json`、每条用例的 `summary.json`、最终 `report.md`**。其它 artifact 不读
2. 任何时候需要"看看代码是否对"→ 你都应当调脚本，不亲自判
3. 禁止在主 Agent 上下文中执行评分公式（所有公式在 evaluator.py / runtime_monitor.py 里）
4. 禁止 mock 数据 —— 如果某步失败，把失败透传给报告，不要编造
