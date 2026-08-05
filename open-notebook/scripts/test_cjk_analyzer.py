# -*- coding: utf-8 -*-
"""Find a working Chinese-friendly analyzer for SurrealDB 2.3.7."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from surrealdb import Surreal

TEST_DOCS = [
    "面试热点导读包含公务员考试相关知识",
    "AI Agent 是人工智能智能体的核心概念",
    "混合检索结合了全文搜索与向量搜索的优势",
]


def main() -> None:
    db = Surreal("http://127.0.0.1:8000")
    db.signin({"username": "root", "password": "root"})
    db.use("open_notebook", "open_notebook")

    candidates = [
        ("blank_punct", "TOKENIZERS blank,punct FILTERS lowercase"),
        ("class_only", "TOKENIZERS class FILTERS lowercase"),
        ("no_filter", "TOKENIZERS blank,class,camel,punct FILTERS lowercase"),
        ("punct_only", "TOKENIZERS punct FILTERS lowercase"),
    ]

    for name, spec in candidates:
        print(f"\n=== {name}: {spec} ===")
        try:
            db.query(f"DEFINE ANALYZER IF NOT EXISTS a_{name} {spec};")
        except Exception as e:
            print(f"  define FAILED: {str(e)[:150]}")
            continue

        # clean table + reindex for this analyzer
        try:
            db.query("DELETE test_cjk:all;")
            db.query(f"REMOVE INDEX IF EXISTS idx_cjk ON TABLE test_cjk;")
            db.query(
                f"DEFINE INDEX IF NOT EXISTS idx_cjk ON TABLE test_cjk "
                f"COLUMNS content SEARCH ANALYZER a_{name} BM25 HIGHLIGHTS;"
            )
            for i, doc in enumerate(TEST_DOCS):
                db.query(
                    f"CREATE test_cjk:{i} SET content = \"{doc.replace('\"', '\\\"')}\";"
                )
            # wait for indexing (sync http should be immediate, but be safe)
            import time

            time.sleep(0.5)

            # test queries
            for q in ["面试", "公务员", "Agent", "混合检索", "向量"]:
                res = db.query(f"SELECT * FROM test_cjk WHERE content @1@ '{q}' LIMIT 5;")
                hits = len(res) if isinstance(res, list) else 0
                print(f"  query '{q}' -> {hits} hits")
        except Exception as e:
            print(f"  test FAILED: {str(e)[:200]}")

    # cleanup
    try:
        db.query("DELETE test_cjk:all;")
        db.query("REMOVE INDEX IF EXISTS idx_cjk ON TABLE test_cjk;")
    except Exception:
        pass


if __name__ == "__main__":
    main()
