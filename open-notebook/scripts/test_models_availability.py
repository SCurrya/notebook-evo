# -*- coding: utf-8 -*-
"""Test model availability across providers.

Reads API keys from environment variables (or the .env file) instead of
hard-coding secrets. Never commit real keys to this file.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _load_env(env_path: Path) -> None:
    """Load KEY=VALUE pairs from a .env file into os.environ (no override)."""
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _load_dotenv() -> None:
    # Allow explicit env override; fall back to the repo-local .env file.
    env_path = Path(__file__).resolve().parent.parent / ".env"
    _load_env(env_path)


XCORE_BASE = "https://xcode.best/v1"
OR_BASE = "https://openrouter.ai/api/v1"


def _key(name: str) -> str:
    _load_dotenv()
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"⚠️  缺少环境变量 {name}，请在 .env 中配置后重试")
        sys.exit(1)
    return value


def chat(base: str, key: str, model: str, timeout: int = 40) -> str:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "用一句话回答：什么是AI Agent？"}],
        "max_tokens": 80,
    }
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
        msg = data["choices"][0]["message"]["content"]
        return f"✅ {model}: {str(msg)[:80]}"
    except Exception as e:
        code = getattr(e, "code", type(e).__name__)
        detail = ""
        if hasattr(e, "read"):
            try:
                detail = e.read().decode()[:120]
            except Exception:
                pass
        return f"❌ {model}: {code} {detail}"


def main() -> None:
    xcode_key = _key("OPENAI_COMPATIBLE_API_KEY")
    or_key = _key("OPENROUTER_API_KEY")

    print("=== xcode.best ===")
    print(chat(XCORE_BASE, xcode_key, "gpt-5.6-luna"))
    print(chat(XCORE_BASE, xcode_key, "gpt-5.4-mini"))

    print("\n=== OpenRouter ===")
    print(chat(OR_BASE, or_key, "nvidia/nemotron-3-ultra-550b-a55b:free"))
    print(chat(OR_BASE, or_key, "deepseek/deepseek-chat-v3-0324:free"))


if __name__ == "__main__":
    main()
