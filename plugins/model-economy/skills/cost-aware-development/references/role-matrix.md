# 角色矩阵

角色权限以 [路由策略](routing-policy.json)为准；下表是同一策略的可读摘要。

| 角色 | 能力 | 何时使用 | 输出边界 |
| --- | --- | --- | --- |
| `model-economy-architect` | `strong`，只读 | 大型/高风险设计审批前的必需完成门；标准任务两次实质失败后的条件角色 | 只输出架构边界、风险、决策；不得写计划、补丁或代码 |
| `model-economy-final-reviewer` | `strong`，只读 | 大型/高风险验证后的必需完成门 | 缺陷、证据缺口、剩余风险；完成复核前不得结束任务 |
| `model-economy-implementer` | `balanced`，可写 | 已批准设计和计划后的实现、调试和测试 | 只改已声明且已获批的文件集合，按 TDD 实施 |
| `model-economy-reviewer` | `balanced`，只读 | 标准任务确需独立判断时 | 对差异和测试给出反馈；不写计划、补丁或代码 |
| `model-economy-explorer` | `economy`，只读 | 最小化文件定位、依赖清点、已知事实收集 | 最小文件清单、事实和约束；不做设计、计划或编辑 |
| `model-economy-batch-worker` | `economy`，可写 | 全部机械任务条件满足的固定规则批量工作 | 固定规则编辑及逐项检查；不做设计、计划或语义判断 |

主 agent 保留任务分级、审批检查、写入协调、风险决策和最终验证责任。
