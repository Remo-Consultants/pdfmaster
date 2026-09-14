"""Bookmarks/outline sidebar panel for navigating PDF structure."""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.document import Document
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BookmarksPanel(QWidget):
    """Panel showing the PDF document outline/bookmarks as a tree."""

    page_requested = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._document: Optional[Document] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self._header = QLabel("Document Outline")
        self._header.setStyleSheet("font-weight: bold;")
        layout.addWidget(self._header)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(16)
        self._tree.setAnimated(True)
        self._tree.itemClicked.connect(self._on_item_clicked)
        self._tree.itemDoubleClicked.connect(self._on_item_clicked)
        layout.addWidget(self._tree)

        self._no_outline_label = QLabel("This PDF has no outline")
        self._no_outline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_outline_label.setWordWrap(True)
        self._no_outline_label.setStyleSheet("color: #94a3b8; padding: 16px;")
        layout.addWidget(self._no_outline_label)

        self._tree.hide()
        self._no_outline_label.show()

    def set_document(self, document: Optional[Document]) -> None:
        """Load the document outline into the tree."""
        self._document = document
        self._tree.clear()

        if document is None or not document.is_open:
            self._tree.hide()
            self._no_outline_label.show()
            return

        try:
            outline = self._get_outline(document)
            if not outline:
                self._tree.hide()
                self._no_outline_label.show()
                return

            self._build_tree(outline, None)
            self._tree.show()
            self._no_outline_label.hide()
            self._tree.expandAll()
            logger.debug("Loaded outline with %d top-level items", len(outline))
        except Exception as exc:
            logger.warning("Failed to load document outline: %s", exc)
            self._tree.hide()
            self._no_outline_label.show()

    def _get_outline(self, document: Document) -> List[dict]:
        """Extract the outline/table of contents from the PDF."""
        with document.transaction(mark_modified=False) as pdf:
            toc = pdf.get_toc(simple=False)
            if not toc:
                return []

            outline = []
            stack = [(0, outline)]

            for entry in toc:
                level = entry[0]
                title = entry[1]
                page = entry[2] - 1 if entry[2] > 0 else 0

                item = {
                    "title": title,
                    "page": page,
                    "children": [],
                }

                while stack and level <= stack[-1][0]:
                    stack.pop()

                if stack:
                    stack[-1][1].append(item)
                else:
                    outline.append(item)

                stack.append((level, item["children"]))

            return outline

    def _build_tree(
        self, items: List[dict], parent: Optional[QTreeWidgetItem]
    ) -> None:
        """Recursively build tree widget items from outline."""
        for item in items:
            if parent is None:
                tree_item = QTreeWidgetItem(self._tree)
            else:
                tree_item = QTreeWidgetItem(parent)

            title = item.get("title", "Untitled")
            page = item.get("page", 0)

            tree_item.setText(0, title)
            tree_item.setData(0, Qt.ItemDataRole.UserRole, page)
            tree_item.setToolTip(0, f"{title} (Page {page + 1})")

            children = item.get("children", [])
            if children:
                self._build_tree(children, tree_item)

    def _on_item_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        """Navigate to the page when a bookmark is clicked."""
        page = item.data(0, Qt.ItemDataRole.UserRole)
        if page is not None and self._document is not None:
            page = max(0, min(page, self._document.page_count - 1))
            self.page_requested.emit(page)
            logger.debug("Bookmark navigation to page %d", page + 1)

    def refresh(self) -> None:
        """Refresh the outline from the current document."""
        self.set_document(self._document)
