# 路由示例

以下涉及六角色的路线只适用于健康增强模式。核心模式的简单任务由主 agent 执行；机械和标准任务仅在已获创建授权、工具可用且满足可见任务契约时可选 `visible_task`。核心模式的大型/高风险任务先报告角色隔离缺口并等待用户选择。

示例使用 [路由策略](routing-policy.json)中的唯一分类和角色集合。每行完整列出对应分类的基础、条件、必需、禁止角色与 strong 双预算；`—` 表示空集合。可见任务的模式映射和前置条件以策略为准，不能据此宣称自定义角色身份。

| 场景 | 分类 ID | 基础允许角色 | 条件角色 | 必需角色 | 禁止角色 | strong 职责席位 | strong 执行请求 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 高风险安全迁移 | large_or_high_risk | model-economy-implementer；model-economy-explorer | — | model-economy-architect；model-economy-final-reviewer | model-economy-reviewer；model-economy-batch-worker | 2 | 4 |
| 引入新架构 | large_or_high_risk | model-economy-implementer；model-economy-explorer | — | model-economy-architect；model-economy-final-reviewer | model-economy-reviewer；model-economy-batch-worker | 2 | 4 |
| 广泛爆炸半径 | large_or_high_risk | model-economy-implementer；model-economy-explorer | — | model-economy-architect；model-economy-final-reviewer | model-economy-reviewer；model-economy-batch-worker | 2 | 4 |
| 已批准规格内的批量改名 | mechanical | model-economy-batch-worker | — | — | model-economy-architect；model-economy-final-reviewer；model-economy-implementer；model-economy-reviewer；model-economy-explorer | 0 | 0 |
| 已知文件的纯字面修正 | simple | — | — | — | model-economy-architect；model-economy-final-reviewer；model-economy-implementer；model-economy-reviewer；model-economy-explorer；model-economy-batch-worker | 0 | 0 |
| 跨模块、边界明确的低风险功能 | standard | model-economy-implementer | model-economy-architect；model-economy-reviewer；model-economy-explorer | — | model-economy-final-reviewer；model-economy-batch-worker | 1 | 2 |
| 标准任务两次实质失败 | standard | model-economy-implementer | model-economy-architect；model-economy-reviewer；model-economy-explorer | — | model-economy-final-reviewer；model-economy-batch-worker | 1 | 2 |

标准分类中的 explorer、reviewer 和 architect 都是条件角色；architect 在两次实质失败或有证据的具体能力不匹配时，可作首次诊断和一次必要澄清。architect 返回诊断决策后由 `balanced` 实施；若诊断发现大型/高风险，重新按 `classification_order` 分类但不重置根工作包预算。大型/高风险的 architect 和 final-reviewer 分别是设计审批与任务结束的完成门。
