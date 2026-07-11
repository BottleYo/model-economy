[English](SECURITY.md)

# 安全策略

## 支持版本

仅支持最新发布版本。条件允许时，请先升级后再复现和报告问题。

## 私密报告

请不要在公开 Issue、讨论区或提交中披露漏洞、凭据、私人路径或可利用细节。请使用 GitHub Security Advisories，并选择 **Report a vulnerability** 私密报告。

报告应包含受影响版本、复现步骤、影响范围和可选修复建议。请使用足够小的示例，并移除敏感信息。维护者会在安全公告中确认收到报告、评估影响，并在适当时协调修复与披露。

## 信任边界

CLI 只管理 `CODEX_HOME` 下的 Model Economy 配置、已声明角色文件，以及 `$CODEX_HOME/AGENTS.md` 中带标记的 Model Economy 受管理区块；它不管理凭据，也不验证模型或角色身份。可选的 `usage` 命令会执行用户选定的 CodexBar CLI，并只公开受资源边界保护的字段白名单；Model Economy 不直接读取 CodexBar 凭据或 session 文件，但不能替第三方可执行文件保证内部行为。配置损坏或归属冲突会失败关闭。只有用户明确授权的 `--force` 操作可以越过相应的归属或冲突保护。详细说明见[README](README.zh-CN.md)。

## 发布检查

维护者运行：

```sh
python3 scripts/check_sensitive_content.py .
python3 -m unittest discover -s tests -v
```

敏感内容检查覆盖工作树，以及每个可达 Git 提交的作者和提交者邮箱、消息、路径和文本 blob。发现问题时只输出相对路径、行号和规则名，不回显匹配内容。
