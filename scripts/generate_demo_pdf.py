# -*- coding: utf-8 -*-
"""Generate a Chinese demo PDF for RAG testing (AI Agent topic)."""

import os
import sys
from pathlib import Path

# Allow running from repo root or scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

OUT_DIR = Path(__file__).resolve().parent.parent / "open-notebook" / "data" / "demo"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/msyh.ttc"),   # Microsoft YaHei
    Path("C:/Windows/Fonts/simhei.ttf"), # SimHei
    Path("C:/Windows/Fonts/simsun.ttc"), # SimSun
]

def load_font():
    for p in FONT_CANDIDATES:
        if p.exists():
            return str(p)
    raise RuntimeError("No CJK font found on this system")

def main():
    font_path = load_font()
    pdfmetrics.registerFont(TTFont("CJK", font_path, subfontIndex=0))

    title_style = ParagraphStyle("Title", fontName="CJK", fontSize=20, leading=28, spaceAfter=12)
    h_style = ParagraphStyle("H", fontName="CJK", fontSize=15, leading=22, spaceBefore=14, spaceAfter=8)
    body_style = ParagraphStyle("Body", fontName="CJK", fontSize=11, leading=18, alignment=4)

    sections = [
        ("《AI Agent 技术综述：从大模型到智能体应用》", title_style, True),
        ("一、什么是 AI Agent", h_style, True),
        ("AI Agent（人工智能智能体）是能够自主感知环境、做出决策并执行行动以完成特定目标的人工智能系统。与传统的单一问答模型不同，Agent 具备目标导向性、自主性和工具调用能力，能够将复杂任务分解为多个子步骤，并动态调用外部工具（如搜索引擎、代码执行器、API 接口）来完成任务。", body_style, True),
        ("2026 年，随着大模型基础能力趋于同质化，全球 AI 产业的重心已从参数规模竞赛全面转向 Agent 工程化落地。衡量 AI 价值的标尺不再是基准测试分数，而是其在真实业务流中自主规划、工具调用及闭环执行的成功率。", body_style, True),
        ("二、Agent 的核心能力", h_style, True),
        ("1. 任务规划（Planning）：Agent 需要将复杂目标拆解为可执行的子任务序列，并根据中间结果动态调整计划。常见的规划方式包括链式推理（Chain-of-Thought）和树状搜索（Tree-of-Thought）。", body_style, True),
        ("2. 工具调用（Tool Use）：通过函数调用（Function Calling）或模型上下文协议（MCP），Agent 可以调用外部工具获取实时信息。MCP（Model Context Protocol）由 Anthropic 于 2024 年底提出，2026 年已成为智能体与外部系统交互的事实标准。", body_style, True),
        ("3. 记忆管理（Memory）：Agent 需要短期记忆（对话上下文）和长期记忆（向量数据库、知识图谱）来维持多轮任务的一致性。RAG（检索增强生成）技术是长期记忆的关键实现。", body_style, True),
        ("4. 自我反思（Self-Reflection）：高级 Agent 会评估自身输出质量，识别错误并自动修正。反思-规划-执行（Reflect-Plan-Execute）循环是提升 Agent 可靠性的重要范式。", body_style, True),
        ("三、多智能体协作", h_style, True),
        ("多智能体系统（Multi-Agent System）通过多个各司其职的 Agent 协作完成复杂任务，例如：规划 Agent 负责任务分解、执行 Agent 负责具体操作、审查 Agent 负责质量把关。Agent 之间通过消息队列或 A2A（Agent-to-Agent）协议通信。", body_style, True),
        ("四、RAG 技术要点", h_style, True),
        ("RAG（Retrieval-Augmented Generation，检索增强生成）通过从外部知识库检索相关文档来增强大模型的回答质量。2026 年的高级 RAG 架构通常包含：混合检索（BM25 关键词检索 + 向量语义检索双路召回）、重排序（Rerank，使用 Cross-Encoder 对候选文档精排）、以及 RAG 评估（RAGAS 框架中的忠实度、答案相关性、上下文精确度、召回率等指标）。", body_style, True),
        ("GraphRAG 则将知识图谱与 RAG 结合，先抽取文档中的实体和关系构建图谱，再通过图谱路径检索辅助推理，特别适合多跳问题（Multi-hop Question）和跨文档推理场景。", body_style, True),
        ("五、AI 智能体应用场景", h_style, True),
        ("1. 智能客服：自动理解用户问题，检索企业知识库，生成准确回复并转接人工。", body_style, True),
        ("2. 代码助手：理解代码仓库上下文，自动生成、修复和重构代码。", body_style, True),
        ("3. 数据分析：连接数据库，根据自然语言查询生成 SQL 并解释结果。", body_style, True),
        ("4. 自动化工作流：如智能体自动完成市场调研、报告撰写、竞品分析等知识工作。", body_style, True),
        ("六、总结与展望", h_style, True),
        ("AI Agent 正从实验室走向产业落地。对于开发者而言，掌握 RAG 检索优化、MCP 工具集成、多智能体编排、RAG 质量评估等工程能力，将成为 AI 时代最核心的竞争力。未来，随着 Agent 通信协议（MCP、A2A）的成熟，跨系统、跨生态的智能体协作将成为常态。", body_style, True),
    ]

    out_path = OUT_DIR / "ai-agent-tech-review.pdf"
    doc = SimpleDocTemplate(str(out_path), pagesize=A4,
                            leftMargin=2.5 * cm, rightMargin=2.5 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm)
    story = []
    for text, style, _ in sections:
        story.append(Paragraph(text, style))
        story.append(Spacer(1, 6))
    doc.build(story)
    print(f"OK: {out_path} ({out_path.stat().st_size / 1024:.0f} KB)")

if __name__ == "__main__":
    main()
