"""Light/dark theming that follows the Windows colour scheme.

Qt 6.5+ reports the OS preference through ``QStyleHints.colorScheme()``
and emits a signal when the user changes it, so PDFMaster can follow
along without a restart.
"""

from __future__ import annotations

from typing import Dict

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette

from src.utils.logger import get_logger

logger = get_logger(__name__)

LIGHT = "light"
DARK = "dark"

# Every colour the UI needs, per scheme. Keeping them in one table makes
# it obvious when a scheme is missing a value.
COLORS: Dict[str, Dict[str, str]] = {
    LIGHT: {
        "window": "#f3f3f3",
        "window_text": "#1a1a1a",
        "base": "#ffffff",
        "alternate_base": "#f7f7f7",
        "text": "#1a1a1a",
        "button": "#fbfbfb",
        "button_text": "#1a1a1a",
        "bright_text": "#ffffff",
        "highlight": "#0067c0",
        "highlight_text": "#ffffff",
        "disabled_text": "#9a9a9a",
        "border": "#d6d6d6",
        # The viewer canvas is deliberately a mid grey, not white, so the
        # page edges stay visible against it.
        "canvas": "#7a7a7a",
        "page_border": "#5c5c5c",
        "shadow": "#4a4a4a",
        "icon": "#2b2b2b",
        "icon_disabled": "#a8a8a8",
        "accent": "#0067c0",
        "panel": "#fafafa",
        "hover": "#e6e6e6",
        "checked": "#cfe4f7",
    },
    DARK: {
        "window": "#202020",
        "window_text": "#eaeaea",
        "base": "#2b2b2b",
        "alternate_base": "#323232",
        "text": "#eaeaea",
        "button": "#2d2d2d",
        "button_text": "#eaeaea",
        "bright_text": "#ffffff",
        "highlight": "#4cc2ff",
        "highlight_text": "#0a0a0a",
        "disabled_text": "#9a9a9a",
        "border": "#3d3d3d",
        "canvas": "#1a1a1a",
        "page_border": "#000000",
        "shadow": "#0d0d0d",
        "icon": "#e4e4e4",
        "icon_disabled": "#8a8a8a",
        "accent": "#4cc2ff",
        "panel": "#252525",
        "hover": "#383838",
        "checked": "#15466b",
    },
}


def detect_scheme() -> str:
    """Return ``"dark"`` or ``"light"`` based on the OS preference."""
    hints = QGuiApplication.styleHints()
    scheme = getattr(hints, "colorScheme", None)
    if scheme is None:  # Qt older than 6.5
        return LIGHT
    try:
        return DARK if scheme() == Qt.ColorScheme.Dark else LIGHT
    except Exception as exc:  # noqa: BLE001 - never block startup on theming
        logger.debug("Could not read the OS colour scheme: %s", exc)
        return LIGHT


def color(name: str, scheme: str) -> str:
    """Look up a themed colour, falling back to the light value."""
    return COLORS.get(scheme, COLORS[LIGHT]).get(name, COLORS[LIGHT][name])


def build_palette(scheme: str) -> QPalette:
    """Build the QPalette for a scheme."""
    c = COLORS.get(scheme, COLORS[LIGHT])
    palette = QPalette()
    role = QPalette.ColorRole
    group = QPalette.ColorGroup

    palette.setColor(role.Window, QColor(c["window"]))
    palette.setColor(role.WindowText, QColor(c["window_text"]))
    palette.setColor(role.Base, QColor(c["base"]))
    palette.setColor(role.AlternateBase, QColor(c["alternate_base"]))
    palette.setColor(role.Text, QColor(c["text"]))
    palette.setColor(role.Button, QColor(c["button"]))
    palette.setColor(role.ButtonText, QColor(c["button_text"]))
    palette.setColor(role.BrightText, QColor(c["bright_text"]))
    palette.setColor(role.Highlight, QColor(c["highlight"]))
    palette.setColor(role.HighlightedText, QColor(c["highlight_text"]))
    palette.setColor(role.ToolTipBase, QColor(c["base"]))
    palette.setColor(role.ToolTipText, QColor(c["text"]))
    palette.setColor(role.PlaceholderText, QColor(c["disabled_text"]))

    for disabled in (role.Text, role.WindowText, role.ButtonText):
        palette.setColor(group.Disabled, disabled, QColor(c["disabled_text"]))
    return palette


