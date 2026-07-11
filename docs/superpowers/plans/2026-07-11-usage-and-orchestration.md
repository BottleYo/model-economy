> 历史文档：记录 0.3.0 的实施过程，已完成且不代表当前运行规则。

# 用量观察与编排收敛实施计划

> **面向代理工作者：** 按指令优先级选择单一编排并逐任务实施；不得叠加完整的 `superpowers:subagent-driven-development` 编排。步骤使用复选框跟踪。

**目标：** 发布 Model Economy `0.3.0`，新增安全、可选的 CodexBar 用量适配器，并收敛 Model Economy 与 Superpowers 的代理编排边界。

**架构：** 独立的 `usage.py` 负责 CodexBar 可执行文件发现、受控子进程、上游 JSON 校验、筛选与稳定摘要；`cli.py` 只解析参数和渲染文本或 JSON。`routing-policy.json` 继续是角色拓扑的唯一机器事实源，Markdown 只提供同策略的执行说明。

**技术栈：** Python 3.11+ 标准库、`argparse`、`dataclasses`、`json`、`subprocess`、`unittest`、CodexBar CLI JSON、现有敏感内容扫描与 GitHub Actions。

## 全局约束

- 不读取、复制、修改或导出 Codex/CodexBar 凭证、token、cookie 和账号文件。
- 不内置 CodexBar 的 JSONL 扫描器、OAuth/API 调用或定价表。
- 绝对路径、账号标签及未知上游字段不得进入公开输出。
- 成本必须标记为 CodexBar 估算，不得描述为准确账单或实际付款。
- 不声称验证实际 subagent 角色、模型身份或精确角色级 token 消耗。
- CodexBar 不可用时不得影响安装、配置、升级和验证命令。
- Model Economy 获得编排权时，是角色拓扑、能力档位、subagent 数量和完成门的唯一事实源；更高优先级指令强制其他编排时只提供成本建议。
- 标准任务由主 agent 或一个 implementer 二选一承担主要实现。
- 本次不持久化路由日志，不新增数据库、后台服务或图形界面。
- 所有新增或修改的公共文档同时维护英文和简体中文版本。
- 插件、项目和 CLI 上下文版本提升到 `0.3.0`；routing schema 为 `3`、usage schema 为 `1`、config/state schema 保持 `1`。

---

### Task 1：收敛编排策略与上下文契约

**文件：**
- 修改：`plugins/model-economy/skills/cost-aware-development/references/routing-policy.json`
- 修改：`plugins/model-economy/skills/cost-aware-development/SKILL.md`
- 修改：`plugins/model-economy/skills/cost-aware-development/references/role-matrix.md`
- 修改：`plugins/model-economy/skills/cost-aware-development/references/context-contract.md`
- 修改：`plugins/model-economy/skills/cost-aware-development/references/routing-examples.md`
- 修改：`tests/test_skill_contract.py`

**接口：**
- 消费：现有 schema v2 分类顺序和六角色定义。
- 产出：schema v3 标准任务条件角色、唯一编排规则、证据边界和扩充后的上下文契约。

- [ ] **Step 1：先写标准任务角色失败测试**

将标准任务期望改为只有 implementer 属于基础允许角色，explorer、reviewer、architect 都是条件角色：

```python
standard = load_policy()["task_classes"]["standard"]
self.assertEqual(standard["base_allowed_roles"], ["model-economy-implementer"])
self.assertEqual(
    {entry["role"] for entry in standard["conditional_roles"]},
    {
        "model-economy-explorer",
        "model-economy-reviewer",
        "model-economy-architect",
    },
)
```

断言 explorer 条件为文件/依赖/事实不明确，reviewer 条件为跨模块、关键逻辑、回归风险不直观或测试覆盖存在实质疑问，architect 保持 `failed_attempts >= 2` 和一次诊断。

- [ ] **Step 2：写唯一编排与证据边界失败测试**

```python
skill = SKILL.read_text(encoding="utf-8")
self.assertIn("唯一编排", skill)
self.assertIn("subagent-driven-development", skill)
self.assertIn("不得增加所选路由之外", skill)
self.assertIn("主 agent 或一个 `model-economy-implementer`", skill)
self.assertIn("变更评估", skill)
self.assertIn("残余交付风险", skill)
self.assertIn("新鲜验证证据", skill)
```

同时断言上下文契约包含“非目标”和“验证命令”，路由收据包含计划路由、实际启动、请求能力档、模型身份未验证。

- [ ] **Step 3：运行测试确认红灯**

运行：

```sh
python3 -m unittest tests.test_skill_contract -v
```

预期：标准任务角色集合、schema 版本及新规则断言失败。

