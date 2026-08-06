# -*- coding: utf-8 -*-
import json
import urllib.request


def main() -> None:
    with urllib.request.urlopen("http://127.0.0.1:5055/api/models", timeout=15) as r:
        models = json.loads(r.read())
    langs = [m for m in models if m.get("type") == "language"]
    print(f"language models: {len(langs)}")
    for m in langs:
        print(f"  {m['id']} | {m.get('name')} | provider={m.get('provider')}")


if __name__ == "__main__":
    main()
