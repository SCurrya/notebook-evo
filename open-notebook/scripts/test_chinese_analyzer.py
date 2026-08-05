# -*- coding: utf-8 -*-
"""Test SurrealDB Chinese analyzer support."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from surrealdb import Surreal


async def main() -> None:
    db = Surreal("http://127.0.0.1:8000")
    db.signin({"username": "root", "password": "root"})
    db.use("open_notebook", "open_notebook")

    # Test 1: ngram analyzer
    try:
        r = await db.query(
            "DEFINE ANALYZER IF NOT EXISTS chinese_analyzer TOKENIZERS ngram(1,2) FILTERS lowercase;"
        )
        print("ngram analyzer OK:", r)
    except Exception as e:
        print("ngram FAILED:", str(e)[:200])

    # Test 2: verify chinese fulltext search works with ngram
    try:
        r = await db.query(
            "CREATE ONLY test_cn:1 SET content = '面试热点导读包含公务员考试相关知识';"
        )
        print("create doc:", r[0]["status"] if isinstance(r, list) else r)
    except Exception as e:
        print("create FAILED:", str(e)[:200])

    try:
        r = await db.query(
            "DEFINE INDEX IF NOT EXISTS idx_test_cn ON TABLE test_cn COLUMNS content SEARCH ANALYZER chinese_analyzer BM25 HIGHLIGHTS;"
        )
        print("define index OK:", r[0]["status"] if isinstance(r, list) else r)
    except Exception as e:
        print("index FAILED:", str(e)[:200])

    try:
        r = await db.query(
            "SELECT * FROM test_cn WHERE content @1@ '面试' LIMIT 5;"
        )
        print("search 面试:", len(r) if isinstance(r, list) else r)
    except Exception as e:
        print("search FAILED:", str(e)[:200])

    # cleanup
    try:
        await db.query("DELETE test_cn:1; REMOVE INDEX idx_test_cn ON TABLE test_cn;")
    except Exception:
        pass
    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
