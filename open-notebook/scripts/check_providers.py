# -*- coding: utf-8 -*-
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    with urllib.request.urlopen("http://127.0.0.1:5055/api/providers", timeout=15) as r:
        providers = json.loads(r.read())
    print(f"providers: {len(providers)} 个")
    for p in providers[:8]:
        print(f"  {p['name']} | mods={p['modalities']} | configured={p['configured']}")


if __name__ == "__main__":
    main()
