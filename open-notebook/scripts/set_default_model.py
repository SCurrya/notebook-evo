# -*- coding: utf-8 -*-
"""Set gpt-5.6-luna (xcode.best) as the default chat model."""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

API = "http://127.0.0.1:5055"


def main() -> None:
    with urllib.request.urlopen(f"{API}/api/models", timeout=15) as r:
        models = json.loads(r.read())

    print("可用模型:")
    for m in models:
        print(f"  {m['id']} | {m.get('name')} | {m.get('provider')} | {m.get('type')}")

    # 优先 gpt-5.4-mini（gpt-5.6-luna 服务端 503 不可用）
    target = next(
        (m for m in models if "gpt-5.4" in (m.get("name") or "") and m.get("type") == "language"),
        None,
    )
    if target is None:
        target = next(
            (m for m in models if "gpt-5.6" in (m.get("name") or "") and m.get("type") == "language"),
            None,
        )
    if target is None:
        target = next(
            (m for m in models if m.get("provider") == "openai_compatible" and m.get("type") == "language"),
            None,
        )
    if target is None:
        print("ERROR: 未找到可用的 openai_compatible 语言模型")
        sys.exit(1)

    target_id = target["id"]
    print(f"\n设置为默认: {target_id} ({target.get('name')})")

    payload = {
        "default_chat_model": target_id,
        "large_context_model": target_id,
        "default_tools_model": target_id,
        "default_transformation_model": target_id,
    }
    req = urllib.request.Request(
        f"{API}/api/models/defaults",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="PUT",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        result = json.loads(r.read())
    print("默认模型已更新:", json.dumps(
        {k: v for k, v in result.items() if "model" in k}, ensure_ascii=False
    ))


if __name__ == "__main__":
    main()
