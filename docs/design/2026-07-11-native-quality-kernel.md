# Model Economy 原生质量内核设计

## 背景

Model Economy 0.3.0 直接引用 Superpowers 的 brainstorming、writing-plans、test-driven-development 和 verification-before-completion。这样既让未安装 Superpowers 的环境缺少完整执行路径，也可能在两套插件同时启用时触发重复设计、计划、代理编排和审查。

## 决策

Model Economy 0.4.0 将质量要求收回核心插件，并采用单入口、按风险渐进加载的原生质量内核。Superpowers 不再是运行依赖，也不会因为已安装或已启用而自动接管任务。

原生质量内核包含四个条件门：

- 意图门：仅在目标存在实质歧义、方案会显著改变结果或涉及高风险边界时要求澄清与审批。
- 计划门：简单任务不写计划，标准任务使用短计划，大型或高风险任务才要求持久化计划。
- 测试门：缺陷修复、核心逻辑和高风险变更优先测试先行；机械、文档和不可合理测试的改动使用风险匹配的替代证据。
- 证据门：任何完成声明前都必须取得新鲜、可执行的验证证据，无法验证时明确披露。

详细规则存放在 `cost-aware-development/references/quality-gates.md`，主 Skill 只保留路由摘要，避免简单任务加载多套独立工作流。

## Superpowers 兼容

安装、启用或发现 Superpowers 只表示能力可用，不构成完整流程授权。默认仍由 Model Economy 独占任务分类、代理编排和质量门。

只有用户在当前任务中明确要求“完整 Superpowers”或“Superpowers strict mode”时，才将本次任务的流程编排权交给 Superpowers。此时 Model Economy 只提供模型与成本建议，不启动角色、不追加计划、审查或验证流程。交权只对当前任务有效。

用户可以明确要求采用测试先行、系统化调试等单项方法；这种请求不等于 strict mode，也不授权 Superpowers 完整编排。

## 兼容矩阵

| Superpowers 状态 | 用户是否明确要求 strict | 行为 |
|---|---|---|
| 未安装 | 否 | Model Economy 原生流程 |
| 已安装但关闭 | 否 | Model Economy 原生流程 |
| 已安装并开启 | 否 | Model Economy 原生流程 |
| 已安装并开启 | 是 | Superpowers 编排；Model Economy 仅提供成本建议 |
| 未安装 | 是 | 明确报告能力不可用，不伪装执行 strict |

## 非目标

- 不复制或改名分发 Superpowers 原始 Skill。
- 不检测、安装、启用、关闭或修改其他插件。
- 不保存跨任务 strict 状态。
- 不削弱大型或高风险任务的 architect、审批和 final reviewer 要求。

## 升级

`enable-global-routing` 会幂等刷新 Model Economy 管理的全局规则块，使用户级指令明确上述优先级。普通 `upgrade` 保持现有模型配置和未受管理内容，不自动修改其他插件。

