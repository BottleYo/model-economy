[English](../en/cli-reference.md)

# CLI 参考

请在仓库根目录运行本地 CLI：

```sh
python3 plugins/model-economy/scripts/model_economy.py <command>
```

Windows 请将 `python3` 替换为 `py -3.11`。每条命令均可接受 `--codex-home <directory>`；`doctor` 还接受 `--codex-bin <command>`。

## `install`

```sh
python3 plugins/model-economy/scripts/model_economy.py install --profile {inherited,openai-56} [--force]
```

安装一个内置档案。`--force` 会覆盖冲突的受管理文件。

## `configure`

```sh
python3 plugins/model-economy/scripts/model_economy.py configure --profile {inherited,openai-56} [--force]
python3 plugins/model-economy/scripts/model_economy.py configure --strong <strong-model> --balanced <balanced-model> --economy <economy-model> [--force]
```

只能使用 `--profile`，或同时给出三个显式模型参数，不能两者并用。

## `verify`

```sh
python3 plugins/model-economy/scripts/model_economy.py verify [--quiet]
```

检查本地安装状态。`--quiet` 会隐藏面向人的报告。

## `doctor`

```sh
python3 plugins/model-economy/scripts/model_economy.py doctor [--smoke]
```

诊断本地前置条件和安装状态。`--smoke` 会尝试启动 Subagent，但不验证角色或模型身份。

## `upgrade`

```sh
python3 plugins/model-economy/scripts/model_economy.py upgrade [--dry-run] [--force]
```

`--dry-run` 只报告受管理变更，不会写入。`--force` 会覆盖冲突的受管理文件。

## `export-profile` 与 `import-profile`

```sh
python3 plugins/model-economy/scripts/model_economy.py export-profile <path>
python3 plugins/model-economy/scripts/model_economy.py import-profile <path> [--force]
```

导出会写入当前档案；导入会安装文件中的档案。显式映射必须提供完整三个档位。

## `uninstall`

```sh
python3 plugins/model-economy/scripts/model_economy.py uninstall [--purge] [--force]
```

不带 `--purge` 时，本地插件配置会保留。`--force` 会绕过固定名称的 Model Economy 角色文件的状态归属证明；只有确认这些文件应删除时才使用。

## `enable-global-routing` 与 `disable-global-routing`

```sh
python3 plugins/model-economy/scripts/model_economy.py enable-global-routing
python3 plugins/model-economy/scripts/model_economy.py disable-global-routing
```

两个命令只会添加或删除 `$CODEX_HOME/AGENTS.md` 中 Model Economy 的受管理块。

## 退出码

| 代码 | 含义 |
| --- | --- |
| `0` | 命令成功。 |
| `1` | 环境、配置、验证或 I/O 失败。 |
| `2` | 受管理文件冲突。 |
| `64` | CLI 用法或参数无效。 |

设置流程请阅读[安装指南](installation.md)，路由行为请阅读[工作原理](how-it-works.md)。
