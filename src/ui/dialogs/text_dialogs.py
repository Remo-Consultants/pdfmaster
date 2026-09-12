"""Dialogs for adding, replacing, and searching text."""

from __future__ import annotations

from typing import Any, Dict, Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)

from src.constants import (
    ANNOT_COLORS,
    DEFAULT_FONT,
    DEFAULT_FONT_SIZE,
    MIN_FONT_SIZE,
    STANDARD_FONTS,
)


class _TextStyleDialog(QDialog):
    """Shared layout for dialogs that collect text plus font settings."""

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(480, 340)
        self._layout = QVBoxLayout(self)
        self._form = QFormLayout()

    def _add_style_controls(
        self, size: float = DEFAULT_FONT_SIZE, with_color: bool = True
    ) -> None:
        self.font_box = QComboBox()
        for code, label in STANDARD_FONTS.items():
            self.font_box.addItem(label, code)
        self._form.addRow("Font", self.font_box)

        self.size_box = QDoubleSpinBox()
        self.size_box.setRange(MIN_FONT_SIZE, 96.0)
        self.size_box.setSingleStep(1.0)
        self.size_box.setValue(size)
        self._form.addRow("Size", self.size_box)

        if with_color:
            self.color_box = QComboBox()
            for name in ANNOT_COLORS:
                self.color_box.addItem(name.title(), name)
            self.color_box.setCurrentText("Black")
            self._form.addRow("Colour", self.color_box)

    def _add_buttons(self, accept_label: str = "Apply") -> None:
        self._layout.addLayout(self._form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(accept_label)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._layout.addWidget(buttons)

    def style_values(self) -> Dict[str, Any]:
        return {
            "font": self.font_box.currentData() or DEFAULT_FONT,
            "size": float(self.size_box.value()),
            "color": self.color_box.currentData() if hasattr(self, "color_box") else None,
        }


class AddTextDialog(_TextStyleDialog):
    """Collects the text and style for a new text box."""

    def __init__(self, parent=None) -> None:
        super().__init__("Add Text", parent)
        self._layout.addWidget(QLabel("Text to place in the box you drew:"))
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Type the text to add...")
        self._layout.addWidget(self.text_edit, stretch=1)
        self._add_style_controls()
        self._add_buttons("Add Text")

    def result_values(self) -> Dict[str, Any]:
        values = self.style_values()
        values["text"] = self.text_edit.toPlainText()
        return values


class ReplaceTextDialog(_TextStyleDialog):
    """Shows the text found in the selection and collects its replacement."""

    def __init__(self, original: str, size: float = DEFAULT_FONT_SIZE, parent=None) -> None:
        super().__init__("Edit Text", parent)
        self._layout.addWidget(QLabel("Existing text in the selected area:"))
        existing = QPlainTextEdit(original)
        existing.setReadOnly(True)
        existing.setMaximumHeight(80)
        self._layout.addWidget(existing)

        self._layout.addWidget(QLabel("Replace with:"))
        self.text_edit = QPlainTextEdit(original)
        self._layout.addWidget(self.text_edit, stretch=1)

        note = QLabel(
            "Note: PDFs store glyphs, not editable sentences. Longer text is "
            "shrunk to fit, and a similar font is substituted when the "
            "original is not embedded."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #888;")
        self._layout.addWidget(note)

        self.keep_style = QCheckBox("Match the original font and size")
        self.keep_style.setChecked(True)
        self.keep_style.toggled.connect(self._toggle_style)
        self._layout.addWidget(self.keep_style)

        self._add_style_controls(size=size)
        self._add_buttons("Replace")
        self._toggle_style(True)

    def _toggle_style(self, keep: bool) -> None:
        for widget in (self.font_box, self.size_box, self.color_box):
            widget.setEnabled(not keep)

    def result_values(self) -> Dict[str, Any]:
        if self.keep_style.isChecked():
            return {"text": self.text_edit.toPlainText(), "font": None,
                    "size": None, "color": None}
        values = self.style_values()
        values["text"] = self.text_edit.toPlainText()
        return values


class FindReplaceDialog(QDialog):
    """Search and replace text across the current page or the whole document."""

    def __init__(self, page_count: int, current_page: int, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Find and Replace")
        self.resize(460, 200)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Text to find")
        form.addRow("Find", self.search_edit)

        self.replace_edit = QLineEdit()
        self.replace_edit.setPlaceholderText("Replacement text")
        form.addRow("Replace with", self.replace_edit)

        self.scope_box = QComboBox()
        self.scope_box.addItem(f"Current page ({current_page + 1})", "current")
        self.scope_box.addItem(f"All {page_count} pages", "all")
        form.addRow("Scope", self.scope_box)

        layout.addLayout(form)

        warning = QLabel(
            "Replacements are applied by redrawing the text, so spacing may "
            "shift slightly."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color: #888;")
        layout.addWidget(warning)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Replace All")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def result_values(self) -> Dict[str, Any]:
        return {
            "search": self.search_edit.text(),
            "replacement": self.replace_edit.text(),
            "all_pages": self.scope_box.currentData() == "all",
        }


class StickyNoteDialog(QDialog):
    """Collects the body of a sticky note."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Note")
        self.resize(420, 240)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Note text:"))
        self.text_edit = QPlainTextEdit()
        layout.addWidget(self.text_edit, stretch=1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def text(self) -> str:
        return self.text_edit.toPlainText()
