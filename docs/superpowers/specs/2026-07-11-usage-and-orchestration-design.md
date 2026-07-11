> 历史文档：记录 0.3.0 的设计，已被 `docs/design/2026-07-11-native-quality-kernel.md` 取代，不代表当前运行规则。

# Model Economy 用量观察与编排收敛设计

## 背景

Model Economy 已能按风险选择能力档和角色，但仍有两个缺口：

1. 用户无法在插件 CLI 中直接观察 Codex 的项目、模型、日期和成本用量。
2. Model Economy 与 Superpowers 的职责虽已基本分开，但尚未明确唯一编排权、标准任务的按需角色条件，以及审查和验证的证据边界。

本次迭代同时补齐这两部分。用量能力采用可选 CodexBar 适配器，不在插件内复制本地会话扫描器；调度能力继续以 `routing-policy.json` 为唯一机器事实源。

## 目标

- 通过 `model_economy usage` 展示 CodexBar 已汇总的 Codex token 与估算成本。
- 支持按项目和最近天数筛选，并提供稳定的文本与 JSON 输出。
- 默认隐藏完整本地路径，不读取或输出 Codex、CodexBar 的认证信息。
- CodexBar 不可用时明确降级，不影响安装、配置、升级和验证功能。
- 明确按指令优先级只选择一套编排；Model Economy 获得编排权时，独占角色拓扑、能力档、数量上限和完成门。
- 将标准任务的 explorer、reviewer 和 architect 改为带条件角色。
- 明确 reviewer、final-reviewer 与完成前验证分别产生不同证据。
- 扩充最小上下文契约，并定义非持久化的路由收据。

## 非目标

- 不内置 CodexBar 的 JSONL 扫描器、OAuth/API 调用或定价表。
- 不读取、复制、修改或导出 Codex/CodexBar 凭证、token、cookie 和账号文件。
- 不承诺准确账单，不把 CodexBar 成本估算描述为实际付款。
- 不声称能够验证实际 subagent 角色、模型身份或精确的角色级 token 消耗。
- 不在本次迭代中持久化任务路由日志，也不建立数据库、后台服务或图形界面。
- 不改变六个现有角色的模型档配置。

## 方案选择

### 采用：可选 CodexBar CLI 适配器

插件通过子进程调用：

```text
codexbar cost --provider codex --format json --days <1...365> --group-by project
```

要求 CodexBar `>= 0.41.0`。如果 `codexbar` 不在 `PATH`，允许通过 `--codexbar-bin` 指定可执行文件。实现只解析 CodexBar 的公开 JSON 输出，不访问其配置目录和缓存目录。CodexBar 是用户授权运行的第三方本地程序；Model Economy 能保证自身不主动读取凭证、不会公开未列入白名单的上游字段，但不能替 CodexBar 保证其内部行为。

选择这一方案的原因：

- 复用用户已经安装的成熟扫描器。
- 避免复制会随 Codex JSONL 格式和定价变化而持续维护的大量代码。
- 将敏感认证和本地会话解析留在 CodexBar 的既有信任边界内。
- Model Economy 保持轻量、跨项目和可卸载。

### 暂不采用：内置 session 扫描器

内置扫描需要处理格式兼容、损坏记录、增量缓存、并发扫描、模型定价和大语料性能，明显超出本次迭代范围。未来只有在 Codex 提供稳定官方接口，或跨平台用户确有无法安装 CodexBar 的普遍需求时再单独设计。

### 后续候选：路由事件与 token 增量估算

未来可以记录任务开始/结束时间和请求角色，再与 token 增量建立估算。但并发任务、上下文缓存和缺失的 `agent_type` 会导致归因误差，因此不得在本次版本中提供角色级精确统计。

## CLI 设计

新增命令：

```sh
python3 plugins/model-economy/scripts/model_economy.py usage
python3 plugins/model-economy/scripts/model_economy.py usage --project .
python3 plugins/model-economy/scripts/model_economy.py usage --days 7
python3 plugins/model-economy/scripts/model_economy.py usage --format json
python3 plugins/model-economy/scripts/model_economy.py usage --codexbar-bin /path/to/codexbar
```

参数约束：

- `--project PATH`：解析为规范化绝对路径，但文本输出只显示项目目录名；JSON 默认也不返回原始绝对路径。
- `--days N`：`1...365`，直接传给 CodexBar，含义是最近 N 个日历日；默认 `30`。
- `--format text|json`：默认 `text`。
- `--codexbar-bin PATH`：优先级高于 `CODEXBAR_BIN` 和 `PATH`。

可执行文件发现顺序：

1. `--codexbar-bin`。
2. `CODEXBAR_BIN`。
3. `PATH` 中的 `codexbar` 或 `CodexBarCLI`。
4. macOS 已知应用包中的 CLI Helper，仅在文件存在且可执行时使用。

