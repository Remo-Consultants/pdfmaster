"""Top chrome — search field and primary Open CTA."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QWidget,
)


class AppTopBar(QWidget):
    """Document name and search. Open lives on the sidebar, once."""

    search_submitted = Signal(str)
    open_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("appTopBar")
        self.setFixedHeight(52)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._full_name = ""

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(16)

        self._title = QLabel()
        self._title.setObjectName("topDocTitle")
        self._title.hide()
        layout.addWidget(self._title, 0)

        self._search = QLineEdit()
        self._search.setObjectName("topSearch")
        self._search.setPlaceholderText("Search this document")
        self._search.setClearButtonEnabled(True)
        self._search.setMaximumWidth(420)
        self._search.returnPressed.connect(self._emit_search)
        layout.addWidget(self._search, 0)
        layout.addStretch(1)

    def _emit_search(self) -> None:
        text = self._search.text().strip()
        if text:
            self.search_submitted.emit(text)

    def set_document_name(self, name: str) -> None:
        """Show the open file name. Empty hides the title."""
        self._full_name = name or ""
        if not self._full_name:
            self._title.clear()
            self._title.hide()
            return
        self._title.show()
        self._title.setToolTip(self._full_name)
        width = 320
        self._title.setText(
            self._title.fontMetrics().elidedText(
                self._full_name, Qt.TextElideMode.ElideMiddle, width
            )
        )

    def set_search_enabled(self, enabled: bool) -> None:
        self._search.setEnabled(enabled)
        if not enabled:
            self._search.clear()

    def focus_search(self) -> None:
        self._search.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self._search.selectAll()
