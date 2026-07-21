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

## `status`

```sh
python3 plugins/model-economy/scripts/model_economy.py status [--format text|json]
```

报告插件版本以及推断得到的 `core`、`enhanced` 或 `degraded` 模式。该命令只读取 Model Economy 自己的配置、状态和六个声明过的角色路径，不联网、不启动子进程。JSON 使用稳定的 `status_schema_version: 1`。核心模式和健康增强模式返回 `0`；降级状态返回 `1`，归属或哈希冲突返回 `2`。身份字段始终为 `false`。`core` 只表示本地六角色增强缺失，不能证明 Codex 已安装或启用插件。

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

## `usage`

```sh
python3 plugins/model-economy/scripts/model_economy.py usage [--days 1..365] [--project <path>] [--format text|json] [--codexbar-bin <path>]
```

读取 CodexBar 0.41.0 或更高版本的本地成本 JSON。默认范围为最近 30 个日历日。`--project` 精确选择项目路径，但公开输出只保留目录名。`--format json` 输出 Model Economy 稳定的 `usage_schema_version: 1` 封装。

CodexBar 是可选的第三方本地程序。Model Economy 不读取其凭据或 session 文件，但不能替 CodexBar 保证内部行为。成本是 CodexBar 估算值；角色归因和模型身份仍未验证。macOS 与 Linux 支持常规 CLI 发现；Windows 需要通过 `--codexbar-bin` 或 `CODEXBAR_BIN` 显式提供兼容可执行文件。

## 退出码

| 代码 | 含义 |
| --- | --- |
| `0` | 命令成功。 |
| `1` | 环境、配置、验证或 I/O 失败。 |
| `2` | 受管理文件冲突。 |
| `64` | CLI 用法或参数无效。 |

设置流程请阅读[安装指南](installation.md)，路由行为请阅读[工作原理](how-it-works.md)。
