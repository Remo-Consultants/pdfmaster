"""Panel for extracting text from PDF pages and copying to clipboard."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QClipboard
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.core.document import Document
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TextExtractPanel(QWidget):
    """Panel for extracting and copying text from PDF pages."""

    text_extracted = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._document: Optional[Document] = None
        self._current_page = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        scope_group = QGroupBox("Extraction Scope")
        scope_layout = QVBoxLayout(scope_group)

        scope_row = QHBoxLayout()
        self._scope_box = QComboBox()
        self._scope_box.addItem("Current page", "current")
        self._scope_box.addItem("Page range", "range")
        self._scope_box.addItem("All pages", "all")
        self._scope_box.currentIndexChanged.connect(self._on_scope_changed)
        scope_row.addWidget(QLabel("Scope:"))
        scope_row.addWidget(self._scope_box, 1)
        scope_layout.addLayout(scope_row)

        range_row = QHBoxLayout()
        self._from_spin = QSpinBox()
        self._from_spin.setMinimum(1)
        self._from_spin.setMaximum(1)
        self._to_spin = QSpinBox()
        self._to_spin.setMinimum(1)
        self._to_spin.setMaximum(1)
        range_row.addWidget(QLabel("From:"))
        range_row.addWidget(self._from_spin)
        range_row.addWidget(QLabel("To:"))
        range_row.addWidget(self._to_spin)
        range_row.addStretch(1)
        scope_layout.addLayout(range_row)
        self._range_widgets = [self._from_spin, self._to_spin]

        layout.addWidget(scope_group)

        buttons_row = QHBoxLayout()
        self._extract_button = QPushButton("Extract Text")
        self._extract_button.clicked.connect(self._on_extract)
        self._extract_button.setEnabled(False)
        buttons_row.addWidget(self._extract_button)
        buttons_row.addStretch(1)
        layout.addLayout(buttons_row)

        text_group = QGroupBox("Extracted Text")
        text_layout = QVBoxLayout(text_group)
        self._text_edit = QPlainTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setPlaceholderText(
            "Click 'Extract Text' to extract text from the selected pages..."
        )
        text_layout.addWidget(self._text_edit)

        copy_row = QHBoxLayout()
        self._copy_button = QPushButton("Copy to Clipboard")
        self._copy_button.clicked.connect(self._on_copy)
        self._copy_button.setEnabled(False)
        self._char_count_label = QLabel("0 characters")
        copy_row.addWidget(self._copy_button)
        copy_row.addStretch(1)
        copy_row.addWidget(self._char_count_label)
        text_layout.addLayout(copy_row)

        layout.addWidget(text_group, 1)
        self._on_scope_changed(0)

    def set_document(self, document: Optional[Document]) -> None:
        """Set the document to extract text from."""
        self._document = document
        self._text_edit.clear()
        self._char_count_label.setText("0 characters")
        self._copy_button.setEnabled(False)

        if document is None or not document.is_open:
            self._extract_button.setEnabled(False)
            self._from_spin.setMaximum(1)
            self._to_spin.setMaximum(1)
            return

        self._extract_button.setEnabled(True)
        page_count = document.page_count
        self._from_spin.setMaximum(page_count)
        self._to_spin.setMaximum(page_count)
        self._from_spin.setValue(1)
        self._to_spin.setValue(page_count)
        logger.debug("Text extract panel set to document with %d pages", page_count)

    def set_current_page(self, page: int) -> None:
        """Update the current page for 'current page' extraction."""
        self._current_page = page
        if self._scope_box.currentData() == "current":
            self._from_spin.setValue(page + 1)
            self._to_spin.setValue(page + 1)

    def _on_scope_changed(self, _index: int) -> None:
        scope = self._scope_box.currentData()
        range_enabled = scope == "range"
        for widget in self._range_widgets:
            widget.setEnabled(range_enabled)

        if scope == "current":
            self._from_spin.setValue(self._current_page + 1)
            self._to_spin.setValue(self._current_page + 1)
        elif scope == "all" and self._document is not None:
            self._from_spin.setValue(1)
            self._to_spin.setValue(self._document.page_count)

    def _on_extract(self) -> None:
        if self._document is None or not self._document.is_open:
            return

        scope = self._scope_box.currentData()
        if scope == "current":
            start = self._current_page
            end = self._current_page
        elif scope == "range":
            start = self._from_spin.value() - 1
            end = self._to_spin.value() - 1
        else:
            start = 0
            end = self._document.page_count - 1

        start = max(0, min(start, self._document.page_count - 1))
        end = max(start, min(end, self._document.page_count - 1))

        text_parts = []
        for page_num in range(start, end + 1):
            try:
                page_text = self._document.get_page_text(page_num)
                if page_text.strip():
                    if end > start:
                        text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")
                    else:
                        text_parts.append(page_text)
            except Exception as exc:
                logger.warning("Failed to extract text from page %d: %s", page_num, exc)
                text_parts.append(f"--- Page {page_num + 1} ---\n[Error extracting text]")

        full_text = "\n\n".join(text_parts)
        self._text_edit.setPlainText(full_text)

        char_count = len(full_text)
        self._char_count_label.setText(f"{char_count:,} characters")
        self._copy_button.setEnabled(char_count > 0)
        self.text_extracted.emit(full_text)
        logger.info(
            "Extracted %d characters from pages %d-%d",
            char_count, start + 1, end + 1
        )

    def _on_copy(self) -> None:
        text = self._text_edit.toPlainText()
        if not text:
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(text, QClipboard.Mode.Clipboard)
        logger.debug("Copied %d characters to clipboard", len(text))
