#!/usr/bin/env python3
"""生成中英文 v0.7.0 分工说明图；只使用自包含 SVG 图形与文字。"""

import argparse
from html import escape
from pathlib import Path


COPY = {
    "zh-CN": {
        "tagline": "小改动别开大会，难题再请强模型。",
        "intro": "先看风险，再选路线。按下表从上往下匹配，不是每次都走四遍。",
        "columns": ("碰到什么活儿", "怎么安排", "检查不能省"),
        "rows": [
            ("large-high-risk", "01  大型 / 高风险", "例如：权限调整、新架构", "strong 架构 → balanced 实现", "→ strong 独立终审", "先确认设计，再看交付证据", "需要健康增强与角色隔离"),
            ("mechanical", "02  机械任务", "例如：有固定规则的批量修改", "五项机械条件全部满足", "才考虑 economy 批处理", "每一项都要能验证", "不满足条件就不硬降档"),
            ("simple", "03  简单任务", "例如：已知配置，改完可直接查", "当前会话直接处理", "不新开子任务", "做完运行对应检查", "改一行，不用凑一桌人"),
            ("standard", "04  标准任务", "其余普通开发、已知行为的修复", "主会话或 balanced 实现", "探索、审查按需要加入", "检查范围跟着风险走", "有具体能力不匹配可提早诊断"),
        ],
        "left_title": "侧边栏任务：先授权，再开工",
        "left": ("机械 / 标准任务可按条件派发；需宿主支持。", "模型与推理强度分别请求；被拒绝就停。", "直接修补优先回原任务，不重讲整部前传。"),
        "right_title": "同一个工作包，共用一本账",
        "right": ("最多 3 个新执行上下文 / 6 次执行请求。", "默认并发 2；继续与重试也计数。", "这是策略级上限，不是平台强制额度。"),
        "footer": "角色路线描述健康增强模式。核心模式不调用缺失角色；高风险缺隔离先停。",
        "limit": "真实可见任务创建、续改与复杂并行尚未实测；不承诺固定 Token 节省。",
    },
    "en": {
        "tagline": "A tiny edit should not need a committee.",
        "intro": "Check risk first. Take the first matching route below, not all four.",
        "columns": ("THE JOB", "WHO HANDLES IT", "WHAT GETS CHECKED"),
        "rows": [
            ("large-high-risk", "01  LARGE / HIGH RISK", "Permissions or new architecture", "strong design / balanced build", "strong independent final review", "Approve design; verify evidence", "Healthy enhancement + isolation"),
            ("mechanical", "02  MECHANICAL", "Repeated edits with fixed rules", "All five conditions must hold", "before economy batch work", "Check every result", "No forced downgrade"),
            ("simple", "03  SIMPLE", "Known setting, direct check", "Handle it in the current task", "No new subtask", "Run the relevant check", "No committee required"),
            ("standard", "04  STANDARD", "Other ordinary development", "Main task or balanced build", "Explore / review when needed", "Match checks to the risk", "Evidence can trigger diagnosis"),
        ],
        "left_title": "VISIBLE TASKS NEED PERMISSION",
        "left": ("Mechanical / standard work; host support required.", "Request model and reasoning; stop if rejected.", "Reuse the task for a direct fix. Skip the recap."),
        "right_title": "ONE WORK PACKAGE, ONE BUDGET",
        "right": ("Up to 3 new contexts / 6 execution requests.", "Default concurrency: 2. Follow-ups count too.", "Policy-level caps, not platform quotas."),
        "footer": "Role routes assume healthy enhancement. Core mode has no custom roles; high-risk isolation gates remain.",
        "limit": "Live visible-task trials remain unverified. No fixed token-savings promise.",
    },
}


def render(language):
    copy = COPY[language]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="1060" viewBox="0 0 1440 1060" role="img" aria-labelledby="title desc">',
             '<title id="title">Model Economy v0.7.0</title>',
             f'<desc id="desc">{escape(copy["intro"])}</desc>',
             '<rect width="1440" height="1060" fill="#f5f2eb"/>',
             '<g font-family="Arial, PingFang SC, Microsoft YaHei, sans-serif">']

    def text(x, y, value, size=22, color="#202a2a", weight="400", fit=None):
        attr = f' data-fit="{fit}"' if fit else ''
        parts.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}"{attr}>{escape(value)}</text>')

    def rect(identifier, x, y, width, height, fill):
        parts.append(f'<rect id="{identifier}" x="{x}" y="{y}" width="{width}" height="{height}" rx="8" fill="{fill}"/>')

    text(48, 65, "MODEL ECONOMY", 34, weight="700")
    text(1220, 63, "v0.7.0", 22, "#41675d")
    text(48, 125, copy["tagline"], 36, weight="700")
    text(48, 164, copy["intro"], 20, "#52615e")
    for x, label in zip((70, 496, 978), copy["columns"]):
        text(x, 217, label, 18, "#52615e", "700")
    for index, (route, name, example, who, detail, check, note) in enumerate(copy["rows"]):
        top = 236 + index * 125
        parts.append(f'<g data-route="{route}">')
        for col, (x, width, fill) in enumerate(((48, 416, "#ffffff"), (474, 470, "#e4eee8"), (954, 438, "#ffffff"))):
            rect(f'{route}-{col}', x, top, width, 113, fill)
        text(70, top + 38, name, 23, weight="700", fit=f'{route}-0')
        text(70, top + 76, example, 19, "#52615e", fit=f'{route}-0')
        text(496, top + 38, who, 22, fit=f'{route}-1')
        text(496, top + 76, detail, 20, "#41675d", fit=f'{route}-1')
        text(978, top + 38, check, 21, fit=f'{route}-2')
        text(978, top + 76, note, 19, "#52615e", fit=f'{route}-2')
        parts.append('</g>')
    for key, x in (("left", 48), ("right", 730)):
        rect(key, x, 763, 662, 173, "#e9e3d7")
        text(x + 22, 800, copy[key + "_title"], 22, weight="700", fit=key)
        for index, line in enumerate(copy[key]):
            text(x + 22, 838 + index * 30, line, 19, fit=key)
    text(48, 980, copy["footer"], 18, "#52615e")
    text(48, 1015, copy["limit"], 18, "#52615e")
    return '\n'.join(parts + ['</g>', '</svg>', ''])


def main():
    parser = argparse.ArgumentParser(description="生成 Model Economy 分工图")
    parser.add_argument("--output-dir", type=Path, default=Path("assets"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for language in COPY:
        (args.output_dir / f"model-economy-flow-{language}.svg").write_text(render(language), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
