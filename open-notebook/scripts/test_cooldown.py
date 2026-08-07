# -*- coding: utf-8 -*-
"""直接验证 ask.py 的模型 cooldown 逻辑。"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from open_notebook.graphs.ask import (
    _is_model_available,
    _mark_model_unavailable,
    _MODEL_COOLDOWN,
    _MODEL_COOLDOWN_SECONDS,
)


class InternalServerError(Exception):
    pass


def main():
    model_id = "model:sqml7zpo1hp4assn0h2f"
    print(f"初始可用性: {_is_model_available(model_id)} (应为 True)")
    _mark_model_unavailable(model_id, InternalServerError("503 boom"))
    print(f"标记后 cooldown 字典: {_MODEL_COOLDOWN}")
    print(f"标记后可用性: {_is_model_available(model_id)} (应为 False)")
    _MODEL_COOLDOWN[model_id] = 0  # 模拟超时
    print(f"超时后可用性: {_is_model_available(model_id)} (应为 True)")
    print("OK")


if __name__ == "__main__":
    main()
