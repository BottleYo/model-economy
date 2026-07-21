#!/usr/bin/env python3
"""生成六张自包含、可重复构建的小红书 3:4 SVG 卡片。"""

import argparse
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "assets/promotion"
CARDS = (
    ("01", "为什么要做模型成本路由？", "日常修改不必套用高风险项目的全部流程", "先看风险，再决定需要多少能力与审查。"),
    ("02", "四类任务，一套明确顺序", "大型/高风险 → 机械 → 简单 → 标准", "首个命中类别决定路线，标准任务是兜底。"),
    ("03", "核心模式：安装后即可用", "简单、机械、标准任务由主 Agent 执行", "原生质量门继续生效，不调用不存在的角色。"),
    ("04", "增强模式：六角色可选", "架构、实现、探索、审查各有权限边界", "本地 CLI 安装角色配置；身份仍标记为未验证。"),
    ("05", "不承诺固定节省比例", "Token 与成本通过 A/B 协议记录", "不做角色级 Token 推断，不把估算写成事实。"),
    ("06", "先从一个真实任务开始", "安装 → 查看 status → 运行示例 → 提交反馈", "社区开源项目；可随时停用或卸载增强配置。"),
)


def svg(number: str, title: str, lead: str, note: str) -> str:
    values = tuple(map(escape, (number, title, lead, note)))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1440" viewBox="0 0 1080 1440">
  <rect width="1080" height="1440" fill="#141719"/>
  <rect x="72" y="72" width="936" height="1296" rx="30" fill="#1B2023" stroke="#647077" stroke-width="2"/>
  <text x="116" y="156" fill="#34C6A4" font-family="system-ui, sans-serif" font-size="32" font-weight="700">MODEL ECONOMY · {values[0]}/06</text>
  <text x="116" y="330" textLength="848" lengthAdjust="spacingAndGlyphs" fill="#F5F7F7" font-family="system-ui, sans-serif" font-size="68" font-weight="700">{values[1]}</text>
  <line x1="116" y1="400" x2="964" y2="400" stroke="#647077" stroke-width="2"/>
  <text x="116" y="548" textLength="848" lengthAdjust="spacingAndGlyphs" fill="#F6B74D" font-family="system-ui, sans-serif" font-size="46" font-weight="650">{values[2]}</text>
  <rect x="116" y="690" width="848" height="320" rx="22" fill="#142925" stroke="#34C6A4" stroke-width="2"/>
  <text x="164" y="812" textLength="752" lengthAdjust="spacingAndGlyphs" fill="#F5F7F7" font-family="system-ui, sans-serif" font-size="40">{values[3]}</text>
  <text x="116" y="1282" fill="#C8D0D2" font-family="system-ui, sans-serif" font-size="30">社区开源 · 策略级上限 · 无固定节省承诺</text>
</svg>
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for number, title, lead, note in CARDS:
        (args.output_dir / f"xiaohongshu-{number}.svg").write_text(
            svg(number, title, lead, note), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
