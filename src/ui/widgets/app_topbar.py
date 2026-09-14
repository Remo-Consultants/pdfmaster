"""Top chrome — search field and primary Open CTA."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)


class AppTopBar(QWidget):
    """Document search + Open PDF, matching the reference's calm top chrome."""

    search_submitted = Signal(str)
    open_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("appTopBar")
        self.setFixedHeight(56)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        self._search = QLineEdit()
        self._search.setObjectName("topSearch")
        self._search.setPlaceholderText("Search document…  Ctrl+F")
        self._search.setClearButtonEnabled(True)
        self._search.returnPressed.connect(self._emit_search)
        layout.addWidget(self._search, 1)

        self._open = QPushButton("Open PDF")
        self._open.setObjectName("primaryCta")
        self._open.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open.clicked.connect(self.open_requested.emit)
        layout.addWidget(self._open)

    def _emit_search(self) -> None:
        text = self._search.text().strip()
        if text:
            self.search_submitted.emit(text)

    def set_search_enabled(self, enabled: bool) -> None:
        self._search.setEnabled(enabled)
        if not enabled:
            self._search.clear()

    def focus_search(self) -> None:
        self._search.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self._search.selectAll()
