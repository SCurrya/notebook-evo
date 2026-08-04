# -*- coding: utf-8 -*-
"""
一键演示模式 - 种子数据脚本。

创建一个演示笔记本，并上传 data/demo/ 下的示例 PDF，
让用户能立刻体验：混合检索、RAG 问答、知识图谱、内容生成。

用法:
    python scripts/seed_demo_data.py

依赖: 需要先启动 SurrealDB（端口 8000）。
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger


async def main(no_embed: bool = False) -> None:
    import socket

    from open_notebook.domain.notebook import Notebook

    # 0. 检测 API 是否可用（sources 处理依赖 API 服务）
    api_ready = False
    for port in (5055, 8000):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=2):
                if port == 5055:
                    api_ready = True
                break
        except OSError:
            continue
    if not api_ready:
        logger.warning(
            "检测到 API 服务未运行。请先启动 API（如运行 start-demo.bat 或 "
            "python run_api.py），来源上传与向量化需要 API 处理。"
        )

    # 1. 查找或创建演示笔记本
    demo_name = "AI 技术研究演示笔记本"
    notebooks = await Notebook.get_all()
    demo = next((n for n in notebooks if getattr(n, "name", "") == demo_name), None)
    if demo is None:
        demo = Notebook(
            name=demo_name,
            description="用于演示混合检索、RAG 问答与知识图谱的示例笔记本",
        )
        await demo.save()
        logger.info(f"创建演示笔记本: {demo.id} ({demo.name})")
    else:
        logger.info(f"复用已有演示笔记本: {demo.id}")

    # 2. 上传示例 PDF（通过 sources_service 处理分块 + 向量化）
    from open_notebook.config import UPLOADS_FOLDER

    demo_dir = Path(__file__).resolve().parent.parent / "data" / "demo"
    if not demo_dir.exists():
        logger.warning(f"演示数据目录不存在: {demo_dir}")
        return

    # 安全校验要求文件必须位于 uploads 目录内，先把示例 PDF 复制过去
    upload_dir = Path(UPLOADS_FOLDER)
    upload_dir.mkdir(parents=True, exist_ok=True)

    from api.sources_service import SourcesService

    service = SourcesService()
    existing = await demo.get_sources()
    existing_titles = {s.title for s in existing}

    added = 0
    for pdf in sorted(demo_dir.glob("*.pdf")):
        if pdf.stem in existing_titles:
            logger.info(f"跳过已存在的来源: {pdf.name}")
            continue
        # 复制到 uploads 目录（保持文件名，避免重复复制）
        target = upload_dir / pdf.name
        if not target.exists():
            import shutil

            shutil.copy2(pdf, target)
            logger.info(f"  复制到 uploads: {target}")
        logger.info(f"上传并处理来源: {pdf.name}")
        try:
            result = service.create_source(
                notebooks=[demo.id],
                source_type="upload",
                file_path=str(target),
                title=pdf.stem,
                transformations=[],
                embed=not no_embed,
            )
            if hasattr(result, "id"):
                logger.info(f"  来源 ID: {result.id}")
            else:
                logger.info(f"  来源处理: {result}")
            added += 1
        except Exception as e:
            logger.warning(f"  来源 {pdf.name} 处理失败: {e}")

    logger.info(f"演示数据就绪: 新增 {added} 个来源，笔记本共 {len(existing) + added} 个来源")
    logger.info("现在可以打开 Web UI 体验混合检索与 RAG 问答。")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="初始化演示数据")
    parser.add_argument(
        "--no-embed",
        action="store_true",
        help="跳过向量化（无 embedding 模型或外网时使用，来源记录仍会创建）",
    )
    args = parser.parse_args()
    asyncio.run(main(no_embed=args.no_embed))