- [ ] **Step 4：最小修改机器策略**

将 routing schema 提升为 `3`，为所有任务增加共享的 `max_subagent_starts: 3` 和 `reclassification_resets_budget: false`，并把 standard 调整为：

```json
{
  "primary_execution": {
    "selection": "exactly_one",
    "choices": ["main_agent", "model-economy-implementer"]
  },
  "base_allowed_roles": ["model-economy-implementer"],
  "conditional_roles": [
    {
      "role": "model-economy-explorer",
      "when": {
        "operator": "any",
        "predicates": [
          "file_location_uncertain",
          "dependency_relationship_uncertain",
          "existing_facts_uncertain"
        ]
      },
      "output": "minimal_facts"
    },
    {
      "role": "model-economy-reviewer",
      "when": {
        "operator": "any",
        "predicates": [
          "cross_module_change",
          "critical_logic_change",
          "non_obvious_regression_risk",
          "material_test_coverage_doubt"
        ]
      },
      "output": "independent_findings"
    },
    {
      "role": "model-economy-architect",
      "when": {"failed_attempts": {"gte": 2}},
      "max_calls": 1,
      "output": "diagnostic_decision",
      "after_completion": {
        "implementation_capability": "balanced",
        "reclassify_when": "large_or_high_risk_discovered"
      }
    }
  ]
}
```

保持六角色恰好落入 base、conditional、required、forbidden 中的一组。增加规则：standard architect 诊断只有在输出满足大型 architect 契约且发生在新审批前时，才能计入重分类后的 architect 完成门。

- [ ] **Step 5：同步人类可读规则**

在 Skill 中写明：

```text
按指令优先级只选择一套编排。Model Economy 获得编排权时，Superpowers 只提供执行方法，不得增加所选路由之外的 agent、计划、审查或完成门；更高优先级指令强制其他编排时，Model Economy 只提供成本建议。
```

明确禁止完整 `subagent-driven-development` 编排；允许 `dispatching-parallel-agents` 作为已批准角色的并行方法；主 agent 与 implementer 二选一；区分 reviewer、final-reviewer 和 verification。

- [ ] **Step 6：扩充上下文与路由收据**

上下文模板增加：

```text
非目标：本角色不得处理的事项。
验证命令：必须运行、可复用或不得无理由重复的命令及证据。
```

新增非持久化路由收据模板，明确没有事件证据时“实际启动：未记录”，模型身份固定标记为未验证。

- [ ] **Step 7：运行目标测试并提交**

运行：

```sh
python3 -m unittest tests.test_skill_contract -v
```

预期：全部通过。

提交：

```sh
git add plugins/model-economy/skills/cost-aware-development tests/test_skill_contract.py
git commit -m "feat: clarify model economy orchestration"
```

---

### Task 2：实现 CodexBar 用量适配器

**文件：**
- 创建：`plugins/model-economy/scripts/model_economy_lib/usage.py`
- 创建：`tests/test_usage.py`

**接口：**
- 产出：`discover_codexbar(explicit, env, which, platform) -> Path`、`check_codexbar_version(binary) -> tuple[int, ...]`、`fetch_usage(binary, days, timeout_seconds=30) -> object`、`summarize_usage(payload, project=None, days=30) -> UsageSummary`、`usage_to_dict(summary) -> dict`。
- 不消费 CLI 参数对象，避免与 `argparse` 耦合。

- [ ] **Step 1：编写可执行文件发现失败测试**

覆盖优先级：显式路径、`CODEXBAR_BIN`、`PATH` 的 `codexbar`、`PATH` 的 `CodexBarCLI`、macOS Helper；覆盖不存在和不可执行。

```python
result = discover_codexbar(
    explicit=explicit,
    env={"CODEXBAR_BIN": str(environment)},
    which=lambda name: str(path_binary) if name == "codexbar" else None,
    platform="darwin",
    macos_candidates=(helper,),
)
self.assertEqual(result, explicit.resolve())
```

- [ ] **Step 2：编写安全子进程失败测试**

使用 mock 断言调用参数包含日历窗口和项目分组：

```python
[str(binary), "cost", "--provider", "codex", "--format", "json", "--days", "30", "--group-by", "project"]
```

覆盖版本低于 `0.41.0`、超时、非零退出、空输出和非法 JSON；异常信息不得包含 stderr、绝对路径或上游账号。用 `Popen` 流式读取，stdout 上限 8 MiB，stderr 丢弃；只保证终止并回收直接子进程。

- [ ] **Step 3：编写规范化与汇总失败测试**

fixture 必须完全构造，包含两个项目、两个日期、两个模型、可选字段缺失和未知字段。断言：

