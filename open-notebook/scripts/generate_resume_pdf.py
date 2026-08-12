# -*- coding: utf-8 -*-
"""Generate a project showcase PDF for job applications.

Output: docs/project-showcase.pdf — a 2-3 page professional summary of
the Notebook-Evo project tailored for an AI / full-stack engineering
hiring manager.
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "project-showcase.pdf"
OUTPUT.parent.mkdir(exist_ok=True)

styles = getSampleStyleSheet()

styles.add(ParagraphStyle(
    name="H1", parent=styles["Heading1"], fontSize=22, spaceAfter=6,
    textColor=colors.HexColor("#4f46e5"), fontName="Helvetica-Bold",
))
styles.add(ParagraphStyle(
    name="H2", parent=styles["Heading2"], fontSize=14, spaceBefore=10,
    spaceAfter=4, textColor=colors.HexColor("#1e293b"),
    fontName="Helvetica-Bold",
))
styles.add(ParagraphStyle(
    name="Body", parent=styles["BodyText"], fontSize=9.5,
    spaceAfter=4, leading=13, textColor=colors.HexColor("#334155"),
))
styles.add(ParagraphStyle(
    name="BulletStyle", parent=styles["BodyText"], fontSize=9.5, leading=13,
    leftIndent=14, bulletIndent=4, spaceAfter=2,
    textColor=colors.HexColor("#334155"),
))
styles.add(ParagraphStyle(
    name="Subtle", parent=styles["BodyText"], fontSize=8.5,
    textColor=colors.HexColor("#64748b"), leading=11,
))


def p(text, style="Body"):
    return Paragraph(text, styles[style])


def bullet(text):
    return Paragraph(f"• {text}", styles["BulletStyle"])


tech_table = Table(
    [
        ["Backend", "Python 3.12 · FastAPI · LangGraph · SurrealDB · Esperanto"],
        ["Frontend", "Next.js 16 · React 19 · Tailwind · shadcn/ui · 14 langs i18n"],
        ["Retrieval", "BM25 (jieba for CJK) · Vector · RRF · Rerank · HyDE"],
        ["AI Orchestration", "LangGraph state · Multi-agent persistence · MCP Server"],
        ["Deployment", "Docker Compose · Windows one-click · Daily auto-backup"],
        ["Testing", "360+ pytest · Frontend lint · CI lint+test"],
    ],
    colWidths=[3 * cm, 14 * cm],
)
tech_table.setStyle(TableStyle([
    ("FONT", (0, 0), (-1, -1), "Helvetica", 9.5),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2ff")),
    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#4f46e5")),
    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
]))

bug_table = Table(
    [
        [
            p("Bug: Source Chat cannot see the source body<br/>"
              "Root cause: ContextBuilder.build() ignored context_config.sources "
              "and always used inclusion_level='insights', so full_text was "
              "never sent to the LLM<br/>"
              "Fix: build() reads cfg_sources + source_chat.py explicitly passes "
              "'full content'"),
            p("Context grew from 43 tokens to 2305 tokens; source chat now "
              "actually reads the document"),
        ],
        [
            p("Bug: Every share link was broken<br/>"
              "Root cause: 'token' is a SurrealDB protected variable; using it "
              "as a query parameter raised 'Protected variable name'<br/>"
              "Fix: query parameter renamed to $share_token"),
            p("ShareLink.get_by_token returns the link, share feature restored"),
        ],
        [
            p("Bug: source_count always 0 / search never filtered by notebook<br/>"
              "Root cause: source->reference->notebook relations had inverted "
              "in/out in every SQL query<br/>"
              "Fix: notebooks.py and sources.py queries use the correct direction"),
            p("source_count correct; search filters by notebook; shared notebook "
              "renders all sources"),
        ],
        [
            p("Bug: Async commands (embed_note etc.) always 'Command not found'<br/>"
              "Root cause: under uvicorn reload, the request-handling subprocess "
              "had an empty command registry<br/>"
              "Fix: api/main.py imports commands modules at startup"),
            p("registered 10 commands; note/source embeddings actually run"),
        ],
        [
            p("Bug: SenseNova API returned 403 for every request<br/>"
              "Root cause: wrong endpoint (api.sensenova.cn all forbidden)<br/>"
              "Fix: SENSENOVA_BASE_URL set to https://token.sensenova.cn/v1"),
            p("deepseek-v4-flash verified working; default chat model resolved"),
        ],
    ],
    colWidths=[11 * cm, 6 * cm],
)
bug_table.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("TOPPADDING", (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#fef2f2")),
    ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#ecfdf5")),
    ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
]))

story = [
    p("Notebook-Evo · Project Showcase", "H1"),
    p("AI Knowledge Workspace · Privacy-first · Multi-model · Self-hostable",
      "Subtle"),
    Spacer(1, 4),
    p("For AI / Full-stack engineering roles | 2026-08", "Subtle"),
    Spacer(1, 10),

    p("Project Summary", "H2"),
    p(
        "A deep enhancement of <b>Open Notebook</b> (MIT). Users upload research "
        "materials, then ask questions against a <b>hybrid retrieval + knowledge "
        "graph + GraphRAG</b> stack, generate reports, and orchestrate multi-agent "
        "workflows. The system supports <b>phone / desktop / tablet</b> real-time "
        "sync (WebSocket + SurrealDB LIVE query), is fully local, and has zero "
        "external service dependency."
    ),
    Spacer(1, 6),

    p("Tech Stack", "H2"),
    tech_table,
    Spacer(1, 6),

    p("Key Capabilities (12 major enhancements)", "H2"),
    bullet("Hybrid retrieval: BM25 (jieba + rank_bm25 fallback for CJK) + "
           "vector recall + RRF fusion + Rerank"),
    bullet("Knowledge graph + GraphRAG: per-notebook entity/relation extraction, "
           "visualization, graph-enhanced QA"),
    bullet("RAG evaluation centre: RAGAS four metrics (Faithfulness / Relevancy "
           "/ Precision / Recall) auto-evaluated"),
    bullet("Multi-agent orchestration: LangGraph state machines persisted across "
           "restarts, task DAG dependencies"),
    bullet("MCP Server: knowledge-base capabilities exposed as standard MCP "
           "tools, callable from Claude / Cursor"),
    bullet("Cross-provider model fallback: xcode.best → SenseNova → OpenRouter, "
           "priority configurable"),
    bullet("Security engineering: SSRF / DNS-rebinding protection, SurrealQL "
           "injection hardening, Jinja2 template-injection fix"),
    bullet("Authentication: constant-time password compare (secrets.compare_digest) "
           "+ Swagger protection + public tunnel access control"),
    bullet("Engineering quality: 360+ unit tests, CI lint+test, Docker one-click "
           "deploy, Windows one-click demo scripts"),
    bullet("Operations automation: daily auto-backup (scheduled task), health-check "
           "auto-restart, Tailscale private network"),
    bullet("Mobile PWA: localized manifest + PNG icons + drawer-style navigation "
           "+ share-by-QR for notebooks"),
    bullet("14-language i18n: zh-CN / en-US / ja-JP / ko-KR / fr-FR / de-DE etc."),
    Spacer(1, 6),

    p("Independent bug fixes (selected)", "H2"),
    bug_table,
    Spacer(1, 6),

    p("Engineering Highlights", "H2"),
    bullet("Git hygiene: clean commit graph (feat / fix / perf / docs labels), "
           "README / CHANGELOG / CONTRIBUTING / SECURITY all present"),
    bullet("CI pipeline: lint + 360+ unit tests, all green"),
    bullet("Config-as-docs: .env.example has comments for every key; "
           "MODEL_PROVIDER_PRIORITY lets users adjust model fallback by "
           "changing one line"),
    bullet("Observability: /api/system/status returns DB connection state, "
           "worker running, model count, db_stats in real time"),
    bullet("Developer experience: health-check.ps1 auto-restarts services, "
           "demo-mode.ps1 one-click demo, get-tunnel-url.ps1 surfaces the "
           "public tunnel URL"),
    Spacer(1, 6),

    p("Demo and Source", "H2"),
    bullet("GitHub: https://github.com/SCurrya/notebook-evo"),
    bullet("README + architecture diagram + API docs + deployment guide + "
           "CHANGELOG are all in place"),
    bullet("Public demo (Cloudflare tunnel): see the latest URL in the README"),
    bullet("Demo video (phone screen capture): link will be added to README shortly"),
    Spacer(1, 6),

    p("Beyond Code", "H2"),
    bullet("Security hygiene: .env in .gitignore, GitHub Push Protection caught a "
           "hardcoded OpenRouter key, all credentials read from .env"),
    bullet("Engineering discipline: each commit is an independently workable "
           "snapshot; local HEAD verified equal to remote HEAD via ls-remote"),
    bullet("Practical debugging: Stop-Process leaves zombie sockets that "
           "cannot be killed; workaround was switching to a different port and "
           "recommending a full restart"),
    bullet("User-first: turning 'I think it works' into 'users actually like it' "
           "(drawer mobile nav, share QR codes, persistent search history)"),
]


def draw_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#94a3b8"))
    canvas.drawString(2 * cm, 1 * cm, "Notebook-Evo · Project Showcase")
    canvas.drawRightString(A4[0] - 2 * cm, 1 * cm, f"Page {doc.page}")
    canvas.restoreState()


def draw_header(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#cbd5e1"))
    canvas.setLineWidth(0.5)
    canvas.line(2 * cm, A4[1] - 1.6 * cm, A4[0] - 2 * cm, A4[1] - 1.6 * cm)
    canvas.restoreState()


doc = BaseDocTemplate(
    str(OUTPUT), pagesize=A4,
    leftMargin=2 * cm, rightMargin=2 * cm,
    topMargin=2 * cm, bottomMargin=2 * cm,
)
frame = Frame(
    doc.leftMargin, doc.bottomMargin,
    doc.width, doc.height,
    id="normal",
)
doc.addPageTemplates([
    PageTemplate(id="main", frames=frame, onPage=draw_header, onPageEnd=draw_footer)
])
doc.build(story)
print(f"PDF written: {OUTPUT}")