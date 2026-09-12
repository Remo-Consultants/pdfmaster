"""Dialog for reordering, adding, and removing pages."""

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

        self.setWindowTitle("Organize Pages")
        self.resize(460, 560)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel("Select a page, then use the buttons to rearrange the document.")
        )

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        layout.addWidget(self._list, stretch=1)

        layout.addLayout(self._build_row([
            ("Move Up", self.move_up),
            ("Move Down", self.move_down),
            ("Duplicate", self.duplicate),
        ]))
        layout.addLayout(self._build_row([
            ("Rotate Left", lambda: self.rotate(-90)),
            ("Rotate Right", lambda: self.rotate(90)),
            ("Delete", self.delete_selected),
        ]))
        layout.addLayout(self._build_row([
            ("Insert Blank Before", self.insert_blank),
            ("Import from PDF...", self.import_pdf),
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
        self._list.clear()
        for summary in PageOrganizer.page_summaries(self._document):
            text = (
                f"Page {summary['number']}  -  "
                f"{summary['width']:.0f} x {summary['height']:.0f} pt  "
                f"({summary['orientation']}"
            )
            text += f", {summary['rotation']}deg)" if summary["rotation"] else ")"
            self._list.addItem(QListWidgetItem(text))
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
