"""Left navigation shell — brand and document modes."""

from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.constants import APP_ICON_PATH, APP_NAME, APP_VERSION
from src.ui.icons import action_icon
from src.ui.theme import color as theme_color

_NAV_ICONS = {
    "home": "nav_home",
    "markup": "nav_markup",
    "edit": "nav_edit",
    "organize": "nav_organize",
    "review": "nav_review",
    "sign": "nav_sign",
    "view": "nav_view",
}

# Internal mode id → label shown in the sidebar.
WORK_MODES: Tuple[Tuple[str, str], ...] = (
    ("home", "Home"),
    ("markup", "Markup"),
    ("edit", "Edit"),
    ("organize", "Organize"),
    ("review", "Review"),
    ("sign", "Sign"),
    ("view", "View"),
)

SIDEBAR_WIDTH = 200


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
        self._document_modes_enabled = False

        self.setObjectName("appSidebar")
        self.setFixedWidth(SIDEBAR_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 20, 12, 16)
        root.setSpacing(2)

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
            btn.setText(label)
            btn.setCheckable(True)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            btn.setIconSize(QSize(18, 18))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setFixedHeight(34)
            btn.clicked.connect(lambda _checked=False, m=mode_id: self.set_mode(m))
            self._nav_buttons[mode_id] = btn
            root.addWidget(btn)

        root.addStretch(1)

        self._nav_buttons["home"].setChecked(True)
        self._refresh_nav_icons()
        self.apply_scheme(scheme)
        self.set_document_modes_enabled(False)

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
        """Show the work list only while a PDF is open."""
        self._document_modes_enabled = enabled
        self._section.setVisible(enabled)
        for mode_id, btn in self._nav_buttons.items():
            btn.setVisible(enabled)
            btn.setEnabled(enabled or mode_id == "home")
        if not enabled and self._mode != "home":
            self.set_mode("home")

    def set_recent_paths(self, paths) -> None:
        """Kept so callers can refresh recents without a sidebar list."""
        del paths

    def _refresh_nav_icons(self) -> None:
        for mode_id, btn in self._nav_buttons.items():
            icon_name = _NAV_ICONS.get(mode_id)
            if icon_name:
                btn.setIcon(action_icon(icon_name, self._scheme))

    def apply_scheme(self, scheme: str) -> None:
        self._scheme = scheme
        muted = theme_color("muted", scheme)
        self._version.setStyleSheet(
            f"color: {muted}; font-size: 11px; background: transparent;"
        )
        self._refresh_nav_icons()
        # Force QSS refresh for object-name rules.
        self.style().unpolish(self)
        self.style().polish(self)
