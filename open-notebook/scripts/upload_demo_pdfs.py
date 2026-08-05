# -*- coding: utf-8 -*-
"""Upload demo PDFs to a notebook via the API (multipart)."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

BASE = "http://127.0.0.1:5055"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--notebook-id", required=True)
    parser.add_argument("--pdf-dir", default="data/demo")
    parser.add_argument("--embed", action="store_true", help="同步向量化（需 embedding 模型）")
    args = parser.parse_args()

    pdf_dir = Path(args.pdf_dir)
    pdfs = sorted(p for p in pdf_dir.glob("*.pdf") if p.name != "gongkao-mianshi.pdf" or True)
    print(f"找到 {len(pdfs)} 个 PDF")

    for pdf in pdfs:
        boundary = "----PythonBoundary"
        fields = {
            "type": "upload",
            "notebooks": json.dumps([args.notebook_id]),
            "embed": "true" if args.embed else "false",
            "async_processing": "true",
        }
        body = bytearray()
        for k, v in fields.items():
            body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
        body.extend(
            (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
                f"filename=\"{pdf.name}\"\r\nContent-Type: application/pdf\r\n\r\n"
            ).encode()
        )
        body.extend(pdf.read_bytes())
        body.extend(f"\r\n--{boundary}--\r\n".encode())

        req = urllib.request.Request(
            f"{BASE}/api/sources",
            data=bytes(body),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode())
                ids = data.get("ids") or data.get("sources") or []
                print(f"[OK] {pdf.name} -> {resp.status} {ids if ids else data}")
        except Exception as e:  # noqa: BLE001
            print(f"[FAIL] {pdf.name} -> {e}")
            if hasattr(e, "read"):
                try:
                    print("  ", e.read().decode()[:300])
                except Exception:  # noqa: BLE001
                    pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
