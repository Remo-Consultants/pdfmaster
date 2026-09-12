"""Side panel showing document properties and page annotations."""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.document import Document
from src.processors.annotations import AnnotationProcessor
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _format_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


class InfoPanel(QWidget):
    """Document metadata plus the annotation list for the current page."""

    delete_requested = Signal(int, int)  # page, annotation index
    annotation_selected = Signal(int, int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._document: Optional[Document] = None
        self._page = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # --- Properties -------------------------------------------------
        props = QGroupBox("Document")
        form = QFormLayout(props)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setContentsMargins(10, 12, 10, 10)
        self._labels = {}
        for key, caption in (
            ("name", "File"),
            ("pages", "Pages"),
            ("size", "Size"),
            ("page_size", "Page size"),
            ("rotation", "Rotation"),
            ("encrypted", "Encrypted"),
            ("forms", "Form fields"),
        ):
            value = QLabel("-")
            value.setWordWrap(True)
            value.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            self._labels[key] = value
            form.addRow(f"{caption}:", value)
        layout.addWidget(props)

        # --- Annotations ------------------------------------------------
        annots = QGroupBox("Markup on this page")
        annot_layout = QVBoxLayout(annots)
        annot_layout.setContentsMargins(8, 12, 8, 8)
        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.currentRowChanged.connect(self._on_row_changed)
        annot_layout.addWidget(self._list)

        buttons = QHBoxLayout()
        self._delete_button = QPushButton("Delete selected")
        self._delete_button.setEnabled(False)
        self._delete_button.clicked.connect(self._on_delete)
        buttons.addWidget(self._delete_button)
        buttons.addStretch(1)
        annot_layout.addLayout(buttons)
        layout.addWidget(annots, 1)

    # ------------------------------------------------------------------
    def set_document(self, document: Optional[Document]) -> None:
        self._document = document
        self.refresh(0)

    def refresh(self, page: Optional[int] = None) -> None:
        """Re-read properties and the annotation list."""
        if page is not None:
            self._page = page
        self._update_properties()
        self._update_annotations()

    # ------------------------------------------------------------------
    def _set(self, key: str, value: str) -> None:
        self._labels[key].setText(value)

    def _update_properties(self) -> None:
        document = self._document
        if document is None or not document.is_open:
            for key in self._labels:
                self._set(key, "-")
            return

        try:
            info = document.get_metadata()
        except Exception as exc:  # noqa: BLE001 - panel must not break the UI
            logger.debug("Could not read document info: %s", exc)
            info = {}

        self._set("name", document.filename or "-")
        self._set("pages", str(info.get("page_count", document.page_count)))
        size = info.get("file_size_bytes")
        self._set("size", _format_size(size) if isinstance(size, int) else "-")
        try:
            width, height = document.get_page_size(self._page)
            self._set("page_size", f"{width:.0f} x {height:.0f} pt")
            self._set("rotation", f"{document.get_page_rotation(self._page)} deg")
        except Exception:  # noqa: BLE001
            self._set("page_size", "-")
            self._set("rotation", "-")
        self._set("encrypted", "Yes" if info.get("encrypted") else "No")

        try:
            with document.transaction(mark_modified=False) as pdf:
                count = sum(1 for _ in (pdf.load_page(self._page).widgets() or []))
                has_form = bool(pdf.is_form_pdf)
        except Exception:  # noqa: BLE001
            count, has_form = 0, False
        self._set("forms", f"{count} on this page" if has_form else "None")

    def _update_annotations(self) -> None:
        self._list.clear()
        self._delete_button.setEnabled(False)
        document = self._document
        if document is None or not document.is_open:
            return
        try:
            entries: List[dict] = AnnotationProcessor.list_annotations(
                document, self._page
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not list annotations: %s", exc)
            return

        if not entries:
            item = QListWidgetItem("No markup on this page")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._list.addItem(item)
            return

        for entry in entries:
            label = entry.get("type") or "Annotation"
            content = (entry.get("content") or "").strip()
            if content:
                label = f"{label} - {content[:40]}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, entry.get("index"))
            self._list.addItem(item)

    # ------------------------------------------------------------------
    def _on_row_changed(self, row: int) -> None:
        item = self._list.item(row) if row >= 0 else None
        index = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        self._delete_button.setEnabled(index is not None)
        if index is not None:
            self.annotation_selected.emit(self._page, int(index))

    def _on_delete(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        index = item.data(Qt.ItemDataRole.UserRole)
        if index is None:
            return
        self.delete_requested.emit(self._page, int(index))
