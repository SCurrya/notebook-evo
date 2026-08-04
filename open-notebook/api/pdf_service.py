"""
PDF generation service using reportlab.

Generates PDF documents directly via reportlab's platypus framework
(no browser printing required). Supports multiple built-in templates,
Markdown parsing, Chinese fonts, and asynchronous task tracking.

Templates:
    - report  : 正式商务报告（封面、目录、页眉页脚）
    - article : 学术文章（可选双栏）
    - resume  : 简历（简洁单栏）
    - letter  : 正式信函
    - ebook   : 电子书（章节式，适合长文）

Output directory: outputs/pdf/
"""

import asyncio
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger
from pydantic import BaseModel, Field

# reportlab 导入：使用 platypus 框架构建文档流
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.styles import ListStyle, ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    ListFlowable,
    ListItem,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# === 输出目录配置 ===
PROJECT_ROOT = Path(__file__).parent.parent
PDF_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "pdf"


# === 中文字体注册 ===
# Windows 常见中文字体路径，按优先级尝试注册
_CHINESE_FONT_CANDIDATES = [
    # Windows
    ("SimSun", r"C:\Windows\Fonts\simsun.ttc"),
    ("MicrosoftYaHei", r"C:\Windows\Fonts\msyh.ttc"),
    ("MicrosoftYaHei", r"C:\Windows\Fonts\msyh.ttf"),
    ("SimHei", r"C:\Windows\Fonts\simhei.ttf"),
    # Linux (需要用户安装)
    ("SimSun", "/usr/share/fonts/truetype/simsun.ttc"),
    ("WenQuanYi", "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
    # macOS
    ("PingFang", "/System/Library/Fonts/PingFang.ttc"),
]

# 已注册的中文字体名称（None 表示未注册）
_REGISTERED_CJK_FONT: Optional[str] = None


def _register_chinese_font() -> Optional[str]:
    """尝试注册中文字体，返回注册成功的字体名称。

    遍历候选字体路径，注册第一个可用的中文字体。
    若系统无中文字体，返回 None（PDF 仍可生成，但中文可能显示为方块）。
    """
    global _REGISTERED_CJK_FONT
    if _REGISTERED_CJK_FONT is not None:
        return _REGISTERED_CJK_FONT

    for font_name, font_path in _CHINESE_FONT_CANDIDATES:
        try:
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                _REGISTERED_CJK_FONT = font_name
                logger.info(f"Registered CJK font: {font_name} from {font_path}")
                return _REGISTERED_CJK_FONT
        except Exception as e:
            # 注册失败时记录调试信息，继续尝试下一个候选
            logger.debug(f"Failed to register font {font_name} at {font_path}: {e}")
            continue

    logger.warning(
        "No CJK font registered. Chinese characters may not render correctly."
    )
    return None


def _get_body_font() -> str:
    """获取正文字体名称（优先使用中文字体）。"""
    cjk = _register_chinese_font()
    return cjk if cjk else "Helvetica"


def _get_heading_font() -> str:
    """获取标题字体名称（优先使用中文字体，否则用 Helvetica-Bold）。"""
    cjk = _register_chinese_font()
    return cjk if cjk else "Helvetica-Bold"


# === Pydantic 模型 ===
class PDFTemplate(BaseModel):
    """PDF 模板描述。"""

    id: str = Field(..., description="模板唯一标识，如 'report'")
    name: str = Field(..., description="模板显示名称")
    description: str = Field(..., description="模板用途说明")
    page_size: str = Field(default="A4", description="页面尺寸：A4 或 LETTER")
    two_column: bool = Field(default=False, description="是否双栏排版")
    has_cover: bool = Field(default=False, description="是否生成封面页")
    has_toc: bool = Field(default=False, description="是否生成目录")
    has_header_footer: bool = Field(
        default=True, description="是否包含页眉页脚"
    )


class PDFGenerationRequest(BaseModel):
    """PDF 生成请求。"""

    template: str = Field(..., description="模板 ID：report/article/resume/letter/ebook")
    title: str = Field(..., min_length=1, description="文档标题")
    author: str = Field(default="", description="作者")
    date: str = Field(default="", description="日期字符串，如 '2026-06-21'")
    company: str = Field(default="", description="公司名称（用于报告/信函）")
    logo_url: Optional[str] = Field(default=None, description="Logo 图片 URL（暂未实现）")
    content: str = Field(..., min_length=1, description="Markdown 格式正文")
    two_column: bool = Field(default=False, description="是否双栏（仅 article 模板）")


class PDFTaskResponse(BaseModel):
    """PDF 生成任务提交响应。"""

    task_id: str
    status: str = "pending"
    message: str = ""


class PDFTaskStatus(BaseModel):
    """PDF 任务状态详情。"""

    id: str
    state: str = "pending"
    progress: int = 0
    message: str = ""
    template: str = ""
    title: str = ""
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    error: Optional[str] = None


class PDFTaskListResponse(BaseModel):
    """PDF 任务列表（分页）。"""

    items: List[PDFTaskStatus]
    total: int
    page: int
    page_size: int


# === 模板定义 ===
# 每种模板的样式配置：字体、间距、配色、页眉页脚等
TEMPLATES: Dict[str, PDFTemplate] = {
    "report": PDFTemplate(
        id="report",
        name="Report (报告)",
        description="正式商务风格，包含封面、目录、页眉页脚，适合商业报告与白皮书。",
        page_size="A4",
        two_column=False,
        has_cover=True,
        has_toc=True,
        has_header_footer=True,
    ),
    "article": PDFTemplate(
        id="article",
        name="Article (文章)",
        description="学术风格，支持双栏排版，适合论文与技术文章。",
        page_size="A4",
        two_column=True,
        has_cover=False,
        has_toc=False,
        has_header_footer=True,
    ),
    "resume": PDFTemplate(
        id="resume",
        name="Resume (简历)",
        description="简洁单栏，适合个人简历与求职材料。",
        page_size="A4",
        two_column=False,
        has_cover=False,
        has_toc=False,
        has_header_footer=False,
    ),
    "letter": PDFTemplate(
        id="letter",
        name="Letter (信函)",
        description="正式信函格式，包含发件人/收件人区块与签名区。",
        page_size="LETTER",
        two_column=False,
        has_cover=False,
        has_toc=False,
        has_header_footer=False,
    ),
    "ebook": PDFTemplate(
        id="ebook",
        name="Ebook (电子书)",
        description="章节式排版，适合长文阅读，每章另起一页。",
        page_size="A4",
        two_column=False,
        has_cover=True,
        has_toc=True,
        has_header_footer=True,
    ),
}


# === Markdown 解析 ===
def _escape_xml(text: str) -> str:
    """转义 XML 特殊字符，保留 reportlab 的内联标记。

    reportlab Paragraph 使用类 XML 语法，需要转义 & < >，
    但保留我们后续注入的 <b>/<i> 标签。
    """
    # 先转义所有特殊字符
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text


def _parse_inline_markdown(text: str) -> str:
    """解析行内 Markdown 标记：**bold**, *italic*, `code`。

    转义 XML 后再将标记转换为 reportlab 的 <b>/<i>/<font> 标签。
    """
    # 先转义 XML 特殊字符
    escaped = _escape_xml(text)

    # **bold** -> <b>bold</b>
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    # *italic* -> <i>italic</i>（避免与 ** 冲突，先处理 **）
    escaped = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", escaped)
    # `code` -> <font name="Courier">code</font>
    escaped = re.sub(r"`(.+?)`", r'<font name="Courier">\1</font>', escaped)
    return escaped


def _parse_markdown_to_flowables(
    content: str, styles: Dict[str, ParagraphStyle]
) -> List[Any]:
    """将 Markdown 内容解析为 reportlab Flowable 列表。

    支持的语法：
        ## 标题  -> H2 段落
        ### 子标题 -> H3 段落
        - 项目  -> 列表项
        1. 有序列表 -> 列表项
        普通段落 -> 正文段落
        ---     -> 分隔符（Spacer）

    返回 Flowable 列表，可直接传入 SimpleDocTemplate.build()。
    """
    flowables: List[Any] = []
    lines = content.split("\n")
    i = 0

    # 收集列表项的缓冲区
    list_items_buffer: List[str] = []
    list_ordered = False

    # ListFlowable 需要 ListStyle（而非 ParagraphStyle）
    _list_style = ListStyle(
        name="MarkdownList",
        leftIndent=18,
        bulletIndent=6,
        spaceBefore=2,
        spaceAfter=2,
    )

    def flush_list() -> None:
        """将缓冲的列表项转为 ListFlowable 并加入 flowables。"""
        nonlocal list_items_buffer, list_ordered
        if not list_items_buffer:
            return
        items = [
            ListItem(Paragraph(_parse_inline_markdown(item), styles["BodyText"]))
            for item in list_items_buffer
        ]
        flowables.append(
            ListFlowable(
                items,
                bulletType="1" if list_ordered else "bullet",
                start="1" if list_ordered else None,
                leftIndent=18,
                style=_list_style,
            )
        )
        list_items_buffer = []
        list_ordered = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 空行：刷新列表缓冲
        if not stripped:
            flush_list()
            i += 1
            continue

        # 分隔线 ---
        if stripped in ("---", "***", "___"):
            flush_list()
            flowables.append(Spacer(1, 6 * mm))
            i += 1
            continue

        # H1/H2/H3 标题
        if stripped.startswith("### "):
            flush_list()
            heading_text = _parse_inline_markdown(stripped[4:])
            flowables.append(Paragraph(heading_text, styles["Heading3"]))
            i += 1
            continue
        if stripped.startswith("## "):
            flush_list()
            heading_text = _parse_inline_markdown(stripped[3:])
            flowables.append(Paragraph(heading_text, styles["Heading2"]))
            i += 1
            continue
        if stripped.startswith("# "):
            flush_list()
            heading_text = _parse_inline_markdown(stripped[2:])
            flowables.append(Paragraph(heading_text, styles["Heading1"]))
            i += 1
            continue

        # 有序列表 1. / 2. 等
        ordered_match = re.match(r"^(\d+)\.\s+(.+)", stripped)
        if ordered_match:
            if not list_items_buffer or not list_ordered:
                flush_list()
                list_ordered = True
            list_items_buffer.append(ordered_match.group(2))
            i += 1
            continue

        # 无序列表 - / * / +
        bullet_match = re.match(r"^[-*+]\s+(.+)", stripped)
        if bullet_match:
            if list_items_buffer and list_ordered:
                flush_list()
                list_ordered = False
            elif not list_items_buffer:
                list_ordered = False
            list_items_buffer.append(bullet_match.group(1))
            i += 1
            continue

        # 引用块 >
        if stripped.startswith("> "):
            flush_list()
            quote_text = _parse_inline_markdown(stripped[2:])
            flowables.append(Paragraph(quote_text, styles["Quote"]))
            i += 1
            continue

        # 普通段落
        flush_list()
        para_text = _parse_inline_markdown(stripped)
        flowables.append(Paragraph(para_text, styles["BodyText"]))
        i += 1

    # 刷新剩余列表
    flush_list()
    return flowables


# === 样式构建 ===
def _build_styles(
    template_id: str, title: str, author: str
) -> Dict[str, ParagraphStyle]:
    """根据模板构建段落样式集合。

    不同模板有不同的字体、间距、配色。
    """
    body_font = _get_body_font()
    heading_font = _get_heading_font()

    # 基础样式表
    base = getSampleStyleSheet()

    # 通用正文样式
    body = ParagraphStyle(
        "BodyText",
        parent=base["BodyText"],
        fontName=body_font,
        fontSize=10.5,
        leading=16,
        alignment=TA_JUSTIFY,
        spaceAfter=6,
        textColor=colors.HexColor("#1f2937"),
    )

    # 标题样式
    h1 = ParagraphStyle(
        "Heading1",
        parent=base["Heading1"],
        fontName=heading_font,
        fontSize=20,
        leading=26,
        spaceBefore=12,
        spaceAfter=12,
        textColor=colors.HexColor("#111827"),
    )
    h2 = ParagraphStyle(
        "Heading2",
        parent=base["Heading2"],
        fontName=heading_font,
        fontSize=15,
        leading=20,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor("#1f2937"),
    )
    h3 = ParagraphStyle(
        "Heading3",
        parent=base["Heading3"],
        fontName=heading_font,
        fontSize=12,
        leading=16,
        spaceBefore=8,
        spaceAfter=4,
        textColor=colors.HexColor("#374151"),
    )

    # 引用样式
    quote = ParagraphStyle(
        "Quote",
        parent=body,
        leftIndent=20,
        rightIndent=10,
        fontName=body_font,
        fontSize=10,
        textColor=colors.HexColor("#6b7280"),
        borderColor=colors.HexColor("#d1d5db"),
        borderWidth=0,
        spaceBefore=6,
        spaceAfter=6,
    )

    styles: Dict[str, ParagraphStyle] = {
        "BodyText": body,
        "Heading1": h1,
        "Heading2": h2,
        "Heading3": h3,
        "Quote": quote,
    }

    # === 模板特定样式调整 ===
    if template_id == "report":
        # 报告：更正式，行距更宽
        styles["BodyText"].fontSize = 11
        styles["BodyText"].leading = 18
        styles["CoverTitle"] = ParagraphStyle(
            "CoverTitle",
            fontName=heading_font,
            fontSize=28,
            leading=36,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=20,
        )
        styles["CoverSubtitle"] = ParagraphStyle(
            "CoverSubtitle",
            fontName=body_font,
            fontSize=14,
            leading=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#475569"),
            spaceAfter=12,
        )
    elif template_id == "article":
        # 文章：紧凑学术风
        styles["BodyText"].fontSize = 10
        styles["BodyText"].leading = 14
        styles["Heading1"].fontSize = 18
        styles["Heading2"].fontSize = 14
    elif template_id == "resume":
        # 简历：紧凑
        styles["BodyText"].fontSize = 10
        styles["BodyText"].leading = 14
        styles["BodyText"].spaceAfter = 4
        styles["Heading2"].fontSize = 13
        styles["Heading2"].textColor = colors.HexColor("#0f172a")
        styles["Heading2"].spaceBefore = 10
        styles["Heading2"].spaceAfter = 4
    elif template_id == "letter":
        # 信函：正式
        styles["BodyText"].fontSize = 11
        styles["BodyText"].leading = 17
        styles["BodyText"].alignment = TA_LEFT
        styles["BodyText"].spaceAfter = 10
    elif template_id == "ebook":
        # 电子书：阅读舒适
        styles["BodyText"].fontSize = 11
        styles["BodyText"].leading = 18
        styles["Heading1"].fontSize = 22
        styles["Heading1"].alignment = TA_CENTER
        styles["Heading1"].spaceBefore = 24
        styles["Heading2"].fontSize = 16

    return styles


# === 页眉页脚回调 ===
def _make_header_footer(
    template_id: str, title: str, author: str, company: str
):
    """创建页眉页脚绘制回调函数。

    返回一个符合 reportlab onPage 签名的函数：
    def(canvas, doc) -> None
    """

    def draw_header_footer(canvas, doc) -> None:
        canvas.saveState()
        body_font = _get_body_font()
        page_num = canvas.getPageNumber()

        if template_id == "report":
            # 报告：顶部标题，底部页码与公司
            canvas.setFont(body_font, 9)
            canvas.setFillColor(colors.HexColor("#6b7280"))
            if title:
                canvas.drawString(
                    2 * cm, A4[1] - 1.2 * cm, title[:60]
                )
            canvas.line(
                2 * cm, A4[1] - 1.4 * cm, A4[0] - 2 * cm, A4[1] - 1.4 * cm
            )
            # 页脚
            canvas.line(2 * cm, 1.5 * cm, A4[0] - 2 * cm, 1.5 * cm)
            footer_left = company if company else author
            if footer_left:
                canvas.drawString(2 * cm, 1.1 * cm, footer_left[:40])
            canvas.drawRightString(
                A4[0] - 2 * cm, 1.1 * cm, f"Page {page_num}"
            )
        elif template_id == "article":
            # 文章：简洁页脚
            canvas.setFont(body_font, 9)
            canvas.setFillColor(colors.HexColor("#6b7280"))
            canvas.drawCentredString(A4[0] / 2, 1.2 * cm, f"— {page_num} —")
        elif template_id == "ebook":
            # 电子书：页眉书名，页脚页码
            canvas.setFont(body_font, 9)
            canvas.setFillColor(colors.HexColor("#6b7280"))
            if title:
                canvas.drawCentredString(A4[0] / 2, A4[1] - 1.2 * cm, title[:50])
            canvas.drawCentredString(A4[0] / 2, 1.2 * cm, f"{page_num}")
        # resume / letter: 无页眉页脚

        canvas.restoreState()

    return draw_header_footer


# === 封面构建 ===
def _build_cover(
    template_id: str,
    title: str,
    author: str,
    date: str,
    company: str,
    styles: Dict[str, ParagraphStyle],
) -> List[Any]:
    """构建封面页 Flowable 列表。"""
    flowables: List[Any] = []
    # 顶部留白
    flowables.append(Spacer(1, 6 * cm))

    cover_title_style = styles.get(
        "CoverTitle", styles["Heading1"]
    )
    cover_subtitle_style = styles.get(
        "CoverSubtitle", styles["BodyText"]
    )

    flowables.append(Paragraph(_escape_xml(title), cover_title_style))

    if author:
        flowables.append(
            Paragraph(f"by {_escape_xml(author)}", cover_subtitle_style)
        )
    if company:
        flowables.append(
            Paragraph(_escape_xml(company), cover_subtitle_style)
        )
    if date:
        flowables.append(Spacer(1, 2 * cm))
        flowables.append(
            Paragraph(_escape_xml(date), cover_subtitle_style)
        )

    flowables.append(PageBreak())
    return flowables


# === 目录构建（简化版） ===
def _build_toc(
    content: str, styles: Dict[str, ParagraphStyle]
) -> List[Any]:
    """从 Markdown 内容提取 ## 标题构建简化目录。

    注意：此处为静态目录（无页码），如需带页码的目录需要
    使用 reportlab 的 TableOfContents 与多遍构建，此处保持简洁。
    """
    flowables: List[Any] = []
    flowables.append(Paragraph("Table of Contents", styles["Heading1"]))
    flowables.append(Spacer(1, 6 * mm))

    toc_style = ParagraphStyle(
        "TOCEntry",
        parent=styles["BodyText"],
        fontSize=11,
        leading=18,
        leftIndent=10,
    )

    lines = content.split("\n")
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            heading = _parse_inline_markdown(stripped[3:])
            flowables.append(Paragraph(heading, toc_style))
        elif stripped.startswith("### "):
            heading = _parse_inline_markdown(stripped[4:])
            sub_style = ParagraphStyle(
                "TOCSubEntry",
                parent=toc_style,
                leftIndent=25,
                fontSize=10,
                textColor=colors.HexColor("#6b7280"),
            )
            flowables.append(Paragraph(heading, sub_style))

    flowables.append(PageBreak())
    return flowables


# === 信函头部构建 ===
def _build_letter_header(
    author: str, company: str, date: str, styles: Dict[str, ParagraphStyle]
) -> List[Any]:
    """构建信函头部（发件人信息块）。"""
    flowables: List[Any] = []
    header_lines: List[str] = []
    if author:
        header_lines.append(author)
    if company:
        header_lines.append(company)
    if date:
        header_lines.append(date)

    if header_lines:
        header_text = "<br/>".join(_escape_xml(l) for l in header_lines)
        flowables.append(Paragraph(header_text, styles["BodyText"]))
        flowables.append(Spacer(1, 8 * mm))
    return flowables


# === PDF 生成核心 ===
def _generate_pdf_sync(
    request: PDFGenerationRequest, output_path: Path
) -> None:
    """同步生成 PDF 文件（在 worker 线程中执行）。

    根据模板配置构建 SimpleDocTemplate/BaseDocTemplate，解析 Markdown，
    组装 Flowable 列表并构建 PDF。
    """
    template = TEMPLATES.get(request.template)
    if template is None:
        raise ValueError(f"Unknown template: {request.template}")

    # 确保中文字体已注册
    _register_chinese_font()

    # 页面尺寸
    page_size = A4 if template.page_size == "A4" else LETTER

    # 构建样式
    styles = _build_styles(request.template, request.title, request.author)

    # 构建 Flowable 列表
    story: List[Any] = []

    # 封面
    if template.has_cover:
        story.extend(
            _build_cover(
                request.template,
                request.title,
                request.author,
                request.date,
                request.company,
                styles,
            )
        )

    # 目录
    if template.has_toc:
        story.extend(_build_toc(request.content, styles))

    # 信函头部
    if request.template == "letter":
        story.extend(
            _build_letter_header(
                request.author, request.company, request.date, styles
            )
        )

    # 简历头部：标题为姓名
    if request.template == "resume" and request.title:
        story.append(Paragraph(_escape_xml(request.title), styles["Heading1"]))
        if request.author:
            contact_style = ParagraphStyle(
                "ResumeContact",
                parent=styles["BodyText"],
                fontSize=10,
                textColor=colors.HexColor("#6b7280"),
                spaceAfter=10,
            )
            story.append(Paragraph(_escape_xml(request.author), contact_style))
        story.append(Spacer(1, 4 * mm))

    # 文章/电子书标题（无封面时在正文前显示）
    if not template.has_cover and request.template in ("article", "ebook"):
        story.append(Paragraph(_escape_xml(request.title), styles["Heading1"]))
        if request.author:
            author_style = ParagraphStyle(
                "ArticleAuthor",
                parent=styles["BodyText"],
                alignment=TA_CENTER,
                textColor=colors.HexColor("#6b7280"),
                spaceAfter=12,
            )
            story.append(Paragraph(f"by {_escape_xml(request.author)}", author_style))
        if request.date:
            date_style = ParagraphStyle(
                "ArticleDate",
                parent=styles["BodyText"],
                alignment=TA_CENTER,
                fontSize=9,
                textColor=colors.HexColor("#9ca3af"),
                spaceAfter=12,
            )
            story.append(Paragraph(_escape_xml(request.date), date_style))
        story.append(Spacer(1, 6 * mm))

    # 解析 Markdown 正文
    body_flowables = _parse_markdown_to_flowables(request.content, styles)
    story.extend(body_flowables)

    # 信函签名区
    if request.template == "letter":
        story.append(Spacer(1, 12 * mm))
        story.append(Paragraph("Sincerely,", styles["BodyText"]))
        story.append(Spacer(1, 6 * mm))
        if request.author:
            story.append(Paragraph(_escape_xml(request.author), styles["BodyText"]))

    # === 构建文档 ===
    # 双栏模式使用 BaseDocTemplate + 双 Frame
    use_two_column = template.two_column and request.two_column

    # 页眉页脚回调（若模板启用）
    on_page = (
        _make_header_footer(
            request.template, request.title, request.author, request.company
        )
        if template.has_header_footer
        else None
    )

    if use_two_column:
        # 双栏：使用 BaseDocTemplate 自定义页面模板
        margin = 2 * cm
        gutter = 0.8 * cm
        col_width = (page_size[0] - 2 * margin - gutter) / 2
        col_height = page_size[1] - 2 * margin

        frame_left = Frame(
            margin, margin, col_width, col_height, id="col1"
        )
        frame_right = Frame(
            margin + col_width + gutter,
            margin,
            col_width,
            col_height,
            id="col2",
        )

        page_template = PageTemplate(
            id="two_col",
            frames=[frame_left, frame_right],
            onPage=on_page if on_page else (lambda c, d: None),
        )

        doc = BaseDocTemplate(
            str(output_path),
            pagesize=page_size,
            pageTemplates=[page_template],
            title=request.title,
            author=request.author,
        )
        # BaseDocTemplate 通过 PageTemplate.onPage 绘制页眉页脚
        doc.build(story)
    else:
        # 单栏：使用 SimpleDocTemplate
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=page_size,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2.5 * cm,
            bottomMargin=2 * cm,
            title=request.title,
            author=request.author,
        )
        # SimpleDocTemplate 通过 build 的 onFirstPage/onLaterPages 绘制页眉页脚
        if on_page:
            doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        else:
            doc.build(story)


