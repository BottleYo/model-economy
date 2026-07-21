[English](../en/installation.md)

# 安装指南

## 前置条件

- Python 3.11 或更高版本；运行时只使用标准库。
- Codex CLI 需要支持 `plugin marketplace add` 与 `plugin add`；可运行 `codex plugin --help` 检查。
- 若希望敏感内容检查覆盖可达提交历史，需要 Git；没有 Git 历史时扫描器只检查工作树。

支持 Linux、macOS 和 Windows。本文使用 `python3` 的位置，在 Windows 中可替换为 `py -3.11`。

## 可选用量依赖

`usage` 命令需要 CodexBar 0.41.0 或更高版本。Model Economy 会在 macOS 与 Linux 上按常规位置发现官方 CLI；若不在 `PATH`，可显式指定 CLI Helper：

```sh
python3 plugins/model-economy/scripts/model_economy.py usage --codexbar-bin /path/to/CodexBarCLI
```

Model Economy 不宣称 Windows 获得 CodexBar 官方支持；需要通过 `--codexbar-bin` 或 `CODEXBAR_BIN` 显式提供兼容可执行文件。CodexBar 是可选依赖，缺失不会影响安装、路由、升级或验证。

## 安装插件

克隆公开仓库，加入 marketplace，再安装插件：

```sh
git clone https://github.com/BottleYo/model-economy.git
cd model-economy
codex plugin marketplace add .
codex plugin add model-economy@model-economy-public
```

完成上述目录式安装后即可使用**核心模式**。四个 Skill 不依赖用户级角色文件；安装后请新建任务。

若需要可选的六角色**增强模式**，推荐安装 `inherited` 档案：

```sh
python3 plugins/model-economy/scripts/model_economy.py install --profile inherited
python3 plugins/model-economy/scripts/model_economy.py verify
python3 plugins/model-economy/scripts/model_economy.py status
```

`inherited` 让角色继续继承当前 Codex 的模型配置。内置 `openai-56` 映射和自定义映射属于进阶选项；两者都不能证明模型身份。

## 配置自定义档案

请同时提供三个档位：

```sh
python3 plugins/model-economy/scripts/model_economy.py configure --strong <strong-model> --balanced <balanced-model> --economy <economy-model>
```

也可以使用 `configure --profile inherited` 或 `configure --profile openai-56` 选择内置档案。只有在审阅过受管理文件冲突后才使用 `--force`。

## 验证与诊断

```sh
python3 plugins/model-economy/scripts/model_economy.py verify
python3 plugins/model-economy/scripts/model_economy.py status --format json
python3 plugins/model-economy/scripts/model_economy.py doctor
python3 plugins/model-economy/scripts/model_economy.py doctor --smoke
```

`doctor --smoke` 检查 Subagent 是否启动，不验证角色或模型身份。

`verify` 还会检查已安装的受管理角色模板是否与当前插件版本一致。更新插件快照后，需要先运行 `upgrade`，验证才会恢复通过。

## 启用全局路由

```sh
python3 plugins/model-economy/scripts/model_economy.py enable-global-routing
python3 plugins/model-economy/scripts/model_economy.py disable-global-routing
```

这两个命令只管理 `$CODEX_HOME/AGENTS.md` 中的 Model Economy 块。启用可重复执行；禁用会保留受管理块以外的原有文本。项目级 `AGENTS.md` 可以覆盖全局说明。

## 与 Superpowers 共存

Superpowers 不是安装依赖。未安装、已关闭或已开启 Superpowers 时，Model Economy 默认都使用自己的原生质量门。仅仅开启插件不会授权完整 Superpowers 流程。

如果当前任务需要完整 Superpowers，请明确写出“本任务使用完整 Superpowers”或“Superpowers strict mode”。Model Economy 随后只提供模型与成本建议，不再启动自己的角色或追加质量流程。该授权不跨任务保存。Model Economy 不会安装、启停或修改 Superpowers。

## 升级

`codex plugin marketplace upgrade` 只刷新 Git marketplace 快照，不能刷新从本地路径添加的 marketplace。请先更新仓库，再重新注册本地 marketplace、重新安装插件快照，最后查看并应用受管理文件升级：

```sh
git pull --ff-only
codex plugin remove model-economy@model-economy-public
codex plugin marketplace remove model-economy-public
codex plugin marketplace add .
codex plugin add model-economy@model-economy-public
python3 plugins/model-economy/scripts/model_economy.py upgrade --dry-run
python3 plugins/model-economy/scripts/model_economy.py upgrade
python3 plugins/model-economy/scripts/model_economy.py enable-global-routing
```

重新安装插件后，0.6.0 的 Skill 会在新任务中可发现；最后一条命令会幂等刷新受管理全局规则，使原生默认和 strict 交权规则保持最新。`--force` 会覆盖冲突的受管理文件。通常应先处理差异。

## 导出与导入档案

```sh
python3 plugins/model-economy/scripts/model_economy.py export-profile <path>
python3 plugins/model-economy/scripts/model_economy.py import-profile <path>
```

导入档案若包含显式模型映射，必须同时包含 `strong`、`balanced` 与 `economy`。

## 卸载

```sh
python3 plugins/model-economy/scripts/model_economy.py uninstall
python3 plugins/model-economy/scripts/model_economy.py uninstall --purge
codex plugin remove model-economy@model-economy-public
```

普通卸载保留本地插件配置；`--purge` 同时删除受管理配置。移除插件不会自动删除全局路由；如需移除，请先运行 `disable-global-routing`。

跨设备使用时，应在另一台设备克隆同一发布标签、重新安装插件，并只用 `export-profile` / `import-profile` 迁移不含密钥的模型档案偏好。不要复制整个 `CODEX_HOME`、状态文件、账户数据或认证材料。

## 指定 Codex 位置

每条本地命令均接受 `--codex-home <directory>`。`doctor` 还接受 `--codex-bin <command>`，用于指定待诊断的 Codex 可执行文件。

继续阅读[工作原理](how-it-works.md)或 [CLI 参考](cli-reference.md)。