def build_stylesheet(scheme: str) -> str:
    """Style the widgets whose defaults look out of place on Windows."""
    c = COLORS.get(scheme, COLORS[LIGHT])
    return f"""
    QToolBar {{
        background: {c['window']};
        border: 0px;
        border-bottom: 1px solid {c['border']};
        spacing: 2px;
        padding: 3px 6px;
    }}
    QToolBar::separator {{
        background: {c['border']};
        width: 1px;
        margin: 4px 5px;
    }}
    QToolButton {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: 4px;
        padding: 4px;
        color: {c['button_text']};
    }}
    QToolButton:hover {{
        background: {c['hover']};
        border-color: {c['border']};
    }}
    QToolButton:checked {{
        background: {c['checked']};
        border-color: {c['accent']};
    }}
    QToolButton:disabled {{ color: {c['disabled_text']}; }}
    QStatusBar {{
        background: {c['window']};
        border-top: 1px solid {c['border']};
        color: {c['window_text']};
    }}
    QStatusBar::item {{ border: 0px; }}
    QDockWidget {{
        color: {c['window_text']};
        titlebar-close-icon: none;
        titlebar-normal-icon: none;
    }}
    QDockWidget::title {{
        background: {c['panel']};
        padding: 6px 8px;
        border-bottom: 1px solid {c['border']};
    }}
    QListWidget, QTreeWidget, QPlainTextEdit, QLineEdit, QSpinBox, QComboBox {{
        background: {c['base']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        selection-background-color: {c['highlight']};
        selection-color: {c['highlight_text']};
    }}
    QListWidget {{ outline: 0; }}
    QListWidget::item {{ padding: 3px; border-radius: 4px; }}
    QListWidget::item:hover {{ background: {c['hover']}; }}
    QListWidget::item:selected {{
        background: {c['checked']};
        color: {c['text']};
        border: 1px solid {c['accent']};
    }}
    /* Page thumbnails: outline the current page rather than tinting it,
       so the preview image stays readable. */
    QListWidget#thumbnailPanel {{
        selection-background-color: transparent;
        selection-color: {c['text']};
        background: {c['panel']};
    }}
    QListWidget#thumbnailPanel::item {{
        border: 2px solid transparent;
        border-radius: 3px;
        margin: 1px;
    }}
    QListWidget#thumbnailPanel::item:hover {{
        background: transparent;
        border-color: {c['border']};
    }}
    QListWidget#thumbnailPanel::item:selected {{
        background: transparent;
        border-color: {c['accent']};
    }}
    QScrollArea {{ border: 0px; }}
    QSlider::groove:horizontal {{
        height: 4px;
        background: {c['border']};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {c['accent']};
        width: 12px;
        height: 12px;
        margin: -5px 0;
        border-radius: 6px;
    }}
    QMenuBar {{ background: {c['window']}; color: {c['window_text']}; }}
    QMenuBar::item:selected {{ background: {c['hover']}; }}
    QMenu {{
        background: {c['base']};
        color: {c['text']};
        border: 1px solid {c['border']};
    }}
    QMenu::item:selected {{ background: {c['highlight']}; color: {c['highlight_text']}; }}
    QMenu::separator {{ height: 1px; background: {c['border']}; margin: 4px 8px; }}
    """


def apply_theme(app: QGuiApplication, scheme: str) -> None:
    """Apply the palette and stylesheet for ``scheme`` to the application."""
    app.setPalette(build_palette(scheme))
    app.setStyleSheet(build_stylesheet(scheme))
    logger.info("Applied %s theme", scheme)
