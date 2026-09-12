"""Core Document tests that require PyMuPDF."""

from __future__ import annotations

from pathlib import Path

import pytest

fitz = pytest.importorskip("pymupdf")

from src.core.document import Document
from src.core.pdf_handler import PDFHandler
from src.utils.exceptions import PageOperationError, PDFLoadError


def _make_pdf(path: Path, pages: int = 3) -> Path:
    doc = fitz.open()
    for index in range(pages):
        page = doc.new_page(width=300, height=400)
        page.insert_text((40, 80), f"Page {index + 1}")
    doc.save(path)
    doc.close()
    return path


def test_document_page_count_and_text(tmp_path: Path) -> None:
    pdf_path = _make_pdf(tmp_path / "sample.pdf", pages=3)
    with Document(pdf_path) as document:
        assert document.get_page_count() == 3
        assert "Page 2" in document.get_page_text(1)
        width, height = document.get_page_size(0)
        assert width > 0 and height > 0
        image = document.render_page_to_image(0, zoom=0.5)
        assert image.size[0] > 0


def test_delete_and_rotate(tmp_path: Path) -> None:
    pdf_path = _make_pdf(tmp_path / "edit.pdf", pages=3)
    with Document(pdf_path) as document:
        document.rotate_page(0, 90)
        assert document.get_page_rotation(0) == 90
        document.delete_page(1)
        assert document.page_count == 2
        document.delete_page(0)
        assert document.page_count == 1
        with pytest.raises(PageOperationError):
            document.delete_page(0)


def test_handler_info_and_extract(tmp_path: Path) -> None:
    pdf_path = _make_pdf(tmp_path / "info.pdf", pages=4)
    info = PDFHandler.get_pdf_info(pdf_path)
    assert info["page_count"] == 4
    output = tmp_path / "extracted.pdf"
    PDFHandler.extract_pages(pdf_path, [1, 3], output)
    with Document(output) as extracted:
        assert extracted.page_count == 2


def test_password_protected_rejected(tmp_path: Path) -> None:
    source = _make_pdf(tmp_path / "plain.pdf", pages=1)
    locked = tmp_path / "locked.pdf"
    doc = fitz.open(source)
    doc.save(
        locked,
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner",
        user_pw="secret",
    )
    doc.close()
    with pytest.raises(PDFLoadError):
        Document(locked)
