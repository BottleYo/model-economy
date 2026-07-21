# 官方审核合成 Fixture

这些文件只用于 Model Economy 0.6.0 的公开审核测试，不包含真实账户、认证信息、网络访问或生产数据。提交后，审核材料使用发布标签中的稳定 URL：

`https://github.com/BottleYo/model-economy/tree/v0.6.0/docs/submission/fixtures`

## 对应关系

| 正向用例 | Fixture | 起点检查 |
| --- | --- | --- |
| 1. 简单任务 | `simple/` | `cd simple && python3 -m unittest -v` |
| 2. 机械任务 | `mechanical/` | `cd mechanical && python3 validate.py` |
| 3. 标准缺陷 | `standard/` | `cd standard && python3 -m unittest -v`，起点应有 1 个失败 |
| 4. 增强模式高风险 | `high-risk/` | `cd high-risk && python3 -m unittest -v` |
| 5. Superpowers 交权 | 不需要代码 fixture | 分别使用已安装/未安装 Superpowers 的干净测试环境 |

`standard/` 的失败是审核任务的预置缺陷，不纳入仓库自身 `tests/` 套件。审核完成后应恢复 fixture 起点或使用新的临时副本，避免前一用例污染后一用例。
