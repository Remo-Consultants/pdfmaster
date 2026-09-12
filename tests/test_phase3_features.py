"""Tests for Phase 3 features: text extraction, bookmarks, search, OCR, batch, security."""

from __future__ import annotations

import pytest
from pathlib import Path

import pymupdf as fitz


class TestTextExtraction:
    """Tests for text extraction panel functionality."""

    def test_document_text_extraction(self, make_text_pdf):
        """Test extracting text from a document."""
        from src.core.document import Document

        path = make_text_pdf()
        with Document(path) as doc:
            text = doc.get_page_text(0)
            assert "Invoice Date" in text
            assert "Customer: ACME Corp" in text

    def test_multi_page_extraction(self, make_pdf):
        """Test extracting text from multiple pages."""
        from src.core.document import Document

        path = make_pdf(pages=3)
        with Document(path) as doc:
            texts = []
            for i in range(doc.page_count):
                texts.append(doc.get_page_text(i))
            assert len(texts) == 3
            assert "Page 1" in texts[0]
            assert "Page 2" in texts[1]
            assert "Page 3" in texts[2]


class TestBookmarks:
    """Tests for bookmarks/outline panel functionality."""

    def test_pdf_with_outline(self, tmp_path):
        """Test extracting outline from a PDF with bookmarks."""
        from src.core.document import Document

        path = tmp_path / "with_outline.pdf"
        doc = fitz.open()
        for i in range(5):
            page = doc.new_page(width=612, height=792)
            page.insert_text((72, 72), f"Chapter {i + 1}")

        toc = [
            [1, "Chapter 1", 1],
            [1, "Chapter 2", 2],
            [2, "Section 2.1", 2],
            [1, "Chapter 3", 3],
        ]
        doc.set_toc(toc)
        doc.save(path)
        doc.close()

        with Document(path) as document:
            with document.transaction(mark_modified=False) as pdf:
                outline = pdf.get_toc()
                assert len(outline) == 4
                assert outline[0][1] == "Chapter 1"
                assert outline[2][1] == "Section 2.1"

    def test_pdf_without_outline(self, make_pdf):
        """Test handling of PDF without bookmarks."""
        from src.core.document import Document

        path = make_pdf()
        with Document(path) as doc:
            with doc.transaction(mark_modified=False) as pdf:
                outline = pdf.get_toc()
                assert outline == []


class TestDocumentSearch:
    """Tests for document-wide search functionality."""

    def test_search_finds_text(self, make_text_pdf):
        """Test searching for text in a document."""
        from src.core.document import Document

        path = make_text_pdf()
        with Document(path) as doc:
            with doc.transaction(mark_modified=False) as pdf:
                page = pdf.load_page(0)
                results = page.search_for("ACME")
                assert len(results) > 0

    def test_search_case_insensitive(self, make_text_pdf):
        """Test case-insensitive search."""
        from src.core.document import Document

        path = make_text_pdf()
        with Document(path) as doc:
            with doc.transaction(mark_modified=False) as pdf:
                page = pdf.load_page(0)
                results_lower = page.search_for("acme", flags=1)
                results_upper = page.search_for("ACME", flags=1)
                assert len(results_lower) == len(results_upper)

    def test_search_no_results(self, make_pdf):
        """Test search with no matches."""
        from src.core.document import Document

        path = make_pdf()
        with Document(path) as doc:
            with doc.transaction(mark_modified=False) as pdf:
                page = pdf.load_page(0)
                results = page.search_for("NONEXISTENT_TEXT_12345")
                assert len(results) == 0


class TestBatchService:
    """Tests for batch processing service."""

    def test_find_pdfs(self, tmp_path, make_pdf):
        """Test finding PDFs in a folder."""
        from src.services.batch_service import BatchService

        for i in range(3):
            pdf_path = tmp_path / f"doc{i}.pdf"
            doc = fitz.open()
            doc.new_page()
            doc.save(pdf_path)
            doc.close()

        (tmp_path / "subdir").mkdir()
        subdir_pdf = tmp_path / "subdir" / "nested.pdf"
        doc = fitz.open()
        doc.new_page()
        doc.save(subdir_pdf)
        doc.close()

        files = BatchService.find_pdfs(tmp_path, recursive=True)
        assert len(files) == 4

        files_flat = BatchService.find_pdfs(tmp_path, recursive=False)
        assert len(files_flat) == 3

    def test_compress_pdf(self, tmp_path, make_pdf):
        """Test compressing a single PDF."""
        from src.services.batch_service import BatchService, COMPRESSION_PRESETS

        source = make_pdf(pages=3)
        output = tmp_path / "compressed.pdf"

        preset = COMPRESSION_PRESETS["default"]
        result = BatchService.compress_pdf(source, output, preset)

        assert result.success
        assert result.output == output
        assert output.exists()

    def test_batch_extract_text(self, tmp_path, make_text_pdf):
        """Test batch text extraction."""
        from src.services.batch_service import BatchService

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        output_dir = tmp_path / "output"

        for i in range(2):
            pdf_path = source_dir / f"doc{i}.pdf"
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), f"Document {i} content")
            doc.save(pdf_path)
            doc.close()

        summary = BatchService.batch_extract_text(source_dir, output_dir)
        assert summary.total == 2
        assert summary.successful == 2

        txt_files = list(output_dir.glob("*.txt"))
        assert len(txt_files) == 2


