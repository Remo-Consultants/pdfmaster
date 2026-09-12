"""Dialog for exporting pages as image files."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from src.constants import (
    DEFAULT_EXPORT_DPI,
    EXPORT_DPI_CHOICES,
    IMAGE_EXPORT_FORMATS,
)


def parse_page_range(text: str, page_count: int) -> List[int]:
    """Parse a range string like ``1-3, 7`` into 0-based page indices.

    An empty string means every page. Out-of-range values are dropped so
    a typo cannot crash the export.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return list(range(page_count))

    pages: set = set()
    for chunk in cleaned.replace(" ", "").split(","):
        if not chunk:
            continue
        if "-" in chunk:
            start, _, end = chunk.partition("-")
            if not start.isdigit() or not end.isdigit():
                continue
            for number in range(int(start), int(end) + 1):
                if 1 <= number <= page_count:
                    pages.add(number - 1)
        elif chunk.isdigit():
            number = int(chunk)
            if 1 <= number <= page_count:
                pages.add(number - 1)
    return sorted(pages)


class ExportImagesDialog(QDialog):
    """Collects the folder, format, resolution, and page range for export."""

    def __init__(self, page_count: int, suggested_dir: Path, parent=None) -> None:
        super().__init__(parent)
        self._page_count = page_count
        self.setWindowTitle("Export Pages as Images")
        self.resize(520, 240)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        folder_row = QHBoxLayout()
        self.folder_edit = QLineEdit(str(suggested_dir))
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse)
        folder_row.addWidget(self.folder_edit, stretch=1)
        folder_row.addWidget(browse)
        form.addRow("Save to", folder_row)

        self.format_box = QComboBox()
        self.format_box.addItems(IMAGE_EXPORT_FORMATS)
        form.addRow("Format", self.format_box)

        self.dpi_box = QComboBox()
        for dpi in EXPORT_DPI_CHOICES:
            self.dpi_box.addItem(f"{dpi} dpi", dpi)
        self.dpi_box.setCurrentIndex(EXPORT_DPI_CHOICES.index(DEFAULT_EXPORT_DPI))
        form.addRow("Resolution", self.dpi_box)

        self.range_edit = QLineEdit()
        self.range_edit.setPlaceholderText(f"All {page_count} pages (e.g. 1-3, 7)")
        form.addRow("Pages", self.range_edit)

        layout.addLayout(form)
        hint = QLabel("Leave Pages empty to export the whole document.")
        hint.setStyleSheet("color: #888;")
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Export")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Choose export folder", self.folder_edit.text()
        )
        if folder:
            self.folder_edit.setText(folder)

    def result_values(self) -> Dict[str, Any]:
        return {
            "folder": Path(self.folder_edit.text()),
            "format": self.format_box.currentText(),
            "dpi": int(self.dpi_box.currentData()),
            "pages": parse_page_range(self.range_edit.text(), self._page_count),
        }