- `--project` 精确匹配规范路径，但输出只保留目录名。
- `--days` 由 CodexBar 形成日历窗口，插件验证返回 `historyDays` 与请求一致，不再按活跃日二次切片。
- input、output、cache read、cache creation、total 和模型 token 分别求和。
- 任一日缺失某指标时该聚合指标为 `None`；模型 token 缺失时不反推。
- 输出不含 `path`、`account` 和未知字段。

- [ ] **Step 4：运行测试确认红灯**

```sh
python3 -m unittest tests.test_usage -v
```

预期：因 `usage.py` 不存在失败。

- [ ] **Step 5：实现稳定数据类型与发现逻辑**

定义：

```python
@dataclass(frozen=True)
class TokenTotals:
    input: int | None
    output: int | None
    cache_read: int | None
    cache_creation: int | None
    total: int | None

@dataclass(frozen=True)
class ModelTotal:
    name: str
    total_tokens: int | None
    estimated_cost: float | None

@dataclass(frozen=True)
class UsageSummary:
    project: str | None
    range_days: int | None
    tokens: TokenTotals
    estimated_cost: float | None
    currency: str | None
    models: tuple[ModelTotal, ...]
```

所有整数拒绝布尔值和负数，金额拒绝非有限值和负数。解析器拒绝重复键、深度超过 32、总记录超过 20,000 的输入。

- [ ] **Step 6：实现受控执行和上游结构校验**

只接受顶层数组或单个 provider 对象；选择 `provider == "codex"` 的唯一记录。先执行 `--version` 并要求 `>= 0.41.0`。超时、非零退出、非法 JSON、资源边界或歧义 provider 抛出 `UsageError`，错误消息只包含固定分类，不拼接 stderr。

- [ ] **Step 7：实现项目与日期汇总**

项目筛选使用 `projects[].path` 精确匹配，再使用项目 `daily`；无项目筛选时使用 provider `daily`。`--days` 已传给 CodexBar，不按活跃日二次切片。每个 token 分量和成本独立聚合，但任一选中记录缺失某分量时该分量整体为 `None`。币种只接受上游 `currencyCode`，模型 token 只接受 `modelBreakdowns[].totalTokens`。

- [ ] **Step 8：实现稳定 JSON 字典**

```python
{
    "usage_schema_version": 1,
    "source": "codexbar",
    "cost_is_estimate": True,
    "project": summary.project,
    "range_days": summary.range_days,
    "tokens": {...},
    "estimated_cost": {"amount": ..., "currency": ...},
    "models": [...],
    "role_attribution": {
        "available": False,
        "reason": "Codex telemetry does not expose verified Model Economy role identity",
    },
}
```

- [ ] **Step 9：运行目标测试并提交**

```sh
python3 -m unittest tests.test_usage -v
```

预期：全部通过。

```sh
git add plugins/model-economy/scripts/model_economy_lib/usage.py tests/test_usage.py
git commit -m "feat: add codexbar usage adapter"
```

---

### Task 3：接入 CLI、双语文档和版本

**文件：**
- 修改：`plugins/model-economy/scripts/model_economy_lib/cli.py`
- 修改：`tests/test_cli.py`
- 修改：`plugins/model-economy/.codex-plugin/plugin.json`
- 修改：`plugins/model-economy/scripts/model_economy_lib/lifecycle.py`
- 修改：`pyproject.toml`
- 修改：`README.md`
- 修改：`README.zh-CN.md`
- 修改：`docs/en/cli-reference.md`
- 修改：`docs/zh-CN/cli-reference.md`
- 修改：`docs/en/how-it-works.md`
- 修改：`docs/zh-CN/how-it-works.md`
- 修改：`docs/en/installation.md`
- 修改：`docs/zh-CN/installation.md`
- 修改：`CHANGELOG.md`
- 修改：`CHANGELOG.zh-CN.md`
- 修改：`tests/test_structure.py`

**接口：**
- 消费：Task 2 的四个公开函数和 `UsageSummary`。
- 产出：`usage` CLI、稳定文本/JSON 输出、统一 `0.3.0` 版本与双语用户文档。

- [ ] **Step 1：编写 CLI 参数和错误失败测试**

覆盖：默认 text、JSON、project、days、显式 binary、`days < 1` 或 `days > 365` 返回 64、CodexBar 缺失及版本过低返回 1。通过 patch Task 2 函数，不启动真实 CodexBar。

```python
with patch("model_economy_lib.cli.discover_codexbar", return_value=binary), \
     patch("model_economy_lib.cli.fetch_usage", return_value=payload), \
     redirect_stdout(output):
    code = main(["usage", "--project", str(project), "--days", "7", "--format", "json"])
self.assertEqual(code, 0)
self.assertNotIn(str(project.parent), output.getvalue())
```

