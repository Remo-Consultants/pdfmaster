"""Home screen and the recent-files pane."""

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
        self._mark.setFixedSize(48, 48)
        self._load_mark()
        card_layout.addWidget(self._mark, 0, Qt.AlignmentFlag.AlignHCenter)

        self._brand = QLabel(APP_NAME)
        brand_font = QFont(self.font())
        brand_font.setPointSize(22)
        brand_font.setWeight(QFont.Weight.DemiBold)
        brand_font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 98)
        self._brand.setFont(brand_font)
        self._brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self._brand)

        self._tagline = QLabel("The desk, not the cloud.")
        self._tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._tagline.setWordWrap(True)
        card_layout.addWidget(self._tagline)

        self._version = QLabel(f"Version {APP_VERSION}")
        self._version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self._version)

        card_layout.addSpacing(4)

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

        root.addStretch(2)

        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._fade = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade.setDuration(320)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.apply_scheme(scheme)

    def showEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().showEvent(event)
        self._opacity.setOpacity(0.0)
        self._fade.stop()
        self._fade.start()

    def _load_mark(self) -> None:
        if APP_ICON_PATH.is_file():
            pix = QPixmap(str(APP_ICON_PATH))
            if not pix.isNull():
                self._mark.setPixmap(
                    pix.scaled(
                        48,
                        48,
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
        window = theme_color("window", scheme)
        self.setStyleSheet(f"WelcomeHome {{ background: {window}; }}")
        self._brand.setStyleSheet(f"color: {text}; background: transparent;")
        self._tagline.setStyleSheet(
            f"color: {muted}; font-size: 14px; background: transparent;"
        )
        accent = theme_color("accent", scheme)
        self._version.setStyleSheet(
            f"color: {accent}; font-size: 13px; font-weight: 600; background: transparent;"
        )
        self._hint.setStyleSheet(
            f"color: {muted}; font-size: 12px; background: transparent;"
        )
        # Force QSS property refresh on the drop zone.
        self._card.style().unpolish(self._card)
        self._card.style().polish(self._card)

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


class RecentFilesPane(QWidget):
    """Recent PDFs, shown in the right dock on the home screen."""

    path_requested = Signal(str)

    def __init__(self, scheme: str = "light", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._scheme = scheme
        self.setObjectName("recentPane")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self._empty = QLabel("No recent files yet")
        self._empty.setWordWrap(True)
        layout.addWidget(self._empty)

        self._list = QListWidget()
        self._list.setObjectName("welcomeRecent")
        self._list.setFrameShape(QFrame.Shape.NoFrame)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.itemActivated.connect(self._on_activated)
        self._list.itemClicked.connect(self._on_activated)
        layout.addWidget(self._list, 1)

        self.apply_scheme(scheme)
        self.refresh()

    def apply_scheme(self, scheme: str) -> None:
        self._scheme = scheme
        muted = theme_color("muted", scheme)
        self._empty.setStyleSheet(f"color: {muted}; font-size: 12px; background: transparent;")

    def refresh(self) -> None:
        self._list.clear()
        try:
            recent = FileHandler.get_recent_files(CONFIG_DIR)[:MAX_RECENT_FILES]
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not load recent files: %s", exc)
            recent = []
        if not recent:
            self._list.hide()
            self._empty.show()
            return
        self._empty.hide()
        self._list.show()
        for path_str in recent:
            path = Path(path_str)
            item = QListWidgetItem(path.name)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setToolTip(str(path))
            if APP_ICON_PATH.is_file():
                item.setIcon(QIcon(str(APP_ICON_PATH)))
            self._list.addItem(item)

    def _on_activated(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.path_requested.emit(str(path))