class TestSecurityService:
    """Tests for PDF security service."""

    def test_get_security_info_unencrypted(self, make_pdf):
        """Test getting security info from unencrypted PDF."""
        from src.core.document import Document
        from src.services.security_service import SecurityService

        path = make_pdf()
        with Document(path) as doc:
            info = SecurityService.get_security_info(doc)
            assert not info.is_encrypted
            assert info.can_print
            assert info.can_copy

    def test_set_password(self, tmp_path, make_pdf):
        """Test setting password on a PDF."""
        from src.core.document import Document
        from src.services.security_service import SecurityService

        source = make_pdf()
        output = tmp_path / "protected.pdf"

        with Document(source) as doc:
            SecurityService.set_password(
                doc,
                output,
                user_password="test123",
                owner_password="owner456",
            )

        assert output.exists()

        encrypted_doc = fitz.open(output)
        assert encrypted_doc.is_encrypted
        authenticated = encrypted_doc.authenticate("test123")
        assert authenticated
        encrypted_doc.close()

    def test_remove_password(self, tmp_path, make_pdf):
        """Test removing password from a PDF."""
        from src.core.document import Document
        from src.services.security_service import SecurityService

        source = make_pdf()
        protected = tmp_path / "protected.pdf"
        decrypted = tmp_path / "decrypted.pdf"

        with Document(source) as doc:
            SecurityService.set_password(doc, protected, user_password="test123")

        pdf = fitz.open(protected)
        pdf.authenticate("test123")
        pdf.save(decrypted, encryption=fitz.PDF_ENCRYPT_NONE)
        pdf.close()

        final = fitz.open(decrypted)
        assert not final.is_encrypted
        final.close()


class TestCompressionPresets:
    """Tests for compression presets."""

    def test_all_presets_defined(self):
        """Test that all expected presets are defined."""
        from src.services.batch_service import COMPRESSION_PRESETS

        expected = ["screen", "ebook", "printer", "prepress", "default"]
        for name in expected:
            assert name in COMPRESSION_PRESETS
            preset = COMPRESSION_PRESETS[name]
            assert hasattr(preset, "image_quality")
            assert hasattr(preset, "image_dpi")
            assert hasattr(preset, "garbage_collect")

    def test_preset_values_reasonable(self):
        """Test that preset values are within reasonable ranges."""
        from src.services.batch_service import COMPRESSION_PRESETS

        for name, preset in COMPRESSION_PRESETS.items():
            assert 0 <= preset.image_quality <= 100
            assert 72 <= preset.image_dpi <= 600
            assert 0 <= preset.garbage_collect <= 4


class TestOCRService:
    """Tests for OCR service."""

    def test_ocr_service_init(self):
        """Test OCR service initialization."""
        from src.services.ocr_service import OCRService

        service = OCRService(backend="tesseract", language="eng")
        assert service._backend == "tesseract"
        assert service._language == "eng"

    def test_get_available_backends(self):
        """Test listing available OCR backends."""
        from src.services.ocr_service import OCRService

        service = OCRService()
        backends = service.get_available_backends()
        assert isinstance(backends, list)


class TestUIWidgets:
    """Tests for new UI widgets (headless)."""

    @pytest.fixture
    def app(self, qtbot):
        """Create a QApplication for widget tests."""
        from PySide6.QtWidgets import QApplication
        return QApplication.instance() or QApplication([])

    def test_text_extract_panel_creation(self, app, qtbot):
        """Test creating text extraction panel."""
        from src.ui.widgets.text_extract_panel import TextExtractPanel

        panel = TextExtractPanel()
        qtbot.addWidget(panel)
        assert panel is not None
        assert not panel._extract_button.isEnabled()

    def test_text_extract_panel_with_document(self, app, qtbot, make_text_pdf):
        """Test text extraction panel with a document."""
        from src.core.document import Document
        from src.ui.widgets.text_extract_panel import TextExtractPanel

        panel = TextExtractPanel()
        qtbot.addWidget(panel)

        path = make_text_pdf()
        with Document(path) as doc:
            panel.set_document(doc)
            assert panel._extract_button.isEnabled()
            assert panel._from_spin.maximum() == doc.page_count

    def test_bookmarks_panel_creation(self, app, qtbot):
        """Test creating bookmarks panel."""
        from src.ui.widgets.bookmarks_panel import BookmarksPanel

        panel = BookmarksPanel()
        qtbot.addWidget(panel)
        assert panel is not None
        assert panel._tree.isHidden()
        assert not panel._no_outline_label.isHidden()

    def test_bookmarks_panel_with_outline(self, app, qtbot, tmp_path):
        """Test bookmarks panel with a PDF that has outline."""
        from src.core.document import Document
        from src.ui.widgets.bookmarks_panel import BookmarksPanel

        path = tmp_path / "with_outline.pdf"
        doc = fitz.open()
        for i in range(3):
            doc.new_page()
        doc.set_toc([[1, "Chapter 1", 1], [1, "Chapter 2", 2]])
        doc.save(path)
        doc.close()

        panel = BookmarksPanel()
        qtbot.addWidget(panel)

        with Document(path) as document:
            panel.set_document(document)
            assert not panel._tree.isHidden()
            assert panel._tree.topLevelItemCount() == 2
