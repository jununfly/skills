#!/usr/bin/env python3
"""Generate a structured Soul Interrogator review report as Markdown.

Usage:
    python generate_report.py <output_file> '<json_data>'

JSON structure:
{
    "original_idea": "一句话描述想法",
    "assumptions": [{"name": "假设A", "status": "稳固"}],
    "key_insight": {"before": "原本以为", "after": "现在意识到"},
    "fatal_risk": {"attack": "最致命攻击点", "chain": "连锁失败路径"},
    "defense": {"prevent": "预防方案", "buffer": "缓冲方案", "escape": "逃生方案"},
    "confidence": {"before": 8, "after": 6, "reason": "原因"},
    "next_step": "建议的下一步"
}
"""

import json
import sys
from pathlib import Path


TEMPLATE = """\
# 灵魂拷问审查报告

## 原始想法
{original_idea}

## 核心假设清单
| 假设 | 状态 |
|------|------|
{assumptions_table}

## 关键洞察
我原本以为 **{before}**，但现在意识到 **{after}**。

## 最致命风险
- **攻击点**：{attack}
- **连锁链条**：{chain}

## 防御方案
- **预防**：{prevent}
- **缓冲**：{buffer}
- **逃生**：{escape}

## 信心变化
- 攻击前信心：**{before_conf}/10**
- 攻击后信心：**{after_conf}/10**
- 原因：{reason}

## 建议下一步
{next_step}
"""


def main():
    if len(sys.argv) < 3:
        print("Usage: generate_report.py <output_file> '<json_data>'", file=sys.stderr)
        sys.exit(1)

    output_path = Path(sys.argv[1])
    data = json.loads(sys.argv[2])

    assumptions = data.get("assumptions", [])
    table_rows = "\n".join(
        f"| {a['name']} | {a['status']} |" for a in assumptions
    )

    risk = data.get("fatal_risk", {})
    defense = data.get("defense", {})
    confidence = data.get("confidence", {})
    insight = data.get("key_insight", {})

    report = TEMPLATE.format(
        original_idea=data.get("original_idea", ""),
        assumptions_table=table_rows if table_rows else "| — | — |",
        before=insight.get("before", ""),
        after=insight.get("after", ""),
        attack=risk.get("attack", ""),
        chain=risk.get("chain", ""),
        prevent=defense.get("prevent", ""),
        buffer=defense.get("buffer", ""),
        escape=defense.get("escape", ""),
        before_conf=confidence.get("before", "?"),
        after_conf=confidence.get("after", "?"),
        reason=confidence.get("reason", ""),
        next_step=data.get("next_step", ""),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"Report written to: {output_path}")


if __name__ == "__main__":
    main()
