"""Dialog for OCR operations on scanned PDF pages."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from src.core.document import Document
from src.services.ocr_service import OCRResult, OCRService
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OCRWorker(QThread):
    """Worker thread for OCR processing."""

    progress = Signal(int, int, int)
    page_done = Signal(int, str, float)
    finished = Signal(list)
    error = Signal(str)

    def __init__(
        self,
        document: Document,
        pages: list,
        backend: str,
        language: str,
        dpi: int,
    ) -> None:
        super().__init__()
        self._document = document
        self._pages = pages
        self._backend = backend
        self._language = language
        self._dpi = dpi

    def run(self) -> None:
        try:
            service = OCRService(backend=self._backend, language=self._language)
            if not service.is_available:
                self.error.emit(f"OCR backend '{self._backend}' is not available")
                return

            results = []
            total = len(self._pages)

            for i, page_num in enumerate(self._pages):
                self.progress.emit(i, total, page_num)
                try:
                    result = service.ocr_page(self._document, page_num, self._dpi)
                    results.append(result)
                    self.page_done.emit(page_num, result.text, result.confidence)
                except Exception as exc:
                    logger.warning("OCR failed for page %d: %s", page_num + 1, exc)
                    results.append(OCRResult(page=page_num, text="", confidence=0.0))

            self.finished.emit(results)

        except Exception as exc:
            logger.error("OCR operation failed: %s", exc)
            self.error.emit(str(exc))


class OCRDialog(QDialog):
    """Dialog for performing OCR on PDF pages."""

    def __init__(self, document: Document, current_page: int = 0, parent=None) -> None:
        super().__init__(parent)
        self._document = document
        self._current_page = current_page
        self._worker: Optional[OCRWorker] = None
        self._results: list = []

        self.setWindowTitle("OCR - Optical Character Recognition")
        self.resize(600, 550)

        layout = QVBoxLayout(self)

        service = OCRService()
        available = service.get_available_backends()

        if not available:
            warning = QLabel(
                "No OCR backend is available.\n\n"
                "Install one of the following:\n"
                "- tesseract-ocr (system package) + pytesseract (pip)\n"
                "- easyocr (pip)\n\n"
                "On Ubuntu/Debian: sudo apt install tesseract-ocr\n"
                "Then: pip install pytesseract"
            )
            warning.setStyleSheet("color: red; padding: 20px;")
            warning.setWordWrap(True)
            layout.addWidget(warning)
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            buttons.rejected.connect(self.reject)
            layout.addWidget(buttons)
            return

        settings_group = QGroupBox("OCR Settings")
        settings_layout = QFormLayout(settings_group)

        self._backend_box = QComboBox()
        for backend in available:
            self._backend_box.addItem(backend.title(), backend)
        settings_layout.addRow("Engine:", self._backend_box)

        self._language_box = QComboBox()
        self._language_box.addItem("English", "eng")
        self._language_box.addItem("German", "deu")
        self._language_box.addItem("French", "fra")
        self._language_box.addItem("Spanish", "spa")
        self._language_box.addItem("Italian", "ita")
        self._language_box.addItem("Portuguese", "por")
        self._language_box.addItem("Chinese (Simplified)", "chi_sim")
        self._language_box.addItem("Japanese", "jpn")
        settings_layout.addRow("Language:", self._language_box)

        self._dpi_spin = QSpinBox()
        self._dpi_spin.setRange(72, 600)
        self._dpi_spin.setValue(300)
        self._dpi_spin.setSuffix(" DPI")
        settings_layout.addRow("Resolution:", self._dpi_spin)

        layout.addWidget(settings_group)

        scope_group = QGroupBox("Pages to Process")
        scope_layout = QFormLayout(scope_group)

        self._scope_box = QComboBox()
        self._scope_box.addItem(f"Current page ({current_page + 1})", "current")
        self._scope_box.addItem("All pages", "all")
        self._scope_box.addItem("Page range", "range")
        self._scope_box.currentIndexChanged.connect(self._on_scope_changed)
        scope_layout.addRow("Scope:", self._scope_box)

        range_row = QHBoxLayout()
        self._from_spin = QSpinBox()
        self._from_spin.setRange(1, document.page_count)
        self._from_spin.setValue(1)
        self._to_spin = QSpinBox()
        self._to_spin.setRange(1, document.page_count)
        self._to_spin.setValue(document.page_count)
        range_row.addWidget(QLabel("From:"))
        range_row.addWidget(self._from_spin)
        range_row.addWidget(QLabel("To:"))
        range_row.addWidget(self._to_spin)
        range_row.addStretch(1)
        scope_layout.addRow("Range:", range_row)
        self._from_spin.setEnabled(False)
        self._to_spin.setEnabled(False)

        layout.addWidget(scope_group)

        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        self._progress_bar = QProgressBar()
        progress_layout.addWidget(self._progress_bar)
        self._status_label = QLabel("Ready")
        progress_layout.addWidget(self._status_label)
        layout.addWidget(progress_group)

        result_group = QGroupBox("Extracted Text")
        result_layout = QVBoxLayout(result_group)
        self._text_edit = QPlainTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setPlaceholderText("OCR results will appear here...")
        result_layout.addWidget(self._text_edit)

        result_buttons = QHBoxLayout()
        self._copy_button = QPushButton("Copy to Clipboard")
        self._copy_button.clicked.connect(self._copy_text)
        self._copy_button.setEnabled(False)
        result_buttons.addWidget(self._copy_button)
        result_buttons.addStretch(1)
        result_layout.addLayout(result_buttons)

        layout.addWidget(result_group, 1)

        self._buttons = QDialogButtonBox()
        self._start_button = self._buttons.addButton(
            "Start OCR", QDialogButtonBox.ButtonRole.ActionRole
        )
        self._start_button.clicked.connect(self._start_ocr)
        self._buttons.addButton(QDialogButtonBox.StandardButton.Close)
        self._buttons.rejected.connect(self.close)
        layout.addWidget(self._buttons)

    def _on_scope_changed(self, _index: int) -> None:
        scope = self._scope_box.currentData()
        enabled = scope == "range"
        self._from_spin.setEnabled(enabled)
        self._to_spin.setEnabled(enabled)

    def _get_pages(self) -> list:
        scope = self._scope_box.currentData()
        if scope == "current":
            return [self._current_page]
        elif scope == "all":
            return list(range(self._document.page_count))
        else:
            start = self._from_spin.value() - 1
            end = self._to_spin.value()
            return list(range(start, end))

    def _start_ocr(self) -> None:
        pages = self._get_pages()
        if not pages:
            return

        self._start_button.setEnabled(False)
        self._progress_bar.setValue(0)
        self._progress_bar.setRange(0, len(pages))
        self._text_edit.clear()
        self._results.clear()
        self._status_label.setText("Starting OCR...")

        backend = self._backend_box.currentData()
        language = self._language_box.currentData()
        dpi = self._dpi_spin.value()

        self._worker = OCRWorker(self._document, pages, backend, language, dpi)
        self._worker.progress.connect(self._on_progress)
        self._worker.page_done.connect(self._on_page_done)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, current: int, total: int, page: int) -> None:
        self._progress_bar.setValue(current)
        self._status_label.setText(f"Processing page {page + 1} ({current + 1}/{total})")

    def _on_page_done(self, page: int, text: str, confidence: float) -> None:
        if text.strip():
            self._text_edit.appendPlainText(f"--- Page {page + 1} (confidence: {confidence:.1f}%) ---")
            self._text_edit.appendPlainText(text)
            self._text_edit.appendPlainText("")

    def _on_finished(self, results: list) -> None:
        self._results = results
        self._progress_bar.setValue(self._progress_bar.maximum())
        self._start_button.setEnabled(True)
        self._copy_button.setEnabled(bool(self._text_edit.toPlainText()))

        total_chars = sum(len(r.text) for r in results)
        avg_conf = (
            sum(r.confidence for r in results) / len(results)
            if results
            else 0.0
        )
        self._status_label.setText(
            f"Complete: {total_chars:,} characters extracted, "
            f"{avg_conf:.1f}% average confidence"
        )

    def _on_error(self, message: str) -> None:
        self._start_button.setEnabled(True)
        self._status_label.setText(f"Error: {message}")

    def _copy_text(self) -> None:
        from PySide6.QtWidgets import QApplication
        text = self._text_edit.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self._status_label.setText("Copied to clipboard")

    def closeEvent(self, event) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.wait(1000)
        super().closeEvent(event)