# === 任务跟踪存储 ===
# 进程内任务存储（生产环境应替换为持久化存储）
_tasks: Dict[str, PDFTaskStatus] = {}


class PDFService:
    """PDF 生成服务，提供模板查询、任务提交、状态跟踪与文件管理。"""

    @staticmethod
    def list_templates() -> List[PDFTemplate]:
        """返回所有可用模板列表。"""
        return list(TEMPLATES.values())

    @staticmethod
    def get_template(template_id: str) -> Optional[PDFTemplate]:
        """根据 ID 获取模板。"""
        return TEMPLATES.get(template_id)

    @staticmethod
    def _ensure_output_dir() -> Path:
        """确保输出目录存在并返回路径。"""
        PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        return PDF_OUTPUT_DIR

    @staticmethod
    def list_tasks(
        page: int = 1, page_size: int = 20
    ) -> PDFTaskListResponse:
        """分页列出任务（按创建时间倒序）。"""
        all_items = sorted(
            _tasks.values(),
            key=lambda t: t.created_at or "",
            reverse=True,
        )
        total = len(all_items)
        start = (page - 1) * page_size
        end = start + page_size
        items = all_items[start:end]
        return PDFTaskListResponse(
            items=items, total=total, page=page, page_size=page_size
        )

    @staticmethod
    def get_task(task_id: str) -> Optional[PDFTaskStatus]:
        """获取单个任务状态。"""
        return _tasks.get(task_id)

    @staticmethod
    def delete_task(task_id: str) -> bool:
        """删除任务及其生成的 PDF 文件。"""
        task = _tasks.get(task_id)
        if task is None:
            return False
        # 删除文件
        if task.file_path:
            try:
                file_path = Path(task.file_path)
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Deleted PDF file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete PDF file for task {task_id}: {e}")
        # 删除任务记录
        _tasks.pop(task_id, None)
        logger.info(f"Deleted PDF task: {task_id}")
        return True

    @staticmethod
    async def submit_task(
        request: PDFGenerationRequest,
    ) -> PDFTaskResponse:
        """提交 PDF 生成任务。

        立即返回任务 ID，生成过程在后台线程异步执行。
        """
        # 校验模板
        if request.template not in TEMPLATES:
            raise ValueError(
                f"Unknown template: {request.template}. "
                f"Available: {list(TEMPLATES.keys())}"
            )

        task_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        # 创建任务记录
        task = PDFTaskStatus(
            id=task_id,
            state="pending",
            progress=0,
            message="Task queued",
            template=request.template,
            title=request.title,
            created_at=now,
            updated_at=now,
        )
        _tasks[task_id] = task

        logger.info(
            f"PDF task submitted: id={task_id} template={request.template} "
            f"title='{request.title}'"
        )

        # 启动后台生成
        asyncio.create_task(
            PDFService._run_generation(task_id, request)
        )

        return PDFTaskResponse(
            task_id=task_id,
            status="pending",
            message="PDF generation task submitted",
        )

    @staticmethod
    async def _run_generation(
        task_id: str, request: PDFGenerationRequest
    ) -> None:
        """后台执行 PDF 生成（在线程池中运行同步代码）。

        更新任务状态：pending -> processing -> completed / failed
        """
        task = _tasks.get(task_id)
        if task is None:
            logger.error(f"Task not found: {task_id}")
            return

        try:
            # 标记为处理中
            task.state = "processing"
            task.progress = 10
            task.message = "Generating PDF..."
            task.updated_at = datetime.now().isoformat()

            # 确保输出目录
            output_dir = PDFService._ensure_output_dir()
            # 文件名：task_id + 模板名 + .pdf
            safe_title = re.sub(r"[^\w\-]", "_", request.title)[:50]
            filename = f"{task_id}_{safe_title}.pdf"
            output_path = output_dir / filename

            # 在线程池中执行同步 PDF 生成
            await asyncio.to_thread(
                _generate_pdf_sync, request, output_path
            )

            # 更新为完成
            file_size = output_path.stat().st_size if output_path.exists() else 0
            task.state = "completed"
            task.progress = 100
            task.message = "PDF generated successfully"
            task.file_path = str(output_path)
            task.file_size = file_size
            task.updated_at = datetime.now().isoformat()

            logger.info(
                f"PDF task completed: id={task_id} file={output_path} "
                f"size={file_size} bytes"
            )
        except Exception as e:
            # 标记为失败
            task.state = "failed"
            task.progress = 0
            task.message = "Generation failed"
            task.error = str(e)
            task.updated_at = datetime.now().isoformat()
            logger.error(f"PDF task failed: id={task_id} error={e}")
            logger.exception(e)

    @staticmethod
    def get_task_file_path(task_id: str) -> Optional[Path]:
        """获取任务生成的 PDF 文件路径（用于下载）。"""
        task = _tasks.get(task_id)
        if task is None or not task.file_path:
            return None
        path = Path(task.file_path)
        return path if path.exists() else None
