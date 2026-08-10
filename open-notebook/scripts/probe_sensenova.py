# -*- coding: utf-8 -*-
"""Probe SenseNova chat models.

Reads the API key from environment variables (or the repo .env file).
Never hard-code secrets in this file.
"""
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

BASE = "https://token.sensenova.cn/v1"
MODELS = ["sensenova-6.7-flash-lite", "sensenova-u1-fast", "deepseek-v4-flash"]


def load_env():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def probe(model: str, key: str) -> str:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "用一句话介绍你自己"}],
        "max_tokens": 100,
    }
    req = urllib.request.Request(
        BASE + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            choice = data["choices"][0]
            msg = choice.get("message", {})
            content = msg.get("content") or ""
            reasoning = msg.get("reasoning") or msg.get("reasoning_content") or ""
            usage = data.get("usage", {})
            snippet = (content or reasoning).strip()[:60]
            return f"OK tokens={usage.get('total_tokens')} -> {snippet}"
    except urllib.error.HTTPError as e:
        d = e.read().decode()[:120]
        return f"{e.code}: {d}"
    except Exception as e:
        return f"{type(e).__name__}: {str(e)[:80]}"


def main():
    load_env()
    key = os.environ.get("SENSENOVA_API_KEY", "").strip()
    if not key:
        print("Missing SENSENOVA_API_KEY in .env")
        sys.exit(1)
    for m in MODELS:
        print(f"{m}: {probe(m, key)}")


if __name__ == "__main__":
    main()
