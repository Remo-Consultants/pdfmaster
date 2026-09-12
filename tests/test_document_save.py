"""Save-path tests, including recovery from a failed overwrite."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.document import Document
from src.utils.exceptions import PageOperationError, PDFLoadError
from src.utils.file_handler import FileHandler


def test_save_as_new_file_keeps_original(make_pdf, tmp_path: Path) -> None:
    source = make_pdf(pages=4)
    target = tmp_path / "copy.pdf"
    with Document(source) as document:
        document.delete_page(0)
        saved = document.save(target)
        assert saved == target.resolve()
        assert document.page_count == 3
        assert not document.is_modified
    with Document(source) as original:
        assert original.page_count == 4


def test_overwrite_persists_edits(make_pdf) -> None:
    source = make_pdf(pages=5)
    with Document(source) as document:
        document.delete_page(2)
        document.rotate_page(0, 90)
        document.save(incremental=False)
    with Document(source) as reopened:
        assert reopened.page_count == 4
        assert reopened.get_page_rotation(0) == 90


def test_overwrite_leaves_no_temp_file(make_pdf, tmp_path: Path) -> None:
    source = make_pdf(name="clean.pdf", pages=3)
    with Document(source) as document:
        document.delete_page(1)
        document.save(incremental=False)
    leftovers = [p.name for p in tmp_path.glob("*__pdfmaster_tmp__*")]
    assert leftovers == []


def test_failed_overwrite_keeps_document_usable(make_pdf, tmp_path: Path) -> None:
    """A locked target must not kill the document or leak a temp file."""
    source = make_pdf(name="locked.pdf", pages=3)
    document = Document(source)
    document.delete_page(1)

    blocker = source.open("rb")  # Windows keeps the file from being replaced
    try:
        with pytest.raises(PageOperationError):
            document.save(incremental=False)
    finally:
        blocker.close()

    # The handle survived, the edit survived, and the user is still warned.
    assert document.is_open
    assert document.page_count == 2
    assert document.is_modified
    assert [p.name for p in tmp_path.glob("*__pdfmaster_tmp__*")] == []

    # Recovery path: Save As to a different file still works.
    rescue = tmp_path / "rescued.pdf"
    document.save(rescue)
    document.close()
    with Document(rescue) as saved:
        assert saved.page_count == 2


def test_incremental_save_falls_back(make_pdf) -> None:
    source = make_pdf(pages=3)
    with Document(source) as document:
        document.delete_page(0)
        document.save(incremental=True)
    with Document(source) as reopened:
        assert reopened.page_count == 2


def test_operations_after_close_raise(make_pdf) -> None:
    source = make_pdf(pages=2)
    document = Document(source)
    document.close()
    assert not document.is_open
    with pytest.raises(PDFLoadError):
        document.page_count


def test_ensure_pdf_suffix() -> None:
    assert FileHandler.ensure_pdf_suffix("report").name == "report.pdf"
    assert FileHandler.ensure_pdf_suffix("report.pdf").name == "report.pdf"
    assert FileHandler.ensure_pdf_suffix("report.PDF").name == "report.PDF"
    assert FileHandler.ensure_pdf_suffix("my.report").name == "my.report.pdf"