不扫描任意用户目录，也不猜测其他平台的安装位置。

### 文本输出

文本输出保持短小，例如：

```text
来源：CodexBar（本地统计，成本为估算）
范围：最近 7 天 · project-name
总 token：12,345,678
输入：12,000,000 · 输出：45,678 · 缓存读取：10,500,000
估算成本：USD 12.34
模型：gpt-example 10,000,000；gpt-example-mini 2,345,678
角色归因：不可用
```

缺失字段显示“不可用”，不得推导或补零。跨多日聚合时，只要任一记录缺失某指标，该指标整体为不可用。模型 token 仅在 CodexBar 返回 `totalTokens` 时显示，不得按成本比例反推。金额采用上游 `currencyCode`；缺少币种时成本整体不可用。

### JSON 输出

Model Economy 输出自己的稳定封装，不透传任意上游字段：

```json
{
  "usage_schema_version": 1,
  "source": "codexbar",
  "cost_is_estimate": true,
  "project": "project-name",
  "range_days": 7,
  "tokens": {
    "input": 12000000,
    "output": 45678,
    "cache_read": 10500000,
    "cache_creation": null,
    "total": 12345678
  },
  "estimated_cost": {
    "amount": 12.34,
    "currency": "USD"
  },
  "models": [],
  "role_attribution": {
    "available": false,
    "reason": "Codex telemetry does not expose verified Model Economy role identity"
  }
}
```

绝对路径、账号标签及未知上游字段不进入输出。

## 错误处理与安全边界

- 找不到 CodexBar：退出码 `1`，说明安装或使用 `--codexbar-bin`，不影响其他命令。
- CodexBar 超时：退出码 `1`；子进程超时固定且可测试，只保证终止并回收直接子进程，不承诺清理第三方程序自行创建的后代进程。
- 非零退出、非法 JSON 或结构不兼容：退出码 `1`，只输出经过截断和控制字符清理的错误摘要。
- 不设置 shell 模式，不拼接命令字符串，使用参数数组启动子进程。
- 不打印 CodexBar stderr 中可能存在的路径、账号或认证信息。
- `--project` 只做本地结果筛选，不把路径发送到网络。
- stdout 限制为 8 MiB，JSON 深度限制为 32，数组记录总数限制为 20,000，重复键视为非法；超过任一边界立即失败。
- macOS 与 Linux 支持 CodexBar 官方 CLI；Windows 仅支持用户通过 `--codexbar-bin` 或 `CODEXBAR_BIN` 显式提供兼容可执行文件。
- 用量命令不得修改任何文件。

## 编排权设计

新增总规则：

> 按指令优先级只选择一套代理编排。Model Economy 获得编排权时，是角色拓扑、能力档位、subagent 数量和完成门的唯一事实源；Superpowers 只提供执行方法，不得增加所选路由之外的代理、计划、审查或完成门。更高优先级指令强制其他编排时，以该指令为准，Model Economy 只提供成本建议，不声称拥有编排权。

具体规则：

- 不得在同一任务中执行完整的 `superpowers:subagent-driven-development` 编排，因为它会自行增加 implementer、逐任务审查和最终审查。
- 可以使用 `dispatching-parallel-agents` 的并行方法，但只能启动当前 Model Economy 路由允许的角色，并继续遵守最多三个 subagent、禁止递归委派及互斥写入集合。
- `requesting-code-review` 可以提供审查清单或提示模板，但不能自动增加未被路由允许的 reviewer。
- `brainstorming` 负责与用户澄清目标和取得设计审批；architect 只提供架构边界、风险和决策，其输出是 brainstorming 的技术输入，不等同于用户审批。
- `writing-plans`、TDD、系统化调试和完成前验证继续作为所选角色的工程方法。

## 标准任务角色收敛

标准任务调整为：

- 默认执行者：主 agent 或一个 `model-economy-implementer`，二者只能选择一个承担主要实现，不能重复实现。
- explorer：仅当文件位置、依赖关系或现有事实不明确，且最小只读探索能解决时允许。
- reviewer：仅当变更跨模块、触及关键逻辑、回归风险不直观或测试覆盖存在实质疑问时允许。
- architect：保持两次实质失败后最多一次、仅用于诊断；发现大型/高风险后重新分类。
- final-reviewer 和 batch-worker：继续禁止。

这些条件进入 `routing-policy.json`，并由测试验证角色集合互斥且覆盖全部六个角色。机器策略增加 `primary_execution`，要求 `main_agent` 与 `model-economy-implementer` 恰好选择一个；增加按顺序判断的条件角色谓词。

