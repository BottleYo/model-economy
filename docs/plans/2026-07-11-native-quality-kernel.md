> 历史资料：本文记录当时的实施过程，不代表当前安装或路由契约；现行规则以仓库当前 README、Skill 与机器路由策略为准。

# Model Economy 0.4.0 实施计划

## 范围

1. 用失败测试锁定核心 Skill 不再依赖 Superpowers，并覆盖原生质量门与显式 strict 交权。
2. 更新全局路由块，使已启用 Superpowers 时仍默认由 Model Economy 编排。
3. 新增精简质量门参考，更新路由示例和角色边界。
4. 将插件和项目版本升级到 0.4.0，更新中英文用户文档及变更日志。
5. 运行完整单元测试、敏感内容检查和本机升级验证。

## 验收标准

- 核心 Skill 不包含 `superpowers:` Skill 引用。
- 未安装或关闭 Superpowers 时，Model Economy 有完整设计、计划、测试和验证规则。
- 仅打开 Superpowers 不会触发交权；只有当前任务的明确 strict 指令才交权。
- strict 交权后 Model Economy 不再启动自己的角色或质量流程。
- 全局路由更新保持标记块外内容不变且可幂等执行。
- 全部测试通过，公开内容不包含凭据或个人数据。
