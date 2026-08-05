# -*- coding: utf-8 -*-
"""Quick test: Chinese hybrid search on the running API."""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def post(path: str, body: dict):
    req = urllib.request.Request(
        "http://127.0.0.1:5055" + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read())


def main() -> None:
    queries = ["公务员面试热点", "AI Agent", "人工智能"]
    for q in queries:
        try:
            r = post(
                "/api/search/hybrid",
                {"query": q, "limit": 5, "search_sources": True, "search_notes": True, "rerank": False},
            )
            print(f"hybrid({q}): total={r['total_count']} vector={r['vector_hits']} text={r['text_hits']}")
            for item in r["results"][:3]:
                print(f"  - [{item['result_type']}] {item['title']} | {item['content_preview'][:50]}")
        except Exception as e:
            print(f"hybrid({q}) FAILED: {e}")


if __name__ == "__main__":
    main()
