[English](README.md)

# Model Economy

> 让强模型负责关键判断，而不是日常机械工作。

![Model Economy](assets/social-preview.png)

Model Economy 是一个面向 Codex 的能力分层开发工作流插件。它把高能力模型留给设计、风险和最终审查关口，把实现与有边界的资料收集分配给合适的能力档位，并用原生轻量质量门按风险控制审批、计划、测试和验证。

它可以显示 CodexBar 的本地 token 与估算成本摘要，但不自行扫描 session，不承诺节省结果，不验证模型或角色身份，也不替代工程判断。

## 为什么需要它

- 将 `strong` 能力留给影响更大的判断，而非例行编辑。
- 为调研、实现、审查和固定规则批处理明确职责边界。
- 只在存在实质歧义或高风险决策时要求审批，并按行为风险选择测试强度。
- 完成前始终要求新鲜验证证据，不让简单任务承担完整方法论流程。

## 工作原理

![Model Economy 任务流](assets/model-economy-flow-zh-CN.svg)

任务按固定顺序分类：大型或高风险、机械、简单、标准。首个命中的类别决定可用角色与 `strong` 调用上限。完整规则见[工作原理](docs/zh-CN/how-it-works.md)。

插件不依赖 Superpowers。即使已安装或开启 Superpowers，默认仍使用 Model Economy 原生流程；只有用户在当前任务中明确要求“完整 Superpowers”或“Superpowers strict mode”时才交出本次编排权。

## 60 秒安装

```sh
git clone https://github.com/BottleYo/model-economy.git
cd model-economy
codex plugin marketplace add .
codex plugin add model-economy@model-economy-public
python3 plugins/model-economy/scripts/model_economy.py install --profile inherited
python3 plugins/model-economy/scripts/model_economy.py verify
```

Windows 请将 `python3` 替换为 `py -3.11`。安装、升级、迁移和卸载详见[安装指南](docs/zh-CN/installation.md)。

## 查看用量

安装 CodexBar 0.41.0 或更高版本后，可以在不暴露账号凭据的情况下查看本地 Codex 用量：

```sh
python3 plugins/model-economy/scripts/model_economy.py usage
python3 plugins/model-economy/scripts/model_economy.py usage --days 7 --project .
python3 plugins/model-economy/scripts/model_economy.py usage --format json
```

适配器显示 CodexBar 的本地 token 总量、模型拆分与估算成本，不会把 token 归因到 Model Economy 角色。

## 任务分类

| 类别 | 条件 | 默认能力 | `strong` 上限 |
| --- | --- | --- | --- |
| 大型或高风险 | 任一高风险边界、新架构或影响范围很广 | `strong` 关口加 `balanced` 实现 | 2 |
| 机械 | 五项固定规则条件全部满足 | `economy` 批处理 | 0 |
| 简单 | 文件已知、无开放判断、可直接验证，且不改变创意或行为 | 主 agent | 0 |
| 标准 | 兜底类别 | `balanced` | 1 |

## 角色

| 角色 | 能力 | 权限 | 职责 |
| --- | --- | --- | --- |
| `model-economy-architect` | `strong` | 只读 | 高风险设计审批前输出架构边界、风险与决策 |
| `model-economy-final-reviewer` | `strong` | 只读 | 高风险验证后输出问题、证据缺口与剩余风险 |
| `model-economy-implementer` | `balanced` | 可写工作区 | 在批准范围内实现、测试和验证 |
| `model-economy-reviewer` | `balanced` | 只读 | 给出独立问题与回归风险 |
| `model-economy-explorer` | `economy` | 只读 | 最小文件清单与事实收集 |
| `model-economy-batch-worker` | `economy` | 可写工作区 | 按固定规则编辑并逐项检查 |

## 轻量工程能力

0.5.0 提供三个可独立触发的叶子 Skill：

- `domain-context`：只提炼当前任务需要的领域术语、不变量与 ADR 约束。
- `module-design`：检查模块边界、知识泄漏和变更面，给出最小结构改进。
- `disposable-prototype`：用隔离的一次性实验回答具体未知，不把探索代码当成品。

这些 Skill 不启动 subagent，不改变任务分类、模型映射、六角色拓扑或质量门，也不自行提交代码。涉及正式实现时仍回到 `cost-aware-development` 路由。它们是插件内置能力，不依赖外部工程方法插件。

## 全局路由

安装完成后，可把通用开发路由块加入全局 `$CODEX_HOME/AGENTS.md`：

```sh
python3 plugins/model-economy/scripts/model_economy.py enable-global-routing
```

命令可重复执行，只会改动 `$CODEX_HOME/AGENTS.md` 中带标记的 Model Economy 受管理区块。项目自己的 `AGENTS.md` 可以覆盖全局规则。需要移除时运行：

```sh
python3 plugins/model-economy/scripts/model_economy.py disable-global-routing
```

## 安全与信任边界

本地 CLI 只管理 `CODEX_HOME` 下自己的配置、声明过的角色文件，以及 `$CODEX_HOME/AGENTS.md` 中带标记的 Model Economy 受管理区块；缺失、损坏或冲突的受管理状态会失败关闭。只有用户明确授权的 `--force` 操作可以越过相应的归属或冲突保护。它不管理凭据、项目数据、未归属文件、其他插件，也不接管 `CODEX_HOME` 的访问控制。

`doctor --smoke` 只能观察 Subagent 是否启动。当前 Codex JSONL 不提供 `agent_type`，因此角色身份和模型身份均未验证。报告漏洞前请阅读[安全策略](SECURITY.zh-CN.md)。

## 文档

- [安装指南](docs/zh-CN/installation.md)：前置条件、安装、升级、档案迁移和卸载。
- [工作原理](docs/zh-CN/how-it-works.md)：分类、角色边界、审批关口与限制。
- [CLI 参考](docs/zh-CN/cli-reference.md)：命令、参数与退出码。
- [安全策略](SECURITY.zh-CN.md)：私密漏洞报告与发布检查。
- [更新记录](CHANGELOG.zh-CN.md)：已发布变更。

## 当前限制

- 用量摘要来自可选的 CodexBar 本地统计；Model Economy 不自行扫描 session，也不把 token 归因到角色。
- `doctor --smoke` 不验证角色或模型身份。
- 插件不安装、启停或修改 Superpowers；仅在当前任务获得明确 strict 授权时与其交接编排权。
- 全局路由不带项目特定上下文，插件卸载时也不会自动删除。

## 贡献

提交变更前请运行本地检查：

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_sensitive_content.py .
```

自定义模型映射时，请在同一行完整指定三个能力档位：

```sh
# 3. custom
python3 plugins/model-economy/scripts/model_economy.py configure --strong <strong-model> --balanced <balanced-model> --economy <economy-model>
py -3.11 plugins/model-economy/scripts/model_economy.py configure --strong <strong-model> --balanced <balanced-model> --economy <economy-model>
```

## 许可证

[MIT](LICENSE)
