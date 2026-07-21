# Model Economy 仓库协作规则

## 语言与定位

- 仓库内新建或修改的维护文档默认使用简体中文；面向国际用户的 README、站点、Release 与提交材料同步提供英文版本。
- Model Economy 是社区开源项目，不代表 OpenAI 官方产品。
- 不宣传固定 Token 节省比例，不声称已验证实际模型或角色身份。
- “上限”统一描述为策略级上限（policy-level caps），不得表述为平台运行时强制。

## 开发边界

- Python 运行时保持 3.11+ 标准库依赖；测试依赖单独声明。
- 不读取或修改认证缓存、原始 session、账号额度、私人项目数据或其他插件文件。
- 本地生命周期 CLI 只管理 `$CODEX_HOME/model-economy/`、六个 `model-economy-*.toml` 角色文件，以及全局 `AGENTS.md` 中带标记的受管理区块。
- `routing-policy.json` 是任务分类、角色集合、模式和完成门的唯一机器事实源。
- `config.toml` 与 `state.json` schema 变更必须有独立设计与迁移计划。

## 验证

提交前至少运行：

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_sensitive_content.py .
python3 /path/to/plugin-creator/scripts/validate_plugin.py plugins/model-economy
git diff --check
```

涉及站点、manifest、视觉资源或 CLI 时，必须同时更新对应契约测试。无法运行真实 Codex CLI 验收时，应明确记录环境原因，不得用静态测试替代身份验证结论。
