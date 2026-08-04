from open_notebook.utils.document_preprocessor import preprocess_document


def test_merges_pdf_forced_line_breaks_inside_sentence():
    text = "备考的压力让学子渴望安静的环境，其诉求背后是对冲刺梦想\n的珍视。"

    result = preprocess_document(text)

    assert "备考的压力让学子渴望安静的环境，其诉求背后是对冲刺梦想的珍视。" in result.cleaned_text


def test_preserves_real_paragraph_breaks():
    text = (
        "第一段开头，继续\n"
        "说明同一段内容。\n"
        "\n"
        "\n"
        "第二段应该单独保留。"
    )

    result = preprocess_document(text)

    assert "第一段开头，继续说明同一段内容。\n\n第二段应该单独保留。" in result.cleaned_text


def test_detects_heading_levels():
    text = "或许\"鸟巢\"不拆，也可两全\n\n粉笔说：\n这是一段正文。"

    result = preprocess_document(text)

    assert "# 或许\"鸟巢\"不拆，也可两全" in result.cleaned_text
    assert "## 粉笔说：" in result.cleaned_text
    assert result.chunks[0].title == '或许"鸟巢"不拆，也可两全'
    assert result.chunks[0].subtitle == "粉笔说："


def test_removes_disclaimer_footer_and_page_number_noise():
    text = (
        "第 1 页\n"
        "正文第一句\n"
        "仍然属于正文。\n"
        "免责声明\n"
        "本资料仅供内部交流，不得用于商业用途。\n"
        "Come to meet a different you\n"
    )

    result = preprocess_document(text)

    assert "第 1 页" not in result.cleaned_text
    assert "免责声明" not in result.cleaned_text
    assert "本资料仅供内部交流" not in result.cleaned_text
    assert "Come to meet a different you" not in result.cleaned_text
    assert "正文第一句仍然属于正文。" in result.cleaned_text
    assert result.removed_line_count >= 4


def test_chunk_metadata_includes_source_file_and_page_number_when_available():
    text = "第 2 页\n\n或许\"鸟巢\"不拆，也可两全\n\n粉笔说：\n正文内容可以用于检索。"

    result = preprocess_document(
        text,
        source_title="热点导读",
        source_file=r"E:\uploads\sample.pdf",
    )

    assert result.chunks
    chunk = result.chunks[0]
    assert chunk.source_file == "sample.pdf"
    assert chunk.page_number == 2
    assert chunk.section == "粉笔说："
    assert chunk.chunk_index == 0
