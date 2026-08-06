# -*- coding: utf-8 -*-
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    body = {
        "question": "AI Agent 的核心能力是什么？",
        "strategy_model": "model:sqml7zpo1hp4assn0h2f",
        "answer_model": "model:sqml7zpo1hp4assn0h2f",
        "final_answer_model": "model:sqml7zpo1hp4assn0h2f",
    }
    req = urllib.request.Request(
        "http://127.0.0.1:5055/api/search/ask",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        content = r.read().decode()

    finals = re.findall(r'"type": "final_answer", "content": (.*?)\}\n\n', content, re.S)
    answers = re.findall(r'"type": "answer", "content": (.*?)\}\n\n', content, re.S)
    print(f"answers={len(answers)} finals={len(finals)}")
    if finals:
        text = json.loads(finals[-1])
        print("=== 最终回答 ===")
        print(text[:1000])


if __name__ == "__main__":
    main()
