"""Dialog for filling in PDF form fields."""

from __future__ import annotations

from typing import Any, Dict, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.constants import APP_NAME
from src.core.document import Document
from src.processors.forms import CHECKBOX, COMBOBOX, LISTBOX, FormProcessor
from src.utils.exceptions import PDFMasterException
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FormDialog(QDialog):
    """Shows every fillable field with an editor appropriate to its type."""

    def __init__(self, document: Document, parent=None) -> None:
        super().__init__(parent)
        self._document = document
        self._editors: Dict[str, QWidget] = {}
        self._fields: List[Dict[str, Any]] = FormProcessor.list_fields(document)

        self.setWindowTitle("Fill Form")
        self.resize(560, 520)

        layout = QVBoxLayout(self)
        editable = [f for f in self._fields if f["editable"] and f["name"]]
        layout.addWidget(
            QLabel(f"{len(editable)} fillable field(s) found in this document.")
        )

        container = QWidget()
        form = QFormLayout(container)
        for field in editable:
            editor = self._build_editor(field)
            self._editors[field["name"]] = editor
            label = field["label"] or field["name"]
            if field["required"]:
                label += " *"
            if field["readonly"]:
                label += " (read-only)"
                editor.setEnabled(False)
            form.addRow(f"{label}  [page {field['page'] + 1}]", editor)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        layout.addWidget(scroll, stretch=1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_editor(self, field: Dict[str, Any]) -> QWidget:
        kind = field["type"]
        value = field["value"]

        if kind == CHECKBOX:
            box = QCheckBox()
            box.setChecked(str(value).strip().lower() not in ("off", "false", "none", ""))
            return box

        if kind in (COMBOBOX, LISTBOX):
            combo = QComboBox()
            combo.addItems(field["options"])
            combo.setEditable(kind == COMBOBOX and not field["options"])
            if value:
                index = combo.findText(str(value))
                if index >= 0:
                    combo.setCurrentIndex(index)
            return combo

        line = QLineEdit(str(value or ""))
        return line

    def collect_values(self) -> Dict[str, Any]:
        """Read the current editor state into a name -> value mapping."""
        values: Dict[str, Any] = {}
        for name, editor in self._editors.items():
            if isinstance(editor, QCheckBox):
                values[name] = editor.isChecked()
            elif isinstance(editor, QComboBox):
                values[name] = editor.currentText()
            elif isinstance(editor, QLineEdit):
                values[name] = editor.text()
        return values

    def _save(self) -> None:
        try:
            count = FormProcessor.set_values(self._document, self.collect_values())
        except PDFMasterException as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))
            return
        self.updated_count = count
        logger.info("Form dialog saved %s field(s)", count)
        self.accept()
