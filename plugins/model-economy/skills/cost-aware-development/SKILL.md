---
name: cost-aware-development
description: 当任务涉及软件开发、调试、重构、测试、代码审查、架构设计、节省 token、成本路由或分层模型时使用。
---

# 成本感知开发

先按任务风险选能力，再按角色分配工作。成本优化不得跳过审批、设计、测试、验证或安全检查。

## 唯一分类表

[路由策略](references/routing-policy.json)是唯一可解析的任务分类、角色集合、条件门、完成门和 `strong` 上限事实源。按 `classification_order` 依次判断，并严格使用 `first_match`：首个匹配项就是唯一结果，最后的 `standard` 是默认 fallback。不因文件数、请求篇幅或用户要求省 token 而降级风险。

跨模块任务不自动是大型：架构不变、边界明确且低风险时为标准。只有新架构、广泛爆炸半径，或安全/隐私迁移才是大型/高风险。机械任务还必须满足全部五个 economy 条件；任一条件不满足则使用 `balanced`，发现高风险则升级为大型/高风险。

## 审批门

创造性或行为变更必须有 `approved_design` 或可追溯的 `approval_evidence`。没有审批证据时，禁止计划和实施；只能澄清、探索或让 architect 给出架构边界、风险与决策。纯字面改动，以及完全落在已批准规格内的确定性机械改动，是仅有例外。

已获批设计后，`balanced` 才能使用 `superpowers:writing-plans` 写计划并按 `superpowers:test-driven-development` 实施。创造性设计仍先使用 `superpowers:brainstorming` 取得审批；完成前使用 `superpowers:verification-before-completion` 取得新的验证证据。

## 单一编排权

按指令优先级只选择一套代理编排。Model Economy 获得编排权时，对角色拓扑、能力档、subagent 数量和完成门拥有唯一编排权；Superpowers 只提供执行方法，不得增加所选路由之外的 agent、计划、审查或完成门。更高优先级指令强制其他编排时，以该指令为准，Model Economy 只提供成本建议，不声称拥有编排权。

不得在同一任务中叠加完整的 `superpowers:subagent-driven-development`。可以复用 `dispatching-parallel-agents` 的并行方法，但只能启动当前路由允许的角色；`requesting-code-review` 可以提供审查方法，不能自动增加未获路由允许的 reviewer。architect 的技术判断是 `brainstorming` 的输入，不等同于用户审批。

## 路由规则

1. 大型/高风险命中任一高风险、新架构或广泛爆炸半径条件。只读 `model-economy-architect`（`strong`）必须在设计审批前完成架构边界、风险和决策输出，且绝不输出计划、补丁或代码。设计获批后，主 agent 或 `model-economy-implementer`（`balanced`）使用 `superpowers:writing-plans` 和 TDD 实施；验证完成后，`model-economy-final-reviewer`（`strong`）必须完成复核，任务才能结束。
2. 机械任务必须同时满足五个 economy 条件；简单任务必须同时满足已知文件、无开放判断、可直接验证且不是创造性/行为变更。简单任务由主 agent 用 `balanced` 完成，不启动 subagent。
3. 其余任务均为标准 fallback。主 agent 或一个 `model-economy-implementer` 必须二选一承担主要实现，不能重复实施。文件位置、依赖或事实不明确时才允许 explorer；跨模块、关键逻辑、非显然回归风险或实质测试疑问出现时才允许 reviewer。`model-economy-architect` 仅当 `failed_attempts >= 2` 时最多调用一次作诊断决策，随后由 `balanced` 实施。诊断若发现大型/高风险，重新运行完整分类并改走大型流程。
4. `model-economy-explorer` 只做最小化事实收集；`model-economy-batch-worker` 只能处理策略允许的机械工作。每个任务生命周期最多启动三个 subagent，重新分类不重置预算，且不得递归委派。标准 architect 诊断只有在新设计审批前完成且满足大型 architect 输出契约时，才能计入重分类后的 architect 完成门。
5. 委派写入前先声明每个 agent 的文件集合。写入集合必须互斥；发现重叠时，主 agent 负责串行执行相关 agent，不能并行写入。

## 上下文与交付

每次委派必须使用[上下文契约](references/context-contract.md)，并按[角色矩阵](references/role-matrix.md)限定职责。发送前先移除密钥、token、个人/生产数据、内部 URL 和无关路径；必要值使用占位符。角色回复不是完成证据，主 agent 必须独立核对文件引用与验证结果。

若运行环境尚未验证模型隔离或角色身份，明确写出“模型隔离未验证”；仍按上述工程流程继续。

reviewer 负责变更评估，报告缺陷、回归风险和测试缺口；final-reviewer 只评估大型/高风险任务的残余交付风险、架构和安全边界及证据缺口；`verification-before-completion` 只取得并核对新鲜验证证据，不重新进行完整代码审查。修复审查发现后的定向复审不算重复证据层。

六类典型选择见[路由示例](references/routing-examples.md)。