所有分类共享同一任务生命周期预算：最多启动三个 subagent，不只是最多并发三个；重新分类不重置预算。标准 architect 诊断若发生在新的大型设计审批前，且输出满足大型 architect 契约，可以计入大型流程的 architect 完成门。大型任务使用 architect 与 final-reviewer 后只剩一个 subagent 名额，主要实施须在主 agent 与 implementer 中选择，explorer 也占用同一预算。

## 证据边界

- reviewer：评估实现是否符合批准范围，报告缺陷、回归风险和测试缺口。
- final-reviewer：只用于大型/高风险任务，评估残余架构风险、安全边界、证据缺口和交付风险。
- verification-before-completion：运行并读取新鲜验证命令，确认测试、构建、静态检查或验收证据真实且覆盖声明；不重新进行完整代码审查。

同一证据层只执行一次。修复审查发现后允许对该发现做定向复审，这不算重复审查。

## 上下文契约

在现有字段中增加：

```text
非目标：本角色明确不得处理的事项。
验证命令：必须运行的命令、可复用的已有证据，以及禁止无理由重复执行的昂贵命令。
```

主 agent 使用统一字段生成摘要，但按角色裁剪内容，不向所有角色复制同一份完整上下文。

## 路由收据

开发任务结束时，主 agent 在最终回复中按需输出极简、非持久化收据：

```text
任务等级：标准
计划路由：implementer、reviewer
实际启动：implementer、reviewer
请求能力档：balanced
strong 请求：0
模型身份：未验证
验证证据：测试通过、静态检查通过
```

约束：

- 不自动写入仓库或用户目录。
- 区分“计划路由”“实际启动”和“请求能力档”。
- 未验证模型身份时不得写成“实际使用 strong/balanced/economy”。
- 没有可靠事件证据时，实际启动写“未记录”，不得根据计划推断。
- 不报告 token 节省百分比。

## 模块边界

新增独立模块 `model_economy_lib/usage.py`：

- 发现 CodexBar CLI。
- 安全执行子进程。
- 校验并规范化上游 JSON。
- 将 `--days` 作为日历窗口传给 CodexBar，并按项目白名单字段汇总。
- 生成稳定输出数据结构。

`cli.py` 只负责参数解析、调用模块和格式化输出。策略与文档修改不依赖 usage 模块，避免调度规则与外部工具集成互相耦合。

## 测试策略

### 用量模块

- 可执行文件发现优先级。
- CodexBar 缺失、不可执行、超时、非零退出和非法 JSON。
- CodexBar 版本低于 `0.41.0`、输出过大、嵌套过深、记录过多和重复键。
- 单项目、多项目、无项目和缺失可选字段。
- 日期筛选、模型聚合及总数计算。
- 默认输出不包含绝对路径、账号和未知字段。
- JSON schema 稳定性和文本缺失值行为。
- subprocess 参数数组，不使用 shell。
- 测试只使用构造的 fixture，不读取真实用户 session、缓存或凭证。

### 路由策略

- 唯一编排权规则存在且不被其他说明抵触。
- 标准任务基础角色和三个条件角色准确。
- 主 agent 与 implementer 二选一的规则明确。
- 每任务最多三次 subagent 启动，重新分类不重置预算。
- reviewer、final-reviewer、verification 的证据职责不重叠。
- 上下文契约包含非目标和验证命令。
- 路由收据明确模型身份与 token 归因限制。

### 回归验证

- 完整单元测试。
- 敏感内容扫描。
- 插件结构验证。
- Linux、macOS、Windows 的现有 CI 矩阵。

## 文档与版本

- README、安装指南、工作原理和 CLI 参考同步更新中英文版本。
- CHANGELOG 记录新增可选 CodexBar 用量适配器和编排规则收敛。
- 插件版本提升为 `0.3.0`；路由策略 schema 提升为 `3`；usage 输出使用独立的 `usage_schema_version: 1`；config/state schema 继续为 `1`。
- `verify` 检查受管理 state 的 `template_version` 是否等于当前插件版本；0.2 安装在升级角色前必须报告版本漂移，而不是误报通过。
- CodexBar 仅作为可选外部工具引用；不复制其代码，因此本次不引入第三方源码或许可证文件。

## 验收标准

1. 没有 CodexBar 时，原有插件功能和测试保持正常。
2. 使用构造的 CodexBar JSON 时，项目、日期、模型、token 和成本输出准确。
3. 输出不泄露绝对路径、账号、认证信息或未知上游字段。
4. 文档不声称精确账单、模型验证、角色级 token 归因或固定节省比例。
5. 标准任务不再默认允许 explorer 和 reviewer；二者必须满足机器可读条件。
6. Superpowers 不得引入第二套代理编排。
7. 完整测试、敏感内容扫描和跨平台 CI 通过。
