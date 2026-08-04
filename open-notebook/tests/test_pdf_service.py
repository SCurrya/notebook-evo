"""
PDF 生成服务测试套件。

测试覆盖：
- 模板查询（list_templates / get_template）
- Markdown 解析（标题、列表、行内标记、转义）
- 每种模板的 PDF 生成（report/article/resume/letter/ebook）
- 双栏排版生成
- 中文字体注册
- 任务状态跟踪（提交、查询、列表、删除）
- 文件输出与大小

测试直接调用 PDFService 类的方法，不启动 FastAPI 服务。
生成的 PDF 文件输出到临时目录，测试后自动清理。
"""

import asyncio
from pathlib import Path
from typing import Iterator

import pytest

from api.pdf_service import (
    PDFGenerationRequest,
    PDFService,
    PDFTaskListResponse,
    PDFTaskResponse,
    PDFTaskStatus,
    PDFTemplate,
    TEMPLATES,
    _build_styles,
    _escape_xml,
    _get_body_font,
    _parse_inline_markdown,
    _parse_markdown_to_flowables,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_output_dir(tmp_path, monkeypatch) -> Iterator[Path]:
    """将 PDF 输出目录重定向到临时目录，测试后自动清理。"""
    import api.pdf_service as svc

    temp_dir = tmp_path / "pdf_output"
    temp_dir.mkdir()
    monkeypatch.setattr(svc, "PDF_OUTPUT_DIR", temp_dir)
    yield temp_dir
    # tmp_path 由 pytest 自动清理


@pytest.fixture
def clean_tasks(monkeypatch):
    """每个测试前清空任务存储，避免相互影响。"""
    import api.pdf_service as svc

    monkeypatch.setattr(svc, "_tasks", {})
    return svc._tasks


@pytest.fixture
def sample_markdown() -> str:
    """包含多种 Markdown 元素的示例内容。"""
    return """## Introduction

This is a **bold** and *italic* paragraph with `inline code`.

## Key Features

- Multiple templates
- Markdown parsing
- Chinese font support

## Steps

1. Choose template
2. Fill content
3. Generate PDF

### Subsection

> This is a blockquote.

Final paragraph.
"""


@pytest.fixture
def sample_request(sample_markdown) -> PDFGenerationRequest:
    """标准 PDF 生成请求。"""
    return PDFGenerationRequest(
        template="report",
        title="Test Report",
        author="Test Author",
        date="2026-06-21",
        company="Test Company",
        content=sample_markdown,
    )


# ============================================================================
# TEST SUITE 1: Template Management
# ============================================================================


class TestTemplateManagement:
    """模板查询功能测试。"""

    def test_list_templates_returns_all_five(self):
        """应返回全部 5 种模板。"""
        templates = PDFService.list_templates()
        assert len(templates) == 5
        template_ids = {t.id for t in templates}
        assert template_ids == {"report", "article", "resume", "letter", "ebook"}

    def test_list_templates_returns_pdftemplate_instances(self):
        """返回的应为 PDFTemplate 实例。"""
        templates = PDFService.list_templates()
        for tpl in templates:
            assert isinstance(tpl, PDFTemplate)
            assert tpl.name
            assert tpl.description
            assert tpl.page_size in ("A4", "LETTER")

    def test_get_template_existing(self):
        """应能根据 ID 获取已存在的模板。"""
        tpl = PDFService.get_template("report")
        assert tpl is not None
        assert tpl.id == "report"
        assert tpl.has_cover is True
        assert tpl.has_toc is True

    def test_get_template_nonexistent(self):
        """不存在的模板 ID 应返回 None。"""
        assert PDFService.get_template("nonexistent") is None

    def test_report_template_has_cover_and_toc(self):
        """报告模板应包含封面和目录。"""
        tpl = TEMPLATES["report"]
        assert tpl.has_cover is True
        assert tpl.has_toc is True
        assert tpl.has_header_footer is True

    def test_article_template_supports_two_column(self):
        """文章模板应支持双栏。"""
        tpl = TEMPLATES["article"]
        assert tpl.two_column is True

    def test_resume_template_no_cover(self):
        """简历模板不应有封面。"""
        tpl = TEMPLATES["resume"]
        assert tpl.has_cover is False
        assert tpl.has_toc is False

    def test_letter_template_uses_letter_page_size(self):
        """信函模板应使用 LETTER 页面尺寸。"""
        tpl = TEMPLATES["letter"]
        assert tpl.page_size == "LETTER"

    def test_ebook_template_has_cover_and_toc(self):
        """电子书模板应包含封面和目录。"""
        tpl = TEMPLATES["ebook"]
        assert tpl.has_cover is True
        assert tpl.has_toc is True


# ============================================================================
# TEST SUITE 2: Markdown Parsing
# ============================================================================


class TestMarkdownParsing:
    """Markdown 解析功能测试。"""

    def test_escape_xml_basic(self):
        """XML 特殊字符应被正确转义。"""
        assert _escape_xml("a & b") == "a &amp; b"
        assert _escape_xml("a < b") == "a &lt; b"
        assert _escape_xml("a > b") == "a &gt; b"

    def test_escape_xml_preserves_plain_text(self):
        """纯文本应保持不变。"""
        assert _escape_xml("Hello World") == "Hello World"

    def test_parse_inline_bold(self):
        """**bold** 应转为 <b>bold</b>。"""
        result = _parse_inline_markdown("**bold text**")
        assert "<b>bold text</b>" in result

    def test_parse_inline_italic(self):
        """*italic* 应转为 <i>italic</i>。"""
        result = _parse_inline_markdown("*italic text*")
        assert "<i>italic text</i>" in result

    def test_parse_inline_code(self):
        """`code` 应转为 Courier 字体标签。"""
        result = _parse_inline_markdown("`code here`")
        assert '<font name="Courier">code here</font>' in result

    def test_parse_inline_mixed(self):
        """混合行内标记应全部正确解析。"""
        result = _parse_inline_markdown("**bold** and *italic* and `code`")
        assert "<b>bold</b>" in result
        assert "<i>italic</i>" in result
        assert '<font name="Courier">code</font>' in result

    def test_parse_markdown_h2_heading(self, sample_markdown):
        """## 标题应解析为 Heading2 段落。"""
        styles = _build_styles("report", "Test", "Author")
        flowables = _parse_markdown_to_flowables(sample_markdown, styles)
        # 应包含至少一个 Paragraph
        assert len(flowables) > 0
        # 查找 Heading2 类型的段落
        headings = [f for f in flowables if hasattr(f, "style") and f.style.name == "Heading2"]
        assert len(headings) >= 2  # Introduction, Key Features, Steps

    def test_parse_markdown_h3_heading(self, sample_markdown):
        """### 子标题应解析为 Heading3 段落。"""
        styles = _build_styles("report", "Test", "Author")
        flowables = _parse_markdown_to_flowables(sample_markdown, styles)
        headings = [f for f in flowables if hasattr(f, "style") and f.style.name == "Heading3"]
        assert len(headings) >= 1  # Subsection

    def test_parse_markdown_unordered_list(self, sample_markdown):
        """无序列表应解析为 ListFlowable。"""
        from reportlab.platypus import ListFlowable

        styles = _build_styles("report", "Test", "Author")
        flowables = _parse_markdown_to_flowables(sample_markdown, styles)
        lists = [f for f in flowables if isinstance(f, ListFlowable)]
        assert len(lists) >= 1

    def test_parse_markdown_ordered_list(self, sample_markdown):
        """有序列表应解析为 ListFlowable。"""
        from reportlab.platypus import ListFlowable

        styles = _build_styles("report", "Test", "Author")
        flowables = _parse_markdown_to_flowables(sample_markdown, styles)
        lists = [f for f in flowables if isinstance(f, ListFlowable)]
        # 应至少有一个有序列表
        assert len(lists) >= 1

    def test_parse_markdown_blockquote(self, sample_markdown):
        """引用块应解析为 Quote 样式段落。"""
        styles = _build_styles("report", "Test", "Author")
        flowables = _parse_markdown_to_flowables(sample_markdown, styles)
        quotes = [f for f in flowables if hasattr(f, "style") and f.style.name == "Quote"]
        assert len(quotes) >= 1

    def test_parse_markdown_plain_paragraph(self):
        """普通段落应解析为 BodyText 段落。"""
        styles = _build_styles("report", "Test", "Author")
        flowables = _parse_markdown_to_flowables("Just a plain paragraph.", styles)
        paragraphs = [
            f for f in flowables
            if hasattr(f, "style") and f.style.name == "BodyText"
        ]
        assert len(paragraphs) == 1

    def test_parse_markdown_separator(self):
        """--- 分隔符应解析为 Spacer。"""
        from reportlab.platypus import Spacer

        styles = _build_styles("report", "Test", "Author")
        flowables = _parse_markdown_to_flowables("Before\n---\nAfter", styles)
        spacers = [f for f in flowables if isinstance(f, Spacer)]
        assert len(spacers) >= 1

    def test_parse_markdown_empty_content(self):
        """空内容应返回空列表。"""
        styles = _build_styles("report", "Test", "Author")
        flowables = _parse_markdown_to_flowables("", styles)
        assert flowables == []

    def test_parse_markdown_chinese_text(self):
        """中文内容应能正常解析。"""
        styles = _build_styles("report", "测试", "作者")
        content = "## 第一章\n\n这是一段中文内容，包含 **加粗** 和 *斜体*。\n"
        flowables = _parse_markdown_to_flowables(content, styles)
        assert len(flowables) > 0


# ============================================================================
# TEST SUITE 3: Style Building
# ============================================================================


class TestStyleBuilding:
    """样式构建功能测试。"""

    def test_build_styles_returns_required_keys(self):
        """应返回所有必需的样式键。"""
        styles = _build_styles("report", "Title", "Author")
        required_keys = {"BodyText", "Heading1", "Heading2", "Heading3", "Quote"}
        assert required_keys.issubset(styles.keys())

    def test_build_styles_report_has_cover_styles(self):
        """报告模板应包含封面样式。"""
        styles = _build_styles("report", "Title", "Author")
        assert "CoverTitle" in styles
        assert "CoverSubtitle" in styles

    def test_build_styles_different_per_template(self):
        """不同模板的正文样式应有差异。"""
        report_styles = _build_styles("report", "T", "A")
        resume_styles = _build_styles("resume", "T", "A")
        # 报告正文字号应大于简历
        assert report_styles["BodyText"].fontSize >= resume_styles["BodyText"].fontSize


# ============================================================================
# TEST SUITE 4: PDF Generation (Sync)
# ============================================================================


class TestPDFGeneration:
    """PDF 文件生成测试（同步方法）。

    直接调用 _generate_pdf_sync，验证文件输出。
    """

    def test_generate_report_pdf(self, sample_request, temp_output_dir):
        """报告模板应成功生成 PDF 文件。"""
        from api.pdf_service import _generate_pdf_sync

        output_path = temp_output_dir / "test_report.pdf"
        _generate_pdf_sync(sample_request, output_path)

        assert output_path.exists()
        assert output_path.stat().st_size > 0
        # 验证 PDF 文件头
        with open(output_path, "rb") as f:
            header = f.read(5)
        assert header == b"%PDF-"

    def test_generate_article_pdf(self, temp_output_dir, sample_markdown):
        """文章模板应成功生成 PDF。"""
        from api.pdf_service import _generate_pdf_sync

        request = PDFGenerationRequest(
            template="article",
            title="Test Article",
            author="Author",
            content=sample_markdown,
            two_column=False,
        )
        output_path = temp_output_dir / "test_article.pdf"
        _generate_pdf_sync(request, output_path)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_generate_article_two_column_pdf(self, temp_output_dir, sample_markdown):
        """文章模板双栏模式应成功生成 PDF。"""
        from api.pdf_service import _generate_pdf_sync

        request = PDFGenerationRequest(
            template="article",
            title="Two Column Article",
            author="Author",
            content=sample_markdown,
            two_column=True,
        )
        output_path = temp_output_dir / "test_article_2col.pdf"
        _generate_pdf_sync(request, output_path)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_generate_resume_pdf(self, temp_output_dir, sample_markdown):
        """简历模板应成功生成 PDF。"""
        from api.pdf_service import _generate_pdf_sync

        request = PDFGenerationRequest(
            template="resume",
            title="Jane Doe",
            author="jane@example.com",
            content=sample_markdown,
        )
        output_path = temp_output_dir / "test_resume.pdf"
        _generate_pdf_sync(request, output_path)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_generate_letter_pdf(self, temp_output_dir, sample_markdown):
        """信函模板应成功生成 PDF。"""
        from api.pdf_service import _generate_pdf_sync

        request = PDFGenerationRequest(
            template="letter",
            title="Cover Letter",
            author="Jane Doe",
            company="Acme Inc.",
            date="2026-06-21",
            content=sample_markdown,
        )
        output_path = temp_output_dir / "test_letter.pdf"
        _generate_pdf_sync(request, output_path)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_generate_ebook_pdf(self, temp_output_dir, sample_markdown):
        """电子书模板应成功生成 PDF。"""
        from api.pdf_service import _generate_pdf_sync

        request = PDFGenerationRequest(
            template="ebook",
            title="My Ebook",
            author="Author",
            content=sample_markdown,
        )
        output_path = temp_output_dir / "test_ebook.pdf"
        _generate_pdf_sync(request, output_path)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_generate_pdf_with_chinese_content(self, temp_output_dir):
        """包含中文内容的 PDF 应成功生成。"""
        from api.pdf_service import _generate_pdf_sync

        request = PDFGenerationRequest(
            template="report",
            title="中文报告标题",
            author="作者名",
            content="## 第一章 引言\n\n这是一段中文正文内容。\n\n- 项目一\n- 项目二\n",
        )
        output_path = temp_output_dir / "test_chinese.pdf"
        _generate_pdf_sync(request, output_path)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_generate_pdf_invalid_template_raises(self, temp_output_dir):
        """无效模板应抛出 ValueError。"""
        from api.pdf_service import _generate_pdf_sync

        request = PDFGenerationRequest(
            template="invalid_template",
            title="Test",
            content="content",
        )
        output_path = temp_output_dir / "invalid.pdf"
        with pytest.raises(ValueError, match="Unknown template"):
            _generate_pdf_sync(request, output_path)


# ============================================================================
# TEST SUITE 5: Chinese Font Registration
# ============================================================================


class TestChineseFont:
    """中文字体注册测试。"""

    def test_register_chinese_font_returns_name_or_none(self):
        """注册函数应返回字体名或 None。"""
        import api.pdf_service as svc

        # 重置缓存以重新尝试注册
        original = svc._REGISTERED_CJK_FONT
        try:
            svc._REGISTERED_CJK_FONT = None
            result = svc._register_chinese_font()
            assert result is None or isinstance(result, str)
        finally:
            svc._REGISTERED_CJK_FONT = original

    def test_get_body_font_returns_string(self):
        """应返回有效的字体名称字符串。"""
        font = _get_body_font()
        assert isinstance(font, str)
        assert len(font) > 0


# ============================================================================
# TEST SUITE 6: Task Tracking
# ============================================================================


class TestTaskTracking:
    """任务状态跟踪测试。

    使用 asyncio.run 同步执行异步方法，不启动 FastAPI 服务。
    """

    def test_submit_task_returns_response(self, clean_tasks, sample_request, temp_output_dir):
        """提交任务应返回 PDFTaskResponse。"""
        result = asyncio.run(PDFService.submit_task(sample_request))
        assert isinstance(result, PDFTaskResponse)
        assert result.task_id
        assert result.status == "pending"

    def test_submit_task_creates_task_record(self, clean_tasks, sample_request, temp_output_dir):
        """提交任务后应能在任务存储中找到记录。"""
        result = asyncio.run(PDFService.submit_task(sample_request))
        task = PDFService.get_task(result.task_id)
        assert task is not None
        assert task.template == "report"
        assert task.title == "Test Report"

    def test_submit_task_invalid_template_raises(self, clean_tasks, temp_output_dir):
        """无效模板应抛出 ValueError。"""
        request = PDFGenerationRequest(
            template="invalid",
            title="Test",
            content="content",
        )
        with pytest.raises(ValueError, match="Unknown template"):
            asyncio.run(PDFService.submit_task(request))

    def test_get_task_nonexistent_returns_none(self, clean_tasks):
        """不存在的任务 ID 应返回 None。"""
        assert PDFService.get_task("nonexistent-id") is None

    def test_list_tasks_empty(self, clean_tasks):
        """空任务列表应返回空 items。"""
        result = PDFService.list_tasks()
        assert isinstance(result, PDFTaskListResponse)
        assert result.items == []
        assert result.total == 0

    def test_list_tasks_pagination(self, clean_tasks, sample_request, temp_output_dir):
        """分页应正确返回指定页的任务。"""
        # 提交多个任务
        for i in range(5):
            req = PDFGenerationRequest(
                template="report",
                title=f"Task {i}",
                content="content",
            )
            asyncio.run(PDFService.submit_task(req))

        # 等待任务记录写入（submit_task 同步写入 _tasks）
        result = PDFService.list_tasks(page=1, page_size=3)
        assert result.total == 5
        assert len(result.items) == 3
        assert result.page == 1
        assert result.page_size == 3

        result_page2 = PDFService.list_tasks(page=2, page_size=3)
        assert len(result_page2.items) == 2

    def test_delete_task_removes_record(self, clean_tasks, sample_request, temp_output_dir):
        """删除任务应移除记录。"""
        result = asyncio.run(PDFService.submit_task(sample_request))
        task_id = result.task_id

        deleted = PDFService.delete_task(task_id)
        assert deleted is True
        assert PDFService.get_task(task_id) is None

    def test_delete_task_nonexistent_returns_false(self, clean_tasks):
        """删除不存在的任务应返回 False。"""
        assert PDFService.delete_task("nonexistent") is False

    def test_task_completes_successfully(self, clean_tasks, sample_request, temp_output_dir):
        """提交任务后应最终变为 completed 状态。"""
        async def _run():
            result = await PDFService.submit_task(sample_request)
            task_id = result.task_id
            # 在同一事件循环中等待后台任务完成
            max_wait = 15.0
            elapsed = 0.0
            while elapsed < max_wait:
                task = PDFService.get_task(task_id)
                if task and task.state in ("completed", "failed"):
                    break
                await asyncio.sleep(0.1)
                elapsed += 0.1
            return PDFService.get_task(task_id)

        task = asyncio.run(_run())
        assert task is not None
        assert task.state == "completed", f"Task failed: {task.error}"
        assert task.progress == 100
        assert task.file_path is not None
        assert task.file_size is not None
        assert task.file_size > 0
        # 文件应实际存在
        assert Path(task.file_path).exists()

    def test_task_failure_records_error(self, clean_tasks, temp_output_dir):
        """生成失败时应记录错误信息。"""
        # 使用无效模板绕过 submit_task 的校验，直接构造会失败的任务
        import api.pdf_service as svc

        request = PDFGenerationRequest(
            template="report",
            title="Test",
            content="content",
        )
        # 手动注入一个会触发失败的请求：替换 TEMPLATES 使生成阶段报错
        original_report = svc.TEMPLATES["report"]
        try:
            # 移除 report 模板使 _generate_pdf_sync 抛出 ValueError
            svc.TEMPLATES.pop("report")
            # 但 submit_task 会校验，所以直接调用 _run_generation
            import uuid
            from datetime import datetime
            task_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            svc._tasks[task_id] = PDFTaskStatus(
                id=task_id,
                state="pending",
                template="report",
                title="Test",
                created_at=now,
                updated_at=now,
            )
            asyncio.run(svc.PDFService._run_generation(task_id, request))

            task = PDFService.get_task(task_id)
            assert task is not None
            assert task.state == "failed"
            assert task.error is not None
        finally:
            svc.TEMPLATES["report"] = original_report

    def test_get_task_file_path_nonexistent(self, clean_tasks):
        """不存在的任务应返回 None 文件路径。"""
        assert PDFService.get_task_file_path("nonexistent") is None

    def test_get_task_file_path_completed(self, clean_tasks, sample_request, temp_output_dir):
        """已完成任务应返回有效文件路径。"""
        async def _run():
            result = await PDFService.submit_task(sample_request)
            task_id = result.task_id
            # 在同一事件循环中等待完成
            max_wait = 15.0
            elapsed = 0.0
            while elapsed < max_wait:
                task = PDFService.get_task(task_id)
                if task and task.state in ("completed", "failed"):
                    break
                await asyncio.sleep(0.1)
                elapsed += 0.1
            return task_id

        task_id = asyncio.run(_run())
        file_path = PDFService.get_task_file_path(task_id)
        assert file_path is not None
        assert file_path.exists()

    def test_delete_task_removes_file(self, clean_tasks, sample_request, temp_output_dir):
        """删除任务时应同时删除生成的 PDF 文件。"""
        async def _run():
            result = await PDFService.submit_task(sample_request)
            task_id = result.task_id
            # 在同一事件循环中等待完成
            max_wait = 15.0
            elapsed = 0.0
            while elapsed < max_wait:
                task = PDFService.get_task(task_id)
                if task and task.state in ("completed", "failed"):
                    break
                await asyncio.sleep(0.1)
                elapsed += 0.1
            return task_id

        task_id = asyncio.run(_run())
        file_path = PDFService.get_task_file_path(task_id)
        assert file_path is not None
        assert file_path.exists()

        PDFService.delete_task(task_id)
        assert not file_path.exists()
        assert PDFService.get_task(task_id) is None


# ============================================================================
# TEST SUITE 7: Pydantic Models
# ============================================================================


class TestPydanticModels:
    """Pydantic 模型验证测试。"""

    def test_pdf_template_model_fields(self):
        """PDFTemplate 应包含所有必需字段。"""
        tpl = PDFTemplate(
            id="test",
            name="Test",
            description="desc",
        )
        assert tpl.page_size == "A4"  # 默认值
        assert tpl.two_column is False
        assert tpl.has_cover is False
        assert tpl.has_toc is False
        assert tpl.has_header_footer is True

    def test_pdf_generation_request_requires_title(self):
        """PDFGenerationRequest 应要求 title 字段。"""
        with pytest.raises(Exception):
            PDFGenerationRequest(
                template="report",
                content="content",
            )  # 缺少 title

    def test_pdf_generation_request_requires_content(self):
        """PDFGenerationRequest 应要求 content 字段。"""
        with pytest.raises(Exception):
            PDFGenerationRequest(
                template="report",
                title="Title",
            )  # 缺少 content

    def test_pdf_generation_request_requires_template(self):
        """PDFGenerationRequest 应要求 template 字段。"""
        with pytest.raises(Exception):
            PDFGenerationRequest(
                title="Title",
                content="content",
            )  # 缺少 template

    def test_pdf_task_response_defaults(self):
        """PDFTaskResponse 应有正确的默认值。"""
        resp = PDFTaskResponse(task_id="abc")
        assert resp.status == "pending"
        assert resp.message == ""

    def test_pdf_task_status_defaults(self):
        """PDFTaskStatus 应有正确的默认值。"""
        status = PDFTaskStatus(id="abc")
        assert status.state == "pending"
        assert status.progress == 0
        assert status.message == ""
        assert status.file_path is None
        assert status.error is None

    def test_pdf_task_list_response_fields(self):
        """PDFTaskListResponse 应包含分页字段。"""
        resp = PDFTaskListResponse(
            items=[], total=0, page=1, page_size=20
        )
        assert resp.items == []
        assert resp.total == 0
        assert resp.page == 1
        assert resp.page_size == 20
