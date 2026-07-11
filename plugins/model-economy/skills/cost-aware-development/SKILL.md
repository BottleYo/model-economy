---
name: cost-aware-development
description: 当任务涉及软件开发、调试、重构、测试、代码审查、架构设计、节省 token、成本路由或分层模型时使用。
---

# 成本感知开发

先按风险选择最低可胜任能力，再决定需要多少流程和角色。简单任务保持简单；成本优化不得绕过真实风险、安全边界或完成证据。

## 唯一分类表

[路由策略](references/routing-policy.json)是任务分类、角色集合、条件门、完成门和 `strong` 上限的唯一机器事实源。按 `classification_order` 和 `first_match` 选择唯一类别；最后的 `standard` 是默认 fallback，不因文件数、请求篇幅或省 token 要求而降级风险。

跨模块不自动等于大型。只有新架构、广泛爆炸半径，或安全、隐私等高风险边界才进入大型/高风险。机械任务必须满足全部五项 economy 条件；任一条件不满足就使用 `balanced`。

## 原生质量内核

Model Economy 自带意图门、计划门、测试门和证据门，不依赖其他开发方法插件。开始任务时只判断各门是否命中；命中时才读取并执行[质量门](references/quality-gates.md)，不得为了形式启动未命中的流程。

目标存在实质歧义、高风险决策或未批准架构边界时，实施前必须取得可追溯审批。目标、约束和验收已经明确时，不重复要求设计审批。简单任务不写持久化计划；标准任务只使用与复杂度匹配的短计划；大型/高风险任务才要求持久化计划。测试强度匹配行为风险。声明完成前始终核对新鲜验证证据。

## Superpowers 兼容

安装、启用或发现 Superpowers 不构成启用完整 Superpowers 工作流的授权。默认由 Model Economy 独占任务分类、代理编排和质量门，不自动调用其完整 brainstorming、planning、subagent-driven-development、executing-plans 或 finishing 流程。

只有用户在当前任务中明确要求“完整 Superpowers”、“full Superpowers”或“Superpowers strict mode”时，才把本次任务的流程编排权交给 Superpowers。交权后 Model Economy 只提供模型与成本建议，不得启动 Model Economy 角色，也不得追加自己的计划、审查或验证流程。交权不跨任务保存；如果运行环境没有 Superpowers，应明确报告 strict mode 不可用。

用户只要求测试先行、系统化调试或完成前验证等单项方法，不等于授权完整 Superpowers，也不触发交权。

## 单一编排权

按指令优先级只选择一套代理编排。Model Economy 获得编排权时，对角色拓扑、能力档、subagent 数量和完成门拥有唯一编排权，不得增加所选路由之外的 agent、计划、审查或完成门。不得叠加第二套 subagent-driven-development；更高优先级指令强制其他编排时，Model Economy 退化为成本建议。

## 路由规则

1. 大型/高风险：只读 `model-economy-architect`（`strong`）必须在设计审批前输出架构边界、风险和决策，且不得写计划、补丁或代码。审批后由主 agent 或一个 `model-economy-implementer`（`balanced`）实施；验证后必须由 `model-economy-final-reviewer`（`strong`）复核才能完成。
2. 机械：只有满足全部 economy 条件时才允许 `model-economy-batch-worker`。简单：由主 agent 用 `balanced` 直接完成，不启动 subagent。
3. 标准：主 agent 或一个 `model-economy-implementer` 必须二选一承担主要实现。文件位置、依赖或事实不明确时才允许 explorer；跨模块、关键逻辑、非显然回归风险或实质测试疑问出现时才允许 reviewer。两次实质失败后才允许一次只读 architect 诊断；发现高风险时重新分类。
4. 每个任务生命周期最多启动三个 subagent，重新分类不重置预算，且不得递归委派。委派写入前声明文件集合；集合重叠时由主 agent 串行协调。

## 上下文与交付

委派使用[上下文契约](references/context-contract.md)和[角色矩阵](references/role-matrix.md)。发送前移除密钥、token、个人或生产数据、内部 URL 和无关路径。角色回复不是完成证据，主 agent 必须独立核对文件引用与验证结果。

reviewer 负责变更评估、回归风险和测试缺口；final-reviewer 只评估大型/高风险任务的残余交付风险、架构与安全边界和证据缺口；证据门只核对新鲜验证证据，不重新做完整代码审查。模型或角色身份无法验证时明确披露。

典型选择见[路由示例](references/routing-examples.md)。