- [ ] **Step 2：编写文本输出失败测试**

断言存在“来源”“成本为估算”“角色归因：不可用”，数字使用千分位；所有可选值缺失时显示“不可用”而非零。

- [ ] **Step 3：运行 CLI 测试确认红灯**

```sh
python3 -m unittest tests.test_cli -v
```

预期：解析器不认识 `usage`。

- [ ] **Step 4：注册 usage 命令并实现输出**

参数：

```python
usage_parser = command("usage")
usage_parser.add_argument("--project", type=Path)
usage_parser.add_argument("--days", type=days_value, default=30)
usage_parser.add_argument("--format", choices=("text", "json"), default="text")
usage_parser.add_argument("--codexbar-bin", type=Path)
```

JSON 使用 `json.dumps(..., ensure_ascii=False, indent=2, sort_keys=True)`；文本格式化只消费 `UsageSummary`。

- [ ] **Step 5：编写版本一致性失败测试并更新版本**

结构测试要求下列位置均为 `0.3.0`：

- `pyproject.toml`
- `plugin.json`
- CLI `_context()` 创建的 `Context.version`
- 生命周期升级目标和相关断言
- `verify_installation()` 对 state `template_version` 与当前 Context 版本的漂移检查

不得修改已发布历史条目的版本文字。

- [ ] **Step 6：更新双语公共文档**

README 只做简短入口；CLI 参考完整说明参数、CodexBar 可选依赖、安全边界、成本估算和角色归因限制；工作原理说明唯一编排权和三类证据；安装指南说明如何发现或指定 CodexBar CLI。中英文命令和事实必须一一对应。

- [ ] **Step 7：更新 CHANGELOG**

新增 `0.3.0`：CodexBar 用量适配器、标准角色条件化、唯一编排权、上下文契约和路由收据。不得记录任何个人用量数字或本机安装路径。

- [ ] **Step 8：运行目标测试并提交**

```sh
python3 -m unittest tests.test_cli tests.test_structure -v
```

预期：全部通过。

```sh
git add plugins/model-economy pyproject.toml README.md README.zh-CN.md docs/en docs/zh-CN CHANGELOG.md CHANGELOG.zh-CN.md tests/test_cli.py tests/test_structure.py
git commit -m "feat: expose usage command and release 0.3.0"
```

---

### Task 4：集成验证、审查与发布

**文件：**
- 只在发现问题时修改 Task 1–3 所列文件及对应测试。

**接口：**
- 消费：完整 `0.3.0` 候选树。
- 产出：通过验证和最终审查的单一发布提交、GitHub main 与 `v0.3.0` Release。

- [ ] **Step 1：运行完整本地验证**

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_sensitive_content.py .
git diff --check main...HEAD
```

预期：测试零失败；仅允许已有的 Codex help 环境跳过；敏感扫描和 diff 检查通过。

- [ ] **Step 2：运行隔离 CLI fixture 验收**

创建临时假 `CodexBarCLI`，支持 `--version` 并只输出不含真实路径和账号的构造 JSON。分别执行 text、JSON、project、days；确认退出码为 0、JSON 可解析且输出无临时目录父路径。

- [ ] **Step 3：运行缺失依赖降级验收**

在清空 `PATH` 且不设置 `CODEXBAR_BIN` 的隔离环境执行 `usage`，确认退出码 1；随后执行 `verify --quiet`，确认原有命令行为不受影响。

- [ ] **Step 4：最终只读审查**

使用 `model-economy-final-reviewer` 检查：

- 上游 JSON 信任边界和路径/账号泄露。
- 汇总计算与缺失值语义。
- subprocess 超时及错误清理。
- 机器策略与 Markdown 一致性。
- Superpowers 不会形成第二套编排。
- 版本、双语文档和测试覆盖。

修复所有 P0–P2，并对修复做定向复审。

- [ ] **Step 5：压缩并合并到 main**

保持功能分支内部审计提交；使用 `git merge --squash codex/usage-routing-v03` 在 main 创建单个发布提交，避免内部计划噪声进入公开主历史。提交身份保持 `Model Economy Contributors <model-economy@users.noreply.github.com>`。

- [ ] **Step 6：推送并等待 CI**

```sh
git push origin main
gh run watch <run-id> --repo BottleYo/model-economy --exit-status
```

预期：Linux、macOS、Windows × Python 3.11/3.12 六组全部通过。

- [ ] **Step 7：创建 v0.3.0 Release**

发布说明只包含公开功能、安全边界、安装/升级命令和已知限制；不得包含个人用量、账号、本机路径或内部开发计划。
