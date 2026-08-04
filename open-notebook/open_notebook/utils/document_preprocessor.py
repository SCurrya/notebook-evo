"""
Document preprocessing utilities for cleaner RAG embeddings.

The preprocessor focuses on text extracted from PDFs where visual layout often
leaks into plain text: forced line breaks, repeated headers/footers, page
numbers, boilerplate disclaimers, and weak section boundaries.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

from loguru import logger

from open_notebook.utils.chunking import CHUNK_SIZE
from open_notebook.utils.token_utils import token_count


_SENTENCE_END_RE = re.compile(r"[。！？!?；;：:]$|[.!?][\"')\]]?$")
_PAGE_NUMBER_RE = re.compile(
    r"^\s*(?:第\s*)?\d{1,4}\s*(?:页|/\s*\d{1,4}|of\s+\d{1,4})?\s*$",
    re.IGNORECASE,
)
_URL_OR_EMAIL_RE = re.compile(r"(https?://|www\.|@[\w.-]+\.[a-z]{2,})", re.IGNORECASE)
_DISCLAIMER_RE = re.compile(
    r"(免责声明|本资料仅供|仅供内部交流|不得用于商业用途|版权归|come to meet a different you)",
    re.IGNORECASE,
)
_CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")


@dataclass
class DocumentChunk:
    content: str
    title: Optional[str] = None
    subtitle: Optional[str] = None
    page_number: Optional[int] = None
    source_file: Optional[str] = None
    section: Optional[str] = None
    chunk_index: int = 0

    def metadata(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "page_number": self.page_number,
            "source_file": self.source_file,
            "section": self.section,
            "chunk_index": self.chunk_index,
        }


@dataclass
class PreprocessedDocument:
    original_text: str
    cleaned_text: str
    chunks: list[DocumentChunk] = field(default_factory=list)
    removed_line_count: int = 0


@dataclass(frozen=True)
class _TextLine:
    text: str
    page_number: Optional[int] = None


@dataclass(frozen=True)
class _Paragraph:
    text: str
    page_number: Optional[int] = None


def preprocess_document(
    text: str,
    *,
    source_title: Optional[str] = None,
    source_file: Optional[str] = None,
    max_chunk_tokens: int = CHUNK_SIZE,
) -> PreprocessedDocument:
    """Clean extracted document text and split it into semantic chunks."""
    if not text or not text.strip():
        return PreprocessedDocument(original_text=text or "", cleaned_text="", chunks=[])

    source_name = Path(source_file).name if source_file else None
    raw_lines = _split_text_into_lines(text)
    lines, removed = _remove_noise_lines(raw_lines, source_title, source_name)
    paragraphs = _merge_wrapped_lines(lines)
    cleaned = _format_with_headings(paragraphs)
    chunks = _semantic_chunks(
        paragraphs,
        source_title=source_title,
        source_file=source_name or source_file,
        max_chunk_tokens=max_chunk_tokens,
    )
    for idx, chunk in enumerate(chunks):
        chunk.chunk_index = idx

    logger.info(
        "Preprocessed document: original_chars={} cleaned_chars={} chunks={} removed_lines={}",
        len(text),
        len(cleaned),
        len(chunks),
        removed,
    )
    return PreprocessedDocument(
        original_text=text,
        cleaned_text=cleaned,
        chunks=chunks,
        removed_line_count=removed,
    )


def _remove_noise_lines(
    raw_lines: Iterable[_TextLine],
    source_title: Optional[str],
    source_file: Optional[str],
) -> tuple[list[_TextLine], int]:
    normalized = [
        _TextLine(_normalize_line(line.text), line.page_number) for line in raw_lines
    ]
    non_empty = [line.text for line in normalized if line.text]
    repeated = _detect_repeated_lines(non_empty)
    title_candidates = {s.strip() for s in (source_title, source_file) if s}
    title_candidates.update(Path(s).stem for s in list(title_candidates) if "." in s)

    kept: list[_TextLine] = []
    removed = 0
    in_disclaimer = False
    for line in normalized:
        if not line.text:
            kept.append(line)
            continue

        if _DISCLAIMER_RE.search(line.text):
            in_disclaimer = True
            removed += 1
            continue
        if in_disclaimer:
            if _looks_like_primary_title(line.text):
                in_disclaimer = False
            else:
                removed += 1
                continue

        if _PAGE_NUMBER_RE.match(line.text):
            removed += 1
            continue
        if line.text in repeated and not _looks_like_heading(line.text):
            removed += 1
            continue
        if line.text in repeated and any(
            _similar_text(line.text, candidate) for candidate in title_candidates
        ):
            removed += 1
            continue
        if _looks_like_publication_footer(line.text):
            removed += 1
            continue

        kept.append(line)

    return _collapse_blank_lines(kept), removed


def _detect_repeated_lines(lines: list[str]) -> set[str]:
    counts: dict[str, int] = {}
    for line in lines:
        if len(line) > 80:
            continue
        counts[line] = counts.get(line, 0) + 1
    threshold = max(3, len(lines) // 40)
    return {line for line, count in counts.items() if count >= threshold}


def _merge_wrapped_lines(lines: list[_TextLine]) -> list[_Paragraph]:
    paragraphs: list[_Paragraph] = []
    buffer = ""
    buffer_page: Optional[int] = None
    blank_count = 0

    for line in lines:
        if not line.text:
            if buffer:
                paragraphs.append(_Paragraph(buffer.strip(), buffer_page))
                buffer = ""
                buffer_page = None
            blank_count += 1
            if blank_count >= 2 and paragraphs and paragraphs[-1].text:
                paragraphs.append(_Paragraph(""))
            continue

        blank_count = 0
        if _looks_like_heading(line.text):
            if buffer:
                paragraphs.append(_Paragraph(buffer.strip(), buffer_page))
                buffer = ""
                buffer_page = None
            paragraphs.append(_Paragraph(line.text, line.page_number))
            continue

        if not buffer:
            buffer = line.text
            buffer_page = line.page_number
            continue

        if _should_join(buffer, line.text):
            separator = "" if _is_cjk_boundary(buffer, line.text) else " "
            buffer = f"{buffer}{separator}{line.text}"
            buffer_page = buffer_page or line.page_number
        else:
            paragraphs.append(_Paragraph(buffer.strip(), buffer_page))
            buffer = line.text
            buffer_page = line.page_number

    if buffer:
        paragraphs.append(_Paragraph(buffer.strip(), buffer_page))

    return _collapse_blank_lines(paragraphs)


def _format_with_headings(paragraphs: list[_Paragraph]) -> str:
    output: list[str] = []
    for paragraph in paragraphs:
        if not paragraph.text:
            if output and output[-1] != "":
                output.append("")
            continue
        level = _heading_level(paragraph.text)
        if level == 1:
            output.extend([f"# {paragraph.text}", ""])
        elif level == 2:
            output.extend([f"## {paragraph.text}", ""])
        else:
            output.extend([paragraph.text, ""])
    return "\n".join(output).strip()


def _semantic_chunks(
    paragraphs: list[_Paragraph],
    *,
    source_title: Optional[str],
    source_file: Optional[str],
    max_chunk_tokens: int,
) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    current_title = source_title
    current_subtitle: Optional[str] = None
    current_parts: list[_Paragraph] = []

    def flush() -> None:
        nonlocal current_parts
        content = "\n\n".join(part.text for part in current_parts if part.text).strip()
        page_number = next(
            (part.page_number for part in current_parts if part.page_number is not None),
            None,
        )
        current_parts = []
        if not content:
            return
        section = current_subtitle or current_title
        for piece in _split_oversized(content, max_chunk_tokens):
            chunks.append(
                DocumentChunk(
                    content=piece,
                    title=current_title,
                    subtitle=current_subtitle,
                    page_number=page_number,
                    source_file=source_file,
                    section=section,
                )
            )

    for paragraph in paragraphs:
        if not paragraph.text:
            continue
        level = _heading_level(paragraph.text)
        if level == 1:
            flush()
            current_title = paragraph.text
            current_subtitle = None
            continue
        if level == 2:
            flush()
            current_subtitle = paragraph.text
            continue

        candidate = "\n\n".join(part.text for part in current_parts + [paragraph])
        if current_parts and token_count(candidate) > max_chunk_tokens:
            flush()
        current_parts.append(paragraph)

    flush()
    return chunks


def _split_oversized(text: str, max_chunk_tokens: int) -> list[str]:
    if token_count(text) <= max_chunk_tokens:
        return [text]

    sentences = _split_sentences(text)
    pieces: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current}{'' if not current else ' '}{sentence}".strip()
        if current and token_count(candidate) > max_chunk_tokens:
            pieces.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces or [text]


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？!?\.])\s+", text)
    return [part.strip() for part in parts if part.strip()]


def _should_join(previous: str, current: str) -> bool:
    if _looks_like_heading(current):
        return False
    if previous.endswith(("-", "—")):
        return True
    if _SENTENCE_END_RE.search(previous):
        return False
    if current[:1] in "，。！？；：,.!?;:":
        return True
    return True


def _heading_level(line: str) -> int:
    if _looks_like_primary_title(line):
        return 1
    if _looks_like_secondary_title(line):
        return 2
    return 0


def _looks_like_heading(line: str) -> bool:
    return _heading_level(line) > 0


def _looks_like_primary_title(line: str) -> bool:
    stripped = line.strip().strip("# ")
    if not stripped or len(stripped) > 42:
        return False
    if _URL_OR_EMAIL_RE.search(stripped) or _SENTENCE_END_RE.search(stripped):
        return False
    has_cjk = bool(_CHINESE_RE.search(stripped))
    quote_title = ("“" in stripped or '"' in stripped or "《" in stripped) and has_cjk
    title_markers = (
        "篇",
        "章",
        "节",
        "一、",
        "二、",
        "三、",
        "四、",
        "五、",
        "热点",
        "导读",
        "评论",
        "申论",
    )
    compact_title = (
        has_cjk
        and len(stripped) <= 24
        and len(stripped) >= 6
        and not any(mark in stripped for mark in "，,；;：:")
        and any(marker in stripped for marker in title_markers)
    )
    return quote_title or compact_title


def _looks_like_secondary_title(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 36:
        return False
    return stripped.endswith(("：", ":")) and not re.search(r"[。！？!?]$", stripped)


def _looks_like_publication_footer(line: str) -> bool:
    lower = line.lower()
    if "come to meet a different you" in lower:
        return True
    return bool(re.search(r"(公众号|微信|微博|网址|电话|地址|出版|版权所有)", line))


def _normalize_line(line: str) -> str:
    line = line.replace("\u00a0", " ").replace("\u3000", " ")
    line = re.sub(r"\s+", " ", line)
    return line.strip()


def _collapse_blank_lines(lines: list) -> list:
    collapsed: list = []
    for line in lines:
        if not line.text:
            if collapsed and collapsed[-1].text:
                collapsed.append(line)
            continue
        collapsed.append(line)
    while collapsed and not collapsed[-1].text:
        collapsed.pop()
    return collapsed


def _is_cjk_boundary(previous: str, current: str) -> bool:
    return bool(
        previous
        and current
        and _CHINESE_RE.search(previous[-1])
        and _CHINESE_RE.search(current[0])
    )


def _similar_text(left: str, right: str) -> bool:
    left_norm = re.sub(r"\W+", "", left).lower()
    right_norm = re.sub(r"\W+", "", right).lower()
    return bool(
        left_norm
        and right_norm
        and (left_norm == right_norm or left_norm in right_norm)
    )


def _split_text_into_lines(text: str) -> list[_TextLine]:
    lines: list[_TextLine] = []
    if "\f" in text:
        for page_idx, page_text in enumerate(text.split("\f"), start=1):
            for line in page_text.splitlines():
                lines.append(_TextLine(line, page_idx))
        return lines

    current_page: Optional[int] = None
    for raw_line in text.splitlines():
        page_number = _extract_page_number(raw_line)
        if page_number is not None:
            current_page = page_number
        lines.append(_TextLine(raw_line, current_page))
    return lines


def _extract_page_number(line: str) -> Optional[int]:
    normalized = _normalize_line(line)
    patterns = (
        r"^第\s*(\d{1,4})\s*页$",
        r"^page\s+(\d{1,4})$",
        r"^(\d{1,4})\s*/\s*\d{1,4}$",
        r"^(\d{1,4})\s+of\s+\d{1,4}$",
        r"^(\d{1,4})$",
    )
    for pattern in patterns:
        match = re.match(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None
