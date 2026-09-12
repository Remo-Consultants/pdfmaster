"""Tests for the high-level PDFHandler operations."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.document import Document
from src.core.pdf_handler import PDFHandler
from src.utils.exceptions import PageOperationError, ValidationError


def test_merge_documents(make_pdf, tmp_path: Path) -> None:
    first = make_pdf(name="a.pdf", pages=2)
    second = make_pdf(name="b.pdf", pages=3)
    output = tmp_path / "merged.pdf"
    PDFHandler.merge_documents(output, first, second)
    with Document(output) as merged:
        assert merged.page_count == 5


def test_merge_requires_two_files(make_pdf, tmp_path: Path) -> None:
    only = make_pdf(name="solo.pdf", pages=1)
    with pytest.raises(ValidationError):
        PDFHandler.merge_documents(tmp_path / "out.pdf", only)


def test_split_document(make_pdf, tmp_path: Path) -> None:
    source = make_pdf(name="big.pdf", pages=6)
    parts = PDFHandler.split_document(source, [(1, 2), (3, 6)], tmp_path / "parts")
    assert len(parts) == 2
    counts = []
    for part in parts:
        with Document(part) as doc:
            counts.append(doc.page_count)
    assert counts == [2, 4]


def test_split_rejects_bad_range(make_pdf, tmp_path: Path) -> None:
    source = make_pdf(pages=3)
    with pytest.raises(ValidationError):
        PDFHandler.split_document(source, [], tmp_path / "parts")
    with pytest.raises(PageOperationError):
        PDFHandler.split_document(source, [(1, 99)], tmp_path / "parts")


def test_extract_pages(make_pdf, tmp_path: Path) -> None:
    source = make_pdf(pages=5)
    output = tmp_path / "extracted.pdf"
    PDFHandler.extract_pages(source, [2, 4], output)
    with Document(output) as extracted:
        assert extracted.page_count == 2
        assert "Page 2" in extracted.get_page_text(0)
        assert "Page 4" in extracted.get_page_text(1)


def test_extract_requires_pages(make_pdf, tmp_path: Path) -> None:
    source = make_pdf(pages=2)
    with pytest.raises(ValidationError):
        PDFHandler.extract_pages(source, [], tmp_path / "out.pdf")


def test_rotate_pages(make_pdf, tmp_path: Path) -> None:
    source = make_pdf(pages=3)
    output = tmp_path / "rotated.pdf"
    PDFHandler.rotate_pages(source, [1, 3], 90, output)
    with Document(output) as rotated:
        assert rotated.get_page_rotation(0) == 90
        assert rotated.get_page_rotation(1) == 0
        assert rotated.get_page_rotation(2) == 90


def test_get_pdf_info(make_pdf) -> None:
    source = make_pdf(pages=4, width=400, height=800)
    info = PDFHandler.get_pdf_info(source)
    assert info["page_count"] == 4
    assert info["page_width"] == 400
    assert info["page_height"] == 800
    assert info["encrypted"] is False
    assert info["file_size_bytes"] > 0


def test_open_document_rejects_empty_path() -> None:
    with pytest.raises(ValidationError):
        PDFHandler.open_document("   ")
