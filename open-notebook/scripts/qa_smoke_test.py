# -*- coding: utf-8 -*-
"""
QA 冒烟测试（Agent 自验）。

验证所有核心 API 端点是否可用，生成验收报告。
用法:
    python scripts/qa_smoke_test.py [--base URL] [--token TOKEN]
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

BASE = "http://127.0.0.1:5055"

CHECKS = [
    # (名称, 方法, 路径, body 或 None)
    ("笔记本列表", "GET", "/api/notebooks", None),
    ("健康检查", "GET", "/health", None),
    ("混合检索", "POST", "/api/search/hybrid", {"query": "AI Agent 技术", "limit": 5}),
    ("自适应检索", "POST", "/api/search/adaptive", {"query": "什么是MCP协议", "limit": 5}),
    ("评估报告列表", "GET", "/api/eval/reports", None),
    ("单题评估", "POST", "/api/eval/run-single", {"question": "什么是MCP？", "reference": "MCP由Anthropic提出", "top_k": 3}),
    ("Agent列表", "GET", "/api/agents", None),
    ("Agent统计", "GET", "/api/agents/stats", None),
    ("图谱问答", "POST", "/api/knowledge-graph/ask", {"question": "什么是AI Agent"}),
    ("图谱抽取", "POST", "/api/knowledge-graph/extract", {"notebook_id": "demo"}),
    ("模型列表", "GET", "/api/models", None),
    ("凭证列表", "GET", "/api/credentials", None),
    ("设置", "GET", "/api/settings", None),
]


def request(base: str, method: str, path: str, body=None, token: str = "") -> tuple[int, str]:
    url = f"{base}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, ""
    except urllib.error.HTTPError as e:
        return e.code, str(e)
    except Exception as e:  # noqa: BLE001
        return 0, str(e)


def main() -> int:
    parser = argparse.ArgumentParser(description="QA 冒烟测试")
    parser.add_argument("--base", default=BASE)
    parser.add_argument("--token", default="")
    args = parser.parse_args()

    lines = ["=== Agent 自验报告 ===", f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}", ""]
    passes = fails = 0
    for name, method, path, body in CHECKS:
        code, err = request(args.base, method, path, body, args.token)
        if 200 <= code < 500:
            passes += 1
            lines.append(f"[PASS] {name} -> {code}")
        else:
            fails += 1
            lines.append(f"[FAIL] {name} -> {code} {err}")

    lines.append("")
    lines.append(f"=== 汇总: {passes} 通过 / {fails} 失败 ===")
    report = "\n".join(lines)
    print(report)

    out = Path(__file__).resolve().parent.parent / "qa_report.txt"
    out.write_text(report, encoding="utf-8")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
