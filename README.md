# Model Economy

Model Economy 是一个 Codex 插件，用稳定角色和可替换的模型映射，让开发任务优先使用最低可胜任的能力档。它适用于需要保留设计审批、测试和验证纪律，同时希望控制模型额度消耗的代码工作流。

它不替代工程判断，也不会自动执行发布、修改用户数据或统计 token 用量。当前版本不自动统计 token；请以 Codex 自身提供的用量信息为准。

## 要求与兼容性

- Python 3.11 或更高版本；运行时只使用标准库。
- 支持 Linux、macOS 和 Windows。Windows 示例可将 `python` 替换为 `py -3.11`。
- Codex CLI 需要提供 `plugin` 子命令。用 `codex plugin --help` 检查本机版本。
- 需要 Git 的仓库才能让敏感内容检查覆盖可达提交历史；没有 Git 历史时只检查工作树。

## 安装

先获取公开仓库，再把其中的 marketplace 加入 Codex。以下命令与当前 Codex CLI 的 `plugin marketplace add`、`plugin add` 语法一致：

```sh
git clone <公开仓库地址>
cd model-economy
codex plugin marketplace add .
codex plugin add model-economy@model-economy-public
```

安装插件后，使用仓库中的本地 CLI 写入角色配置。可从三种配置方式中选择一种：

```sh
# 1. inherited：角色继承 Codex 当前模型设置
python plugins/model-economy/scripts/model_economy.py install --profile inherited

# 2. openai-56：使用随插件提供的三档模型映射
python plugins/model-economy/scripts/model_economy.py install --profile openai-56

# 3. custom：显式提供 strong、balanced、economy 三个模型
python plugins/model-economy/scripts/model_economy.py configure \
  --strong <strong-model> \
  --balanced <balanced-model> \
  --economy <economy-model>
```

所有命令都可通过 `--codex-home <目录>` 指向另一套 Codex 配置目录；`--codex-bin <命令>` 用于 `doctor` 选择要诊断的 Codex 可执行文件。完整参数以 `python plugins/model-economy/scripts/model_economy.py --help` 为准。

## 诊断与 Smoke

安装后运行：

```sh
python plugins/model-economy/scripts/model_economy.py verify
python plugins/model-economy/scripts/model_economy.py doctor
python plugins/model-economy/scripts/model_economy.py doctor --smoke
```

`doctor --smoke` 分三层报告：Subagent 启动、角色身份和模型身份。它只能观察到 Subagent 是否启动；当前 Codex JSONL 不提供 `agent_type`，因此角色身份显示“未验证”，模型身份也显示“未验证”。不要把 smoke 输出当成角色或模型隔离已被证明的证据。

## 更新与卸载

更新 marketplace 快照后，使用本地 CLI 更新已管理的角色文件：

```sh
codex plugin marketplace upgrade model-economy-public
python plugins/model-economy/scripts/model_economy.py upgrade
```

普通卸载保留本地配置；`--purge` 同时删除插件管理的配置。若文件被手动修改，命令会以冲突失败，先检查差异；仅在确认需要覆盖时使用 `--force`。

```sh
python plugins/model-economy/scripts/model_economy.py uninstall
python plugins/model-economy/scripts/model_economy.py uninstall --purge
codex plugin remove model-economy@model-economy-public
```

## 兼容模式

`inherited` 是兼容模式：生成的角色文件不固定模型名，继续使用 Codex 当前的模型配置。`openai-56` 与 `custom` 会写入明确的角色模型映射。配置切换仍受完整性检查保护；若本地文件与记录不一致，先处理冲突再继续。

## 隐私与信任边界

本地 CLI 只管理 `CODEX_HOME/model-economy/` 下的 `config.toml` 和 `state.json`，以及 `CODEX_HOME/agents/` 中由它写入的角色文件。`config.toml` 保存档案名和可选模型标识，不应存放凭据。`state.json` 保存已管理文件及其哈希，是本地包管理元数据，不是防篡改凭证，也不应被当作授权来源。

CLI 对缺失、损坏或哈希不一致的配置和状态采取失败关闭策略，不会据此删除不确定归属的文件。`CODEX_HOME` 的访问控制、用户提示、其他插件和未受管理的角色文件均在本插件的信任边界之外。不要将凭据、私人路径、个人项目名或生产数据提交到本仓库；提交前运行：

```sh
python scripts/check_sensitive_content.py .
```

扫描器只打印相对路径、行号和规则名，不会回显疑似秘密原文；它还检查每个可达 Git 提交的作者和提交者邮箱、提交消息、树路径与文本 blob。

## 与 Superpowers 的关系

插件内的 `cost-aware-development` skill 约束模型角色选择，并要求继续遵循 Superpowers 的设计审批、计划、测试驱动开发和完成前验证流程。它不安装、不替换也不绕过 Superpowers；需要这些流程时，请在 Codex 环境中单独提供 Superpowers。

## 开发检查

```sh
python -m unittest discover -s tests -v
python scripts/check_sensitive_content.py .
```

CI 会在 Linux、macOS、Windows 的 Python 3.11 与 3.12 上运行相同检查。
