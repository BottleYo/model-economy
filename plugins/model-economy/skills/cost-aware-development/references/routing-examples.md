# 路由示例

示例使用 [路由策略](routing-policy.json)中的唯一分类和角色集合。每行完整列出对应分类的基础、条件、必需、禁止角色与 `strong_max`；`—` 表示空集合。

| 场景 | 分类 ID | 基础允许角色 | 条件角色 | 必需角色 | 禁止角色 | `strong` 上限 |
| --- | --- | --- | --- | --- | --- | --- |
| 高风险安全迁移 | large_or_high_risk | model-economy-implementer；model-economy-explorer | — | model-economy-architect；model-economy-final-reviewer | model-economy-reviewer；model-economy-batch-worker | 2 |
| 引入新架构 | large_or_high_risk | model-economy-implementer；model-economy-explorer | — | model-economy-architect；model-economy-final-reviewer | model-economy-reviewer；model-economy-batch-worker | 2 |
| 广泛爆炸半径 | large_or_high_risk | model-economy-implementer；model-economy-explorer | — | model-economy-architect；model-economy-final-reviewer | model-economy-reviewer；model-economy-batch-worker | 2 |
| 已批准规格内的批量改名 | mechanical | model-economy-batch-worker | — | — | model-economy-architect；model-economy-final-reviewer；model-economy-implementer；model-economy-reviewer；model-economy-explorer | 0 |
| 已知文件的纯字面修正 | simple | — | — | — | model-economy-architect；model-economy-final-reviewer；model-economy-implementer；model-economy-reviewer；model-economy-explorer；model-economy-batch-worker | 0 |
| 跨模块、边界明确的低风险功能 | standard | model-economy-implementer；model-economy-reviewer；model-economy-explorer | model-economy-architect | — | model-economy-final-reviewer；model-economy-batch-worker | 1 |
| 标准任务两次实质失败 | standard | model-economy-implementer；model-economy-reviewer；model-economy-explorer | model-economy-architect | — | model-economy-final-reviewer；model-economy-batch-worker | 1 |

标准分类中的 architect 不是基础角色，只在 `failed_attempts >= 2` 时最多调用一次。architect 返回诊断决策后由 `balanced` 实施；若诊断发现大型/高风险，重新按 `classification_order` 分类。大型/高风险的 architect 和 final-reviewer 分别是设计审批与任务结束的完成门。
