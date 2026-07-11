[English](../en/installation.md)

# 安装指南

## 前置条件

- Python 3.11 或更高版本；运行时只使用标准库。
- Codex CLI 需要支持 `plugin marketplace add` 与 `plugin add`；可运行 `codex plugin --help` 检查。
- 若希望敏感内容检查覆盖可达提交历史，需要 Git；没有 Git 历史时扫描器只检查工作树。

支持 Linux、macOS 和 Windows。本文使用 `python3` 的位置，在 Windows 中可替换为 `py -3.11`。

## 安装插件

克隆公开仓库，加入 marketplace，再安装插件：

```sh
git clone https://github.com/BottleYo/model-economy.git
cd model-economy
codex plugin marketplace add .
codex plugin add model-economy@model-economy-public
```

安装一个内置档案：

```sh
python3 plugins/model-economy/scripts/model_economy.py install --profile inherited
python3 plugins/model-economy/scripts/model_economy.py install --profile openai-56
```

`inherited` 让角色继续继承当前 Codex 的模型配置；`openai-56` 会写入内置的三档映射。首次配置只需选择其中一条命令。

## 配置自定义档案

请同时提供三个档位：

```sh
python3 plugins/model-economy/scripts/model_economy.py configure --strong <strong-model> --balanced <balanced-model> --economy <economy-model>
```

也可以使用 `configure --profile inherited` 或 `configure --profile openai-56` 选择内置档案。只有在审阅过受管理文件冲突后才使用 `--force`。

## 验证与诊断

```sh
python3 plugins/model-economy/scripts/model_economy.py verify
python3 plugins/model-economy/scripts/model_economy.py doctor
python3 plugins/model-economy/scripts/model_economy.py doctor --smoke
```

`doctor --smoke` 检查 Subagent 是否启动，不验证角色或模型身份。

## 启用全局路由

```sh
python3 plugins/model-economy/scripts/model_economy.py enable-global-routing
python3 plugins/model-economy/scripts/model_economy.py disable-global-routing
```

这两个命令只管理 `$CODEX_HOME/AGENTS.md` 中的 Model Economy 块。启用可重复执行；禁用会保留受管理块以外的原有文本。项目级 `AGENTS.md` 可以覆盖全局说明。

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
```

`--force` 会覆盖冲突的受管理文件。通常应先处理差异。

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

## 指定 Codex 位置

每条本地命令均接受 `--codex-home <directory>`。`doctor` 还接受 `--codex-bin <command>`，用于指定待诊断的 Codex 可执行文件。

继续阅读[工作原理](how-it-works.md)或 [CLI 参考](cli-reference.md)。
