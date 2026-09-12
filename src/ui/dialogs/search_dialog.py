"""Document-wide search dialog for finding text across all pages."""

from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.core.document import Document
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SearchResult:
    """Represents a single search result."""

    def __init__(
        self, page: int, text: str, context: str, position: Tuple[float, float, float, float]
    ) -> None:
        self.page = page
        self.text = text
        self.context = context
        self.position = position


class SearchDialog(QDialog):
    """Dialog for searching text across all document pages."""

    go_to_page = Signal(int)
    highlight_result = Signal(int, tuple)

    def __init__(self, document: Document, parent=None) -> None:
        super().__init__(parent)
        self._document = document
        self._results: List[SearchResult] = []

        self.setWindowTitle("Search Document")
        self.resize(600, 450)
        self.setModal(False)

        layout = QVBoxLayout(self)

        search_row = QHBoxLayout()
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Enter search text...")
        self._search_edit.returnPressed.connect(self._on_search)
        search_row.addWidget(self._search_edit, 1)

        self._search_button = QPushButton("Search")
        self._search_button.clicked.connect(self._on_search)
        search_row.addWidget(self._search_button)
        layout.addLayout(search_row)

        options_row = QHBoxLayout()
        self._case_sensitive = QCheckBox("Case sensitive")
        self._whole_word = QCheckBox("Whole words only")
        options_row.addWidget(self._case_sensitive)
        options_row.addWidget(self._whole_word)
        options_row.addStretch(1)
        layout.addLayout(options_row)

        self._status_label = QLabel("Enter text and click Search")
        self._status_label.setStyleSheet("color: #888;")
        layout.addWidget(self._status_label)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self._results_list = QListWidget()
        self._results_list.setAlternatingRowColors(True)
        self._results_list.itemClicked.connect(self._on_result_clicked)
        self._results_list.itemDoubleClicked.connect(self._on_result_double_clicked)
        splitter.addWidget(self._results_list)

        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.addWidget(QLabel("Context:"))
        self._context_label = QLabel()
        self._context_label.setWordWrap(True)
        self._context_label.setStyleSheet(
            "background: #f0f0f0; padding: 8px; border-radius: 4px;"
        )
        self._context_label.setMinimumHeight(60)
        preview_layout.addWidget(self._context_label)
        splitter.addWidget(preview_widget)

        splitter.setSizes([300, 100])
        layout.addWidget(splitter, 1)

        buttons_row = QHBoxLayout()
        self._prev_button = QPushButton("Previous")
        self._prev_button.clicked.connect(self._go_prev)
        self._prev_button.setEnabled(False)
        self._next_button = QPushButton("Next")
        self._next_button.clicked.connect(self._go_next)
        self._next_button.setEnabled(False)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        buttons_row.addWidget(self._prev_button)
        buttons_row.addWidget(self._next_button)
        buttons_row.addStretch(1)
        buttons_row.addWidget(close_button)
        layout.addLayout(buttons_row)

    def _on_search(self) -> None:
        query = self._search_edit.text().strip()
        if not query:
            return

        if self._document is None or not self._document.is_open:
            self._status_label.setText("No document open")
            return

        self._results.clear()
        self._results_list.clear()
        self._context_label.setText("")

        case_sensitive = self._case_sensitive.isChecked()
        whole_word = self._whole_word.isChecked()

        try:
            with self._document.transaction(mark_modified=False) as pdf:
                for page_num in range(pdf.page_count):
                    page = pdf.load_page(page_num)
                    flags = 0
                    if not case_sensitive:
                        flags |= 1
                    text_instances = page.search_for(query, flags=flags)

                    for rect in text_instances:
                        context = self._get_context(page, rect, query)

                        if whole_word:
                            if not self._is_whole_word(context, query, case_sensitive):
                                continue

                        result = SearchResult(
                            page=page_num,
                            text=query,
                            context=context,
                            position=(rect.x0, rect.y0, rect.x1, rect.y1),
                        )
                        self._results.append(result)

                        item = QListWidgetItem(
                            f"Page {page_num + 1}: {context[:80]}..."
                            if len(context) > 80
                            else f"Page {page_num + 1}: {context}"
                        )
                        item.setData(Qt.ItemDataRole.UserRole, len(self._results) - 1)
                        self._results_list.addItem(item)

        except Exception as exc:
            logger.error("Search failed: %s", exc)
            self._status_label.setText(f"Search error: {exc}")
            return

        count = len(self._results)
        if count == 0:
            self._status_label.setText(f"No results found for '{query}'")
        else:
            self._status_label.setText(f"Found {count} result(s) for '{query}'")

        self._prev_button.setEnabled(count > 0)
        self._next_button.setEnabled(count > 0)

        if count > 0:
            self._results_list.setCurrentRow(0)
            self._on_result_clicked(self._results_list.item(0))

        logger.info("Search for '%s' found %d results", query, count)

    def _get_context(self, page, rect, query: str) -> str:
        """Extract text context around the search result."""
        try:
            expanded = rect + (-50, -20, 50, 20)
            expanded.intersect(page.rect)
            text = page.get_text("text", clip=expanded)
            text = " ".join(text.split())
            return text[:200] if text else query
        except Exception:
            return query

    def _is_whole_word(self, context: str, query: str, case_sensitive: bool) -> bool:
        """Check if query appears as a whole word in context."""
        import re
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = rf"\b{re.escape(query)}\b"
        return bool(re.search(pattern, context, flags))

    def _on_result_clicked(self, item: Optional[QListWidgetItem]) -> None:
        if item is None:
            return
        index = item.data(Qt.ItemDataRole.UserRole)
        if index is None or index >= len(self._results):
            return
        result = self._results[index]
        self._context_label.setText(result.context)

    def _on_result_double_clicked(self, item: Optional[QListWidgetItem]) -> None:
        if item is None:
            return
        index = item.data(Qt.ItemDataRole.UserRole)
        if index is None or index >= len(self._results):
            return
        result = self._results[index]
        self.go_to_page.emit(result.page)
        self.highlight_result.emit(result.page, result.position)

    def _go_prev(self) -> None:
        current = self._results_list.currentRow()
        if current > 0:
            self._results_list.setCurrentRow(current - 1)
            self._on_result_double_clicked(self._results_list.currentItem())

    def _go_next(self) -> None:
        current = self._results_list.currentRow()
        if current < self._results_list.count() - 1:
            self._results_list.setCurrentRow(current + 1)
            self._on_result_double_clicked(self._results_list.currentItem())

    def set_search_text(self, text: str) -> None:
        """Pre-fill the search field."""
        self._search_edit.setText(text)
        if text:
            self._on_search()
