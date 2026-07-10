# 安全策略

## 支持版本

当前仅维护最新发布版本。请先升级到最新版本后复现问题。

## 私密报告

请不要在公开 Issue、讨论区或提交中披露安全问题、凭据、私人路径或可利用细节。请在仓库的 GitHub Security Advisory 流程中选择“Report a vulnerability”提交私密报告。

报告请包含受影响版本、复现步骤、影响范围和可选修复建议。请使用最小化示例，并移除任何敏感内容。维护者会在 GitHub Security Advisory 中确认收到报告、评估影响，并在适当时协调修复和披露。

## 发布前检查

维护者在发布前运行：

```sh
python scripts/check_sensitive_content.py .
python -m unittest discover -s tests -v
```

敏感内容检查覆盖工作树，以及每个可达 Git 提交的作者和提交者邮箱、提交消息、树路径与文本 blob。发现问题时只输出相对路径、行号和规则名，不输出匹配原文。
