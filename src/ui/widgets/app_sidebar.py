"""Left navigation shell — brand, WORK modes, and Open / Recents."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.constants import APP_ICON_PATH, APP_NAME, APP_VERSION
from src.ui.theme import color as theme_color

# Internal mode id → label shown in the sidebar.
WORK_MODES: Tuple[Tuple[str, str], ...] = (
    ("home", "Home"),
    ("markup", "Markup"),
    ("edit", "Edit"),
    ("organize", "Organize"),
    ("review", "Review"),
    ("view", "View"),
)

SIDEBAR_WIDTH = 220


class AppSidebar(QWidget):
    """Primary IA for the desktop shell — modes live here, not on a ribbon tab strip."""

    mode_changed = Signal(str)
    open_requested = Signal()
    recent_requested = Signal(str)

    def __init__(self, scheme: str = "light", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._scheme = scheme
        self._mode = "home"
        self._nav_buttons: dict[str, QToolButton] = {}
        self._recent_paths: List[str] = []
        self._document_modes_enabled = False

        self.setObjectName("appSidebar")
        self.setFixedWidth(SIDEBAR_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 16, 14, 16)
        root.setSpacing(4)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        self._mark = QLabel()
        self._mark.setFixedSize(28, 28)
        self._load_mark()
        brand_row.addWidget(self._mark)

        brand_col = QVBoxLayout()
        brand_col.setSpacing(0)
        self._brand = QLabel(APP_NAME)
        self._brand.setObjectName("sidebarBrand")
        brand_col.addWidget(self._brand)
        self._version = QLabel(f"v{APP_VERSION}")
        brand_col.addWidget(self._version)
        brand_row.addLayout(brand_col, 1)
        root.addLayout(brand_row)

        root.addSpacing(8)
        self._section = QLabel("WORK")
        self._section.setObjectName("sidebarSection")
        root.addWidget(self._section)

        for mode_id, label in WORK_MODES:
            btn = QToolButton()
            btn.setObjectName("sidebarNav")
            btn.setText(f"  {label}")
            btn.setCheckable(True)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setFixedHeight(36)
            btn.clicked.connect(lambda _checked=False, m=mode_id: self.set_mode(m))
            self._nav_buttons[mode_id] = btn
            root.addWidget(btn)

        root.addStretch(1)

        self._open_btn = QPushButton("Open PDF")
        self._open_btn.setObjectName("sidebarOpen")
        self._open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_btn.clicked.connect(self.open_requested.emit)
        root.addWidget(self._open_btn)

        self._recents_btn = QPushButton("Recents")
        self._recents_btn.setObjectName("sidebarGhost")
        self._recents_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._recents_btn.clicked.connect(self._show_recents_menu)
        root.addWidget(self._recents_btn)

        self._nav_buttons["home"].setChecked(True)
        self.apply_scheme(scheme)

    def _load_mark(self) -> None:
        if APP_ICON_PATH.is_file():
            pix = QPixmap(str(APP_ICON_PATH))
            if not pix.isNull():
                self._mark.setPixmap(
                    pix.scaled(
                        28,
                        28,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                return
        self._mark.setText("PDF")

    @property
    def current_mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str, *, emit: bool = True) -> None:
        if mode not in self._nav_buttons:
            return
        if mode != "home" and not self._document_modes_enabled:
            mode = "home"
        if mode == self._mode:
            if emit:
                self.mode_changed.emit(mode)
            return
        self._mode = mode
        for mid, btn in self._nav_buttons.items():
            btn.setChecked(mid == mode)
        if emit:
            self.mode_changed.emit(mode)

    def set_document_modes_enabled(self, enabled: bool) -> None:
        """When no PDF is open, keep Home selectable; grey out other modes."""
        self._document_modes_enabled = enabled
        for mode_id, btn in self._nav_buttons.items():
            if mode_id == "home":
                btn.setEnabled(True)
            else:
                btn.setEnabled(enabled)
        if not enabled and self._mode != "home":
            self.set_mode("home")

    def set_recent_paths(self, paths: Sequence[str]) -> None:
        self._recent_paths = [p for p in paths if p]
        self._recents_btn.setEnabled(bool(self._recent_paths))

    def _show_recents_menu(self) -> None:
        if not self._recent_paths:
            return
        menu = QMenu(self)
        for path_str in self._recent_paths:
            path = Path(path_str)
            action = menu.addAction(path.name)
            action.setToolTip(path_str)
            action.triggered.connect(
                lambda _checked=False, p=path_str: self.recent_requested.emit(p)
            )
        menu.exec(self._recents_btn.mapToGlobal(self._recents_btn.rect().bottomLeft()))

    def apply_scheme(self, scheme: str) -> None:
        self._scheme = scheme
        muted = theme_color("muted", scheme)
        self._version.setStyleSheet(
            f"color: {muted}; font-size: 11px; background: transparent;"
        )
        # Force QSS refresh for object-name rules.
        self.style().unpolish(self)
        self.style().polish(self)
