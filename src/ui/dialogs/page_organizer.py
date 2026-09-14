"""Dialog for reordering, merging, adding, and removing pages."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from src.constants import APP_NAME, PDF_FILTER
from src.core.document import Document
from src.processors.page_ops import PageOrganizer
from src.utils.exceptions import PDFMasterException
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PageOrganizerDialog(QDialog):
    """Edit page structure with immediate, undoable changes."""

    document_changed = Signal()

    def __init__(
        self,
        document: Document,
        before_edit: Optional[Callable[[], None]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._document = document
        self._before_edit = before_edit or (lambda: None)
        self._drag_reordering = False

        self.setWindowTitle("Organize Pages")
        self.resize(480, 600)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Drag pages to reorder, or use the buttons. "
                "Changes apply immediately and can be undone with Ctrl+Z."
            )
        )

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._list.model().rowsMoved.connect(self._on_rows_moved)
        layout.addWidget(self._list, stretch=1)

        layout.addLayout(self._build_row([
            ("Move Up", self.move_up),
            ("Move Down", self.move_down),
            ("To Top", self.move_to_top),
            ("To Bottom", self.move_to_bottom),
        ]))
        layout.addLayout(self._build_row([
            ("Reverse Order", self.reverse_order),
            ("Duplicate", self.duplicate),
            ("Delete", self.delete_selected),
        ]))
        layout.addLayout(self._build_row([
            ("Rotate Left", lambda: self.rotate(-90)),
            ("Rotate Right", lambda: self.rotate(90)),
            ("Insert Blank", self.insert_blank),
        ]))
        layout.addLayout(self._build_row([
            ("Import from PDF...", self.import_pdf),
            ("Merge PDFs...", self.merge_pdfs),
        ]))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.accept)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self.refresh()

    # ------------------------------------------------------------------
    def _build_row(self, actions) -> QHBoxLayout:
        row = QHBoxLayout()
        for label, slot in actions:
            button = QPushButton(label)
            button.clicked.connect(slot)
            row.addWidget(button)
        return row

    def refresh(self, keep_row: Optional[int] = None) -> None:
        """Rebuild the page list from the document."""
        row = self._list.currentRow() if keep_row is None else keep_row
        self._drag_reordering = True
        try:
            self._list.clear()
            for summary in PageOrganizer.page_summaries(self._document):
                text = (
                    f"Page {summary['number']}  -  "
                    f"{summary['width']:.0f} x {summary['height']:.0f} pt  "
                    f"({summary['orientation']}"
                )
                text += f", {summary['rotation']}deg)" if summary["rotation"] else ")"
                item = QListWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, summary["index"])
                self._list.addItem(item)
        finally:
            self._drag_reordering = False
        if self._list.count():
            self._list.setCurrentRow(min(max(row, 0), self._list.count() - 1))

    def _selected_rows(self) -> list:
        return sorted(index.row() for index in self._list.selectedIndexes())

    def _current_row(self) -> int:
        return self._list.currentRow()

    def _apply(self, operation: Callable[[], None], keep_row: Optional[int] = None) -> None:
        """Run an edit with undo support and refresh both dialog and viewer."""
        try:
            self._before_edit()
            operation()
        except PDFMasterException as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))
            return
        self.refresh(keep_row)
        self.document_changed.emit()

    def _on_rows_moved(self, *_args) -> None:
        """Apply drag-and-drop order from the list widget to the document."""
        if self._drag_reordering:
            return
        order = [
            self._list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._list.count())
        ]
        if None in order or sorted(order) != list(range(self._document.page_count)):
            self.refresh()
            return
        if order == list(range(self._document.page_count)):
            return
        self._apply(lambda: PageOrganizer.reorder(self._document, order))

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------
    def move_up(self) -> None:
        row = self._current_row()
        if row <= 0:
            return
        self._apply(lambda: PageOrganizer.move_page(self._document, row, row - 1),
                    keep_row=row - 1)

    def move_down(self) -> None:
        row = self._current_row()
        if row < 0 or row >= self._document.page_count - 1:
            return
        self._apply(lambda: PageOrganizer.move_page(self._document, row, row + 1),
                    keep_row=row + 1)

    def move_to_top(self) -> None:
        rows = self._selected_rows()
        if not rows:
            return
        self._apply(
            lambda: PageOrganizer.move_pages_to_edge(
                self._document, rows, to_start=True
            ),
            keep_row=0,
        )

    def move_to_bottom(self) -> None:
        rows = self._selected_rows()
        if not rows:
            return
        self._apply(
            lambda: PageOrganizer.move_pages_to_edge(
                self._document, rows, to_start=False
            ),
            keep_row=self._document.page_count - 1,
        )

    def reverse_order(self) -> None:
        if self._document.page_count < 2:
            return
        self._apply(lambda: PageOrganizer.reverse_order(self._document), keep_row=0)

    def duplicate(self) -> None:
        row = self._current_row()
        if row < 0:
            return
        self._apply(lambda: PageOrganizer.duplicate_page(self._document, row),
                    keep_row=row + 1)

    def rotate(self, degrees: int) -> None:
        rows = self._selected_rows()
        if not rows:
            return
        self._apply(lambda: PageOrganizer.rotate_pages(self._document, rows, degrees))

    def delete_selected(self) -> None:
        rows = self._selected_rows()
        if not rows:
            return
        if self._document.page_count - len(rows) < 1:
            QMessageBox.information(
                self, APP_NAME, "A document must keep at least one page."
            )
            return
        confirm = QMessageBox.question(
            self,
            "Delete pages",
            f"Delete {len(rows)} page(s)? This can be undone with Ctrl+Z.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._apply(lambda: PageOrganizer.delete_pages(self._document, rows),
                    keep_row=max(0, rows[0] - 1))

    def insert_blank(self) -> None:
        row = max(0, self._current_row())
        self._apply(lambda: PageOrganizer.insert_blank_page(self._document, row),
                    keep_row=row)

    def import_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import pages from PDF", str(Path.home()), PDF_FILTER
        )
        if not path:
            return
        at = self._current_row() + 1 if self._current_row() >= 0 else -1
        self._apply(lambda: PageOrganizer.import_pages(self._document, path, at_index=at))

    def merge_pdfs(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Merge PDFs into this document", str(Path.home()), PDF_FILTER
        )
        if not paths:
            return
        at = self._current_row() + 1 if self._current_row() >= 0 else -1
        self._apply(
            lambda: PageOrganizer.merge_pdfs(self._document, paths, at_index=at)
        )
