# 全局开发路由实施计划

> **面向代理工作者：** 必须使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans` 按任务实施，并使用复选框跟踪步骤。

**目标：** 为 Model Economy 增加安全、幂等、可撤销的全局开发路由命令，并发布为 `0.2.0`。

**架构：** 新建独立的 `global_routing.py` 负责标记验证和纯文本转换；CLI 只负责解析命令、选择 `$CODEX_HOME/AGENTS.md` 和执行原子文件操作。受管理块外的用户内容不参与语义解析。

**技术栈：** Python 3.11+ 标准库、`unittest`、现有 `atomic_write`、Codex 插件清单与 GitHub Actions。

---

### Task 1：全局规则纯文本转换

**文件：**
- 创建：`plugins/model-economy/scripts/model_economy_lib/global_routing.py`
- 创建：`tests/test_global_routing.py`

- [ ] 编写失败测试，覆盖空文件创建、已有内容追加、规范块幂等、旧块替换。
- [ ] 运行 `python3 -m unittest tests.test_global_routing -v`，确认因模块或函数缺失失败。
- [ ] 实现固定标记、规范规则文本和 `enable_text(text)` 纯函数。
- [ ] 编写失败测试，覆盖禁用、重复禁用、损坏/重复/逆序标记。
- [ ] 实现 `disable_text(text)` 和严格标记验证。
- [ ] 重跑目标测试，确认全部通过。

### Task 2：文件操作与 CLI

**文件：**
- 修改：`plugins/model-economy/scripts/model_economy_lib/global_routing.py`
- 修改：`plugins/model-economy/scripts/model_economy_lib/cli.py`
- 修改：`tests/test_cli.py`

- [ ] 编写失败测试，验证 `enable-global-routing` 使用显式 `--codex-home` 创建 `AGENTS.md`，且不触碰默认主目录。
- [ ] 编写失败测试，验证重复启用零写入、禁用只删除受管理块、损坏标记返回冲突码 2。
- [ ] 实现 `enable_global_routing(path)` 与 `disable_global_routing(path)`，使用 `atomic_write` 和现有 `ChangeSet`。
- [ ] 在 CLI 注册两个子命令并输出统一变更摘要。
- [ ] 运行 `python3 -m unittest tests.test_cli tests.test_global_routing -v`，确认通过。

### Task 3：自动发现、版本与中文文档

**文件：**
- 修改：`plugins/model-economy/skills/cost-aware-development/SKILL.md`
- 修改：`plugins/model-economy/.codex-plugin/plugin.json`
- 修改：`README.md`
- 修改：`CHANGELOG.md`
- 修改：`tests/test_structure.py`

- [ ] 编写失败结构测试，要求版本为 `0.2.0`、skill description 覆盖通用软件开发触发词、README 包含启用/禁用命令和安全边界。
- [ ] 更新插件版本与 skill description，不修改路由正文策略。
- [ ] 在 README 添加跨项目自动启用、撤销和另一台电脑安装说明。
- [ ] 在 CHANGELOG 新增 `0.2.0` 中文条目。
- [ ] 运行结构测试、插件校验和 skill 校验。

### Task 4：审查、发布与真实安装验证

**文件：**
- 修改：`.superpowers/sdd/progress.md`（忽略文件，仅本地审计）

- [ ] 运行 `python3 -m unittest discover -s tests -v`。
- [ ] 运行 `python3 scripts/check_sensitive_content.py .`。
- [ ] 运行插件与 skill 校验器，以及 `git diff --check`。
- [ ] 使用 `gpt-5.6-sol + medium` 做最终只读审查并修复发现。
- [ ] 合并到 `main`，推送 GitHub，等待 Linux/macOS/Windows × Python 3.11/3.12 CI 全绿。
- [ ] 在真实 `$CODEX_HOME` 执行一次启用、验证规范块存在、重复启用，再执行禁用恢复原文件；仅比较前后哈希是否一致，不输出内容或哈希值。
- [ ] 创建 `v0.2.0` Release，并在发布说明中明确全局规则可被项目 `AGENTS.md` 覆盖。
