# Eval 格式参考

本文档定义 booksmith 的测试评估格式，基于 skill-creator 的 eval schema。

---

## eval_metadata.json

每个测试案例的元数据，位于 `<workspace>/iteration-N/eval-<ID>/eval_metadata.json`：

```json
{
  "eval_id": 1,
  "eval_name": "basic-o'reilly-workflow",
  "prompt": "帮我写一本关于 Docker 容器技术的 O'Reilly 风格技术书",
  "assertions": [
    "project.json 存在且包含正确的 title、style、target_reader 字段",
    "research/ 目录存在，包含至少 4 个方向的调研文件",
    "Phase 1.5 调研 Review 表格已展示给用户"
  ]
}
```

---

## grading.json

评判结果，位于 `<workspace>/iteration-N/eval-<ID>/grading.json`：

```json
{
  "expectations": [
    {
      "text": "project.json 存在且包含正确的 title、style、target_reader 字段",
      "passed": true,
      "evidence": "文件存在于 ~/Books/docker-container-tech/project.json，字段正确"
    },
    {
      "text": "research/ 目录存在，包含至少 4 个方向的调研文件",
      "passed": true,
      "evidence": "research/01-core-concepts.md, 02-tools.md, 03-cases.md, 04-best-practices.md"
    },
    {
      "text": "Phase 1.5 调研 Review 表格已展示给用户",
      "passed": false,
      "evidence": "调研完成后直接进入 Phase 2，跳过了 Review 检查点"
    }
  ],
  "summary": {
    "passed": 2,
    "failed": 1,
    "total": 3,
    "pass_rate": 0.67
  },
  "execution_metrics": {
    "tool_calls": {
      "Bash": 12,
      "Read": 8,
      "Write": 5
    },
    "total_tool_calls": 25,
    "total_steps": 8,
    "errors_encountered": 0,
    "output_chars": 3450,
    "transcript_chars": 12400
  },
  "timing": {
    "executor_duration_seconds": 165.0,
    "grader_duration_seconds": 26.0,
    "total_duration_seconds": 191.0
  }
}
```

**字段说明：**
- `expectations[].text`：断言描述（必须与 assertions 中的描述一致）
- `expectations[].passed`：布尔值
- `expectations[].evidence`：判断依据，必须具体
- grading.json 的 expectations 数组**必须用固定字段名**：`text` / `passed` / `evidence`

---

## timing.json

每次运行后保存到 `<workspace>/iteration-N/eval-<ID>/timing.json`：

```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3
}
```

**注意**：timing 数据只在 task 完成通知里出现一次，必须立即保存。

---

## benchmark.json

聚合统计，位于 `<workspace>/iteration-N/benchmark.json`：

```json
{
  "run_summary": {
    "with_skill": {
      "pass_rate": {"mean": 0.85, "stddev": 0.05, "min": 0.80, "max": 0.90}
    },
    "without_skill": {
      "pass_rate": {"mean": 0.30, "stddev": 0.10, "min": 0.20, "max": 0.40}
    },
    "delta": {"pass_rate": "+0.55"}
  },
  "per_eval": [
    {
      "eval_id": 1,
      "eval_name": "basic-workflow",
      "with_skill_pass_rate": 1.0,
      "without_skill_pass_rate": 0.3
    }
  ]
}
```

---

## 断言设计原则

- **客观可验证**：断言必须能被自动化检查，不依赖主观判断
- **描述清晰**：断言名应在 benchmark viewer 中一目了然
- **适度数量**：每个 eval 3-5 个断言，太多难以维护
- **区分度**：好 skill 应让断言 pass rate 明显高于 baseline

**不适合自动断言的维度**（用 human review）：
- 写作风格是否符合用户偏好
- 叙事流畅度
- 内容深度的主观判断
