"""Dialogs for watermarks and rubber stamps."""

from __future__ import annotations

from typing import Any, Dict, Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from src.processors.watermark import STAMP_PRESETS
from src.ui.dialogs.export_dialog import parse_page_range


class WatermarkDialog(QDialog):
    """Configure a multi-page text watermark."""

    def __init__(self, page_count: int, current_page: int = 0, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Watermark")
        self.resize(440, 280)
        self._page_count = max(1, page_count)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.text_edit = QLineEdit("CONFIDENTIAL")
        form.addRow("Text:", self.text_edit)

        self.scope_box = QComboBox()
        self.scope_box.addItem("All pages", "all")
        self.scope_box.addItem(f"Current page ({current_page + 1})", "current")
        self.scope_box.addItem("Page range…", "range")
        form.addRow("Pages:", self.scope_box)

        self.range_edit = QLineEdit()
        self.range_edit.setPlaceholderText(f"e.g. 1-{self._page_count}")
        self.range_edit.setEnabled(False)
        form.addRow("Range:", self.range_edit)
        self.scope_box.currentIndexChanged.connect(self._on_scope)

        self.opacity_spin = QDoubleSpinBox()
        self.opacity_spin.setRange(5, 100)
        self.opacity_spin.setValue(25)
        self.opacity_spin.setSuffix(" %")
        form.addRow("Opacity:", self.opacity_spin)

        self.angle_spin = QDoubleSpinBox()
        self.angle_spin.setRange(-90, 90)
        self.angle_spin.setValue(45)
        self.angle_spin.setSuffix(" °")
        form.addRow("Angle:", self.angle_spin)

        self.size_spin = QDoubleSpinBox()
        self.size_spin.setRange(12, 144)
        self.size_spin.setValue(64)
        self.size_spin.setSuffix(" pt")
        form.addRow("Font size:", self.size_spin)

        layout.addLayout(form)
        layout.addWidget(
            QLabel("Watermarks are drawn into the page content and can be undone.")
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._current_page = current_page

    def _on_scope(self) -> None:
        self.range_edit.setEnabled(self.scope_box.currentData() == "range")

    def result_values(self) -> Dict[str, Any]:
        scope = self.scope_box.currentData()
        if scope == "all":
            pages = None
        elif scope == "current":
            pages = [self._current_page]
        else:
            pages = parse_page_range(self.range_edit.text(), self._page_count)
        return {
            "text": self.text_edit.text().strip(),
            "pages": pages,
            "opacity": self.opacity_spin.value() / 100.0,
            "angle": self.angle_spin.value(),
            "fontsize": self.size_spin.value(),
        }


class StampDialog(QDialog):
    """Place a preset/custom text stamp or an image stamp on the current page."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Stamp")
        self.resize(440, 260)
        self._image_path: Optional[str] = None

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.kind_box = QComboBox()
        self.kind_box.addItem("Text stamp", "text")
        self.kind_box.addItem("Image stamp", "image")
        self.kind_box.currentIndexChanged.connect(self._on_kind)
        form.addRow("Type:", self.kind_box)

        self.preset_box = QComboBox()
        self.preset_box.addItem("(custom)", "")
        for label in STAMP_PRESETS:
            self.preset_box.addItem(label, label)
        self.preset_box.currentIndexChanged.connect(self._on_preset)
        form.addRow("Preset:", self.preset_box)

        self.text_edit = QLineEdit("DRAFT")
        form.addRow("Text:", self.text_edit)

        image_row = QHBoxLayout()
        self.image_edit = QLineEdit()
        self.image_edit.setPlaceholderText("Choose a PNG / JPEG…")
        self.image_edit.setEnabled(False)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        image_row.addWidget(self.image_edit, 1)
        image_row.addWidget(browse)
        form.addRow("Image:", image_row)

        layout.addLayout(form)
        layout.addWidget(
            QLabel("Stamps are placed on the current page (centred text / lower-right image).")
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_kind(self) -> None:
        is_image = self.kind_box.currentData() == "image"
        self.image_edit.setEnabled(is_image)
        self.text_edit.setEnabled(not is_image)
        self.preset_box.setEnabled(not is_image)

    def _on_preset(self) -> None:
        value = self.preset_box.currentData()
        if value:
            self.text_edit.setText(str(value))

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose stamp image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp);;All Files (*.*)",
        )
        if path:
            self.image_edit.setText(path)
            self._image_path = path

    def result_values(self) -> Dict[str, Any]:
        kind = self.kind_box.currentData()
        return {
            "kind": kind,
            "text": self.text_edit.text().strip(),
            "image_path": self.image_edit.text().strip() or self._image_path,
        }
