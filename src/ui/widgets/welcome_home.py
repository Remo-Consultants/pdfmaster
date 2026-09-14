"""Brand-forward empty home — drop zone, open CTA, and recent files."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    Signal,
)
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.constants import APP_ICON_PATH, APP_NAME, APP_VERSION, CONFIG_DIR, MAX_RECENT_FILES
from src.ui.theme import color as theme_color
from src.utils.file_handler import FileHandler
from src.utils.logger import get_logger

logger = get_logger(__name__)


class WelcomeHome(QWidget):
    """Shown when no PDF is open — the product's first impression."""

    open_requested = Signal()
    path_requested = Signal(str)

    def __init__(self, scheme: str = "light", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._scheme = scheme
        self.setObjectName("welcomeHome")
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        root = QVBoxLayout(self)
        root.setContentsMargins(48, 40, 48, 40)
        root.setSpacing(0)
        root.addStretch(1)

        self._card = QFrame()
        self._card.setObjectName("welcomeDropZone")
        self._card.setProperty("dragActive", False)
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(40, 36, 40, 36)
        card_layout.setSpacing(14)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self._mark = QLabel()
        self._mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._mark.setFixedSize(72, 72)
        self._load_mark()
        card_layout.addWidget(self._mark, 0, Qt.AlignmentFlag.AlignHCenter)

        self._brand = QLabel(APP_NAME)
        brand_font = QFont(self.font())
        brand_font.setPointSize(28)
        brand_font.setWeight(QFont.Weight.DemiBold)
        brand_font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 98)
        self._brand.setFont(brand_font)
        self._brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self._brand)

        self._tagline = QLabel("Open a PDF. Work stays on your machine.")
        self._tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._tagline.setWordWrap(True)
        card_layout.addWidget(self._tagline)

        self._version = QLabel(f"Version {APP_VERSION}")
        self._version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self._version)

        self._features = QLabel(
            "Review tab — Compare · PDF/A · Search · Batch  ·  Markup — Watermark · Stamp"
        )
        self._features.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._features.setWordWrap(True)
        card_layout.addWidget(self._features)

        card_layout.addSpacing(8)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self._open_btn = QPushButton("Open PDF")
        self._open_btn.setObjectName("welcomePrimary")
        self._open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_btn.clicked.connect(self.open_requested.emit)
        actions.addWidget(self._open_btn)

        self._hint = QLabel("or drop a file here  ·  Ctrl+O")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addLayout(actions)
        card_layout.addWidget(self._hint)

        root.addWidget(self._card, 0, Qt.AlignmentFlag.AlignHCenter)
        self._card.setMinimumWidth(420)
        self._card.setMaximumWidth(560)

        root.addSpacing(28)

        self._recent_label = QLabel("Recent")
        recent_font = QFont(self.font())
        recent_font.setPointSize(11)
        recent_font.setWeight(QFont.Weight.DemiBold)
        self._recent_label.setFont(recent_font)
        self._recent_label.setMaximumWidth(560)
        root.addWidget(self._recent_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self._recent_list = QListWidget()
        self._recent_list.setObjectName("welcomeRecent")
        self._recent_list.setMaximumWidth(560)
        self._recent_list.setMinimumHeight(120)
        self._recent_list.setMaximumHeight(200)
        self._recent_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._recent_list.itemActivated.connect(self._on_recent_activated)
        self._recent_list.itemClicked.connect(self._on_recent_activated)
        root.addWidget(self._recent_list, 0, Qt.AlignmentFlag.AlignHCenter)

        self._empty_recent = QLabel("No recent files yet")
        self._empty_recent.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_recent.setMaximumWidth(560)
        root.addWidget(self._empty_recent, 0, Qt.AlignmentFlag.AlignHCenter)

        root.addStretch(2)

        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._fade = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade.setDuration(320)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.apply_scheme(scheme)
        self.refresh_recents()

    def showEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().showEvent(event)
        self.refresh_recents()
        self._opacity.setOpacity(0.0)
        self._fade.stop()
        self._fade.start()

    def _load_mark(self) -> None:
        if APP_ICON_PATH.is_file():
            pix = QPixmap(str(APP_ICON_PATH))
            if not pix.isNull():
                self._mark.setPixmap(
                    pix.scaled(
                        72,
                        72,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                return
        self._mark.setText("PDF")

    def apply_scheme(self, scheme: str) -> None:
        """Retheme labels for the current scheme."""
        self._scheme = scheme
        text = theme_color("window_text", scheme)
        muted = theme_color("muted", scheme)
        surface = theme_color("surface", scheme)
        self.setStyleSheet(f"WelcomeHome {{ background: {surface}; }}")
        self._brand.setStyleSheet(f"color: {text}; background: transparent;")
        self._tagline.setStyleSheet(
            f"color: {muted}; font-size: 14px; background: transparent;"
        )
        accent = theme_color("accent", scheme)
        self._version.setStyleSheet(
            f"color: {accent}; font-size: 13px; font-weight: 600; background: transparent;"
        )
        self._features.setStyleSheet(
            f"color: {muted}; font-size: 12px; background: transparent; padding: 0 8px;"
        )
        self._hint.setStyleSheet(
            f"color: {muted}; font-size: 12px; background: transparent;"
        )
        self._recent_label.setStyleSheet(
            f"color: {text}; background: transparent; margin-top: 4px;"
        )
        self._empty_recent.setStyleSheet(
            f"color: {muted}; font-size: 12px; background: transparent;"
        )
        # Force QSS property refresh on the drop zone.
        self._card.style().unpolish(self._card)
        self._card.style().polish(self._card)

    def refresh_recents(self) -> None:
        """Reload the recent-files list from disk."""
        self._recent_list.clear()
        try:
            recent = FileHandler.get_recent_files(CONFIG_DIR)[:MAX_RECENT_FILES]
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not load recent files: %s", exc)
            recent = []

        if not recent:
            self._recent_list.hide()
            self._empty_recent.show()
            return

        self._empty_recent.hide()
        self._recent_list.show()
        for path_str in recent:
            path = Path(path_str)
            item = QListWidgetItem(path.name)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setToolTip(str(path))
            if APP_ICON_PATH.is_file():
                item.setIcon(QIcon(str(APP_ICON_PATH)))
            self._recent_list.addItem(item)

    def _on_recent_activated(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.path_requested.emit(str(path))

    # ------------------------------------------------------------------
    # Drag and drop
    # ------------------------------------------------------------------
    def _set_drag_active(self, active: bool) -> None:
        self._card.setProperty("dragActive", active)
        self._card.style().unpolish(self._card)
        self._card.style().polish(self._card)

    @staticmethod
    def _pdf_paths_from_mime(event) -> List[str]:
        paths: List[str] = []
        mime = event.mimeData()
        if mime is None or not mime.hasUrls():
            return paths
        for url in mime.urls():
            local = url.toLocalFile()
            if local and local.lower().endswith(".pdf"):
                paths.append(local)
        return paths

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if self._pdf_paths_from_mime(event):
            event.acceptProposedAction()
            self._set_drag_active(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self._set_drag_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        self._set_drag_active(False)
        paths = self._pdf_paths_from_mime(event)
        if not paths:
            event.ignore()
            return
        event.acceptProposedAction()
        self.path_requested.emit(paths[0])
