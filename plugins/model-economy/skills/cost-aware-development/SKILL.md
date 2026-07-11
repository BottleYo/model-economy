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

## 路由规则

1. 大型/高风险命中任一高风险、新架构或广泛爆炸半径条件。只读 `model-economy-architect`（`strong`）必须在设计审批前完成架构边界、风险和决策输出，且绝不输出计划、补丁或代码。设计获批后，主 agent 或 `model-economy-implementer`（`balanced`）使用 `superpowers:writing-plans` 和 TDD 实施；验证完成后，`model-economy-final-reviewer`（`strong`）必须完成复核，任务才能结束。
2. 机械任务必须同时满足五个 economy 条件；简单任务必须同时满足已知文件、无开放判断、可直接验证且不是创造性/行为变更。简单任务由主 agent 用 `balanced` 完成，不启动 subagent。
3. 其余任务均为标准 fallback。标准任务由 `balanced` 在审批后计划和实施，基础允许角色包含 `model-economy-implementer`。`model-economy-architect` 不在基础角色中；仅当 `failed_attempts >= 2` 时最多调用一次作诊断决策，随后由 `balanced` 实施。诊断若发现大型/高风险，重新运行完整分类并改走大型流程。
4. `model-economy-explorer` 只做最小化事实收集；`model-economy-batch-worker` 只能处理策略允许的机械工作。每个任务最多三个 subagent，且不得递归委派。
5. 委派写入前先声明每个 agent 的文件集合。写入集合必须互斥；发现重叠时，主 agent 负责串行执行相关 agent，不能并行写入。

## 上下文与交付

每次委派必须使用[上下文契约](references/context-contract.md)，并按[角色矩阵](references/role-matrix.md)限定职责。发送前先移除密钥、token、个人/生产数据、内部 URL 和无关路径；必要值使用占位符。角色回复不是完成证据，主 agent 必须独立核对文件引用与验证结果。

若运行环境尚未验证模型隔离或角色身份，明确写出“模型隔离未验证”；仍按上述工程流程继续。

六类典型选择见[路由示例](references/routing-examples.md)。
