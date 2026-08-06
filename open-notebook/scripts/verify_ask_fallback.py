# -*- coding: utf-8 -*-
"""Verify: /api/config works + ask falls back from gpt-5.6-luna to gpt-5.4-mini."""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

API = "http://127.0.0.1:5055"


def main() -> None:
    # 1. config
    with urllib.request.urlopen(f"{API}/api/config", timeout=15) as r:
        print("1. /api/config ->", r.status, json.loads(r.read().decode()))

    # 2. defaults
    with urllib.request.urlopen(f"{API}/api/models/defaults", timeout=15) as r:
        d = json.loads(r.read())
        print("2. default chat:", d.get("default_chat_model"))

    # 3. ask with default (gpt-5.6-luna should 503 -> fallback to gpt-5.4-mini)
    model = d.get("default_chat_model")
    body = {
        "question": "AI Agent 的核心能力是什么？",
        "strategy_model": model,
        "answer_model": model,
        "final_answer_model": model,
    }
    req = urllib.request.Request(
        f"{API}/api/search/ask",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            content = r.read().decode()
        print(f"3. ask -> 200, {len(content)} bytes (stream)")
        print("   前 200 字:", content[:200].replace("\n", " "))
    except Exception as e:
        print(f"3. ask FAILED: {e}")
        if hasattr(e, "read"):
            try:
                print("   body:", e.read().decode()[:200])
            except Exception:
                pass


if __name__ == "__main__":
    main()
