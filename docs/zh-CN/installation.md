[English](../en/installation.md)

# 安装指南

> v0.7.0 已纳入角色覆盖和迁移功能。真实桌面派发试点经批准跳过，不代表通过。增强模式升级前请先执行 `upgrade --dry-run` 预览，并保留迁移备份。

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

### v0.7.0：模型与推理强度分开配置

例如保留模型继承，同时指定实现角色的推理强度：

```sh
python3 plugins/model-economy/scripts/model_economy.py configure --profile inherited --reasoning model-economy-implementer=medium
```

新安装默认：架构师和终审员 high，实现者和审查者 medium，探索者和批处理者 low。继承模型不代表继承推理强度，也不保证实际选择了更轻量模型。

完整显式三档映射还可通过 `--role-model` 覆盖单个角色模型。角色名、合法强度及参数规则见 [CLI 参考](cli-reference.md)。`configure` 从所选基础档案重建配置；它会重设未显式保留的覆盖。需要保留旧安装设置时使用 `upgrade`。

## 验证与诊断

```sh
python3 plugins/model-economy/scripts/model_economy.py verify
python3 plugins/model-economy/scripts/model_economy.py status --format json
python3 plugins/model-economy/scripts/model_economy.py doctor
python3 plugins/model-economy/scripts/model_economy.py doctor --smoke
```

普通 `doctor` 只检查受管理文件和 `codex --version`，不会调用检查范围更广的 `codex doctor`，也不会检查认证、session 或数据库工件。`doctor --smoke` 会显式启动一次经过认证的临时 Codex 运行，可能产生用量，并检查 Subagent 是否启动；它不验证角色或模型身份。

`verify` 还会检查已安装的受管理角色模板是否与当前插件版本一致。更新插件快照后，需要先运行 `upgrade`，验证才会恢复通过。

## 启用全局路由

```sh
python3 plugins/model-economy/scripts/model_economy.py enable-global-routing
python3 plugins/model-economy/scripts/model_economy.py disable-global-routing
```

这两个命令只管理 `$CODEX_HOME/AGENTS.md` 中的 Model Economy 块。启用可重复执行；禁用会保留受管理块以外的原有文本。项目级 `AGENTS.md` 可以覆盖全局说明。

v0.7.0 更新了可见任务的授权与兼容说明。若之前已经启用全局路由，安装新版本后可审阅并再次运行 `enable-global-routing` 刷新该受管理区块；普通 `upgrade` 不自动改写它。没有启用过全局路由的用户不需要新增此配置。

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

重新安装插件后，当前版本的 Skill 会在新任务中可发现；最后一条命令会幂等刷新受管理全局规则，使原生默认和 strict 交权规则保持最新。`--force` 会覆盖冲突的受管理文件。通常应先处理差异。

### v0.7.0：配置迁移与备份

旧 schema 1 配置可以只读加载，`status` 与 `verify` 不会迁移安装。正式 `upgrade` 将配置写为 schema 2，保留原模型和经所有权检查的实际角色推理强度；旧档案导入保留旧推理默认。state 和 status JSON 仍为 schema 1。

不要用重复运行本地 `install` 代替迁移：已有受管理 schema 1 安装会被拒绝，带 `--force` 也一样。请先 `upgrade`；只有明确想重设档案时才使用 `configure`。

先审阅 `upgrade --dry-run` 的版本、模型与 reasoning 差异，再运行正式升级。干运行不写文件、不创建备份。正式 v1→v2 迁移会报告唯一备份目录，结构如下：

```text
model-economy/backups/upgrade-<唯一标识>/
├── config.toml
├── state.json
├── agents/（六个原角色文件）
└── manifest.json
```

备份仅包含上述原始受管理工件。manifest 保存相对名称、迁移前哈希、原权限以及预期迁移后哈希，不包含其他用户文件。备份失败时安装不变；写入事务失败时恢复原字节和权限。迁移备份在卸载及 purge 后保留。

如需人工回退：

1. 暂停会使用这份配置的任务，确认备份对应本次迁移。
2. 对照 manifest 的迁移后哈希检查当前八个受管理工件。任一不一致时停止覆盖，先保留并核对后来修改的内容。
3. 核对备份文件的迁移前哈希，拒绝缺失文件、链接或被修改的备份。
4. 在维护窗口成套恢复六角色、config、state，并恢复记录的文件权限；不要只把 schema 数字改回 1，也不要只恢复一个文件。
5. 切回与备份对应的插件版本，运行该版本的 `verify`。未通过前不继续使用增强模式。

本版不提供自动降级命令。不要把迁移备份作为跨设备档案复制。

## 导出与导入档案

v0.7.0 导出的 schema 2 档案保存角色模型覆盖与完整 reasoning；接收设备需使用 v0.7.0+。只导出不会改写原安装；档案不携带任务、项目和本机安装状态。

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
