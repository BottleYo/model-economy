# 贡献指南

感谢你改进 Model Economy。提交前请先确认变更保持成本路由、权限边界和公开承诺一致。

## 开始之前

- 缺陷、安装问题和功能建议请使用对应 Issue 模板。
- 安全问题不要公开提交，请按照 [安全策略](SECURITY.zh-CN.md)使用 GitHub Security Advisory。
- 大型行为变更应先说明目标、非目标、兼容性和验证方法。

## 本地开发

运行时要求 Python 3.11 或更高版本。测试依赖可使用项目声明的 test dependency group 安装。

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_sensitive_content.py .
git diff --check
```

新增公开命令、文档、Skill、角色字段、站点页面或视觉资源时，应增加能防止中英文、manifest、策略和实现漂移的测试。

## Pull Request

PR 应包含：

- 变更目的与用户影响。
- 测试命令及结果。
- 安全、隐私、安装和兼容性影响。
- 未验证事项与剩余风险。

不要提交凭据、认证文件、原始会话、私人路径、生产数据或内部 URL。
