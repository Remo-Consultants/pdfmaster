"""Light studio theme inspired by a quiet document workspace.

Soft lavender canvas, white panels, and an indigo accent. The app uses
this light theme so the shell stays consistent.
"""

from __future__ import annotations

from typing import Dict

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPalette

from src.utils.logger import get_logger

logger = get_logger(__name__)

LIGHT = "light"
DARK = "dark"

# Soft corners, matching the studio cards.
RADIUS_PX = 12

# Every colour the UI needs, per scheme. Keeping them in one table makes
# it obvious when a scheme is missing a value.
COLORS: Dict[str, Dict[str, str]] = {
    LIGHT: {
        "window": "#f4f2fb",
        "window_text": "#1c1b2e",
        "base": "#ffffff",
        "alternate_base": "#f4f2fb",
        "text": "#1c1b2e",
        "button": "#ffffff",
        "button_text": "#1c1b2e",
        "bright_text": "#ffffff",
        "highlight": "#4f46e5",
        "highlight_text": "#ffffff",
        "disabled_text": "#a8a4bb",
        "border": "#e7e4f2",
        "canvas": "#f4f2fb",
        "page_border": "#e7e4f2",
        "shadow": "#c4bdd6",
        "icon": "#312e81",
        "icon_disabled": "#a8a4bb",
        "accent": "#4f46e5",
        "accent_soft": "#ece9fe",
        "panel": "#f7f6fc",
        "hover": "#f3f1fb",
        "checked": "#ece9fe",
        "paper": "#ffffff",
        "surface": "#ffffff",
        "muted": "#8b879c",
        "danger": "#dc2626",
        "success": "#059669",
        "sidebar": "#ffffff",
        "sidebar_text": "#4b5168",
        "sidebar_active": "#ece9fe",
        "sidebar_hover": "#f3f1fb",
        "topbar": "#ffffff",
        "cta": "#4f46e5",
        "cta_text": "#ffffff",
        "radius": str(RADIUS_PX),
    },
    DARK: {
        "window": "#07090c",
        "window_text": "#e7eef4",
        "base": "#0e1217",
        "alternate_base": "#12171d",
        "text": "#e7eef4",
        "button": "#12171d",
        "button_text": "#e7eef4",
        "bright_text": "#041016",
        "highlight": "#a78bfa",
        "highlight_text": "#1e1b4b",
        "disabled_text": "#5c6b7a",
        "border": "#1c242e",
        "canvas": "#0a0d11",
        "page_border": "#05070a",
        "shadow": "#000000",
        "icon": "#d5dee6",
        "icon_disabled": "#5c6b7a",
        "accent": "#a78bfa",
        "accent_soft": "#2e1065",
        "panel": "#10151b",
        "hover": "#171e26",
        "checked": "#2e1065",
        "paper": "#0e1217",
        "surface": "#0e1217",
        "muted": "#8b9aab",
        "danger": "#f87171",
        "success": "#34d399",
        "sidebar": "#07090c",
        "sidebar_text": "#b7c3cf",
        "sidebar_active": "#10151b",
        "sidebar_hover": "#10151b",
        "topbar": "#07090c",
        "cta": "#7c3aed",
        "cta_text": "#ffffff",
        "radius": str(RADIUS_PX),
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


def apply_app_font(app: QGuiApplication) -> None:
    """Set a calm Segoe UI Variable hierarchy for the whole app."""
    font = QFont("Segoe UI Variable")
    if not font.exactMatch():
        font = QFont("Segoe UI")
    font.setStyleHint(QFont.StyleHint.SansSerif)
    font.setPointSize(10)
    app.setFont(font)


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
    palette.setColor(role.Link, QColor(c["accent"]))

    for disabled in (role.Text, role.WindowText, role.ButtonText):
        palette.setColor(group.Disabled, disabled, QColor(c["disabled_text"]))
    return palette


def build_stylesheet(scheme: str) -> str:
    """Style the widgets whose defaults look out of place on Windows."""
    c = COLORS.get(scheme, COLORS[LIGHT])
    r = c.get("radius", str(RADIUS_PX))
    return f"""
    QMainWindow {{
        background: {c['window']};
    }}
    QToolBar {{
        background: {c['window']};
        border: 0px;
        border-bottom: 1px solid {c['border']};
        spacing: 2px;
        padding: 4px 8px;
    }}
    QToolBar::separator {{
        background: {c['border']};
        width: 1px;
        margin: 6px 6px;
    }}
    QToolButton {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: {r}px;
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
    QAbstractButton {{
        color: {c['button_text']};
    }}
    QPushButton,
    QDialogButtonBox QPushButton,
    QMessageBox QPushButton {{
        background: {c['button']};
        color: {c['button_text']};
        border: 1px solid {c['border']};
        border-radius: 10px;
        padding: 8px 16px;
        min-height: 18px;
    }}
    QPushButton:hover,
    QDialogButtonBox QPushButton:hover,
    QMessageBox QPushButton:hover {{
        background: {c['hover']};
        color: {c['button_text']};
    }}
    QPushButton:pressed,
    QDialogButtonBox QPushButton:pressed,
    QMessageBox QPushButton:pressed {{
        background: {c['checked']};
        color: {c['button_text']};
    }}
    QPushButton:disabled,
    QDialogButtonBox QPushButton:disabled,
    QMessageBox QPushButton:disabled {{
        color: {c['disabled_text']};
    }}
    QStatusBar {{
        background: {c['window']};
        border-top: 1px solid {c['border']};
        color: {c['muted']};
        padding: 2px 8px;
        min-height: 22px;
    }}
    QStatusBar::item {{ border: 0px; }}
    QDockWidget {{
        color: {c['window_text']};
        titlebar-close-icon: none;
        titlebar-normal-icon: none;
        font-weight: 500;
    }}
    QDockWidget::title {{
        background: {c['sidebar']};
        padding: 8px 12px;
        border-bottom: 1px solid {c['border']};
        text-align: left;
    }}
    QListWidget, QTreeWidget, QPlainTextEdit, QLineEdit, QSpinBox, QComboBox {{
        background: {c['base']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: {r}px;
        padding: 4px 8px;
        selection-background-color: {c['highlight']};
        selection-color: {c['highlight_text']};
    }}
    QListWidget {{ outline: 0; }}
    QListWidget::item {{ padding: 6px; border-radius: 8px; }}
    QListWidget::item:hover {{ background: {c['hover']}; }}
    QListWidget::item:selected {{
        background: {c['checked']};
        color: {c['text']};
        border: 1px solid {c['accent']};
    }}
    QListWidget#thumbnailPanel {{
        selection-background-color: transparent;
        selection-color: {c['text']};
        background: {c['panel']};
        border: none;
        border-radius: 0;
    }}
    QListWidget#thumbnailPanel::item {{
        border: 2px solid transparent;
        border-radius: 8px;
        margin: 2px;
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
        height: 3px;
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
    QMenuBar {{
        background: {c['window']};
        color: {c['window_text']};
        padding: 2px 4px;
        border-bottom: 1px solid {c['border']};
    }}
    QMenuBar::item {{
        color: {c['window_text']};
        padding: 4px 10px;
        border-radius: 8px;
    }}
    QMenuBar::item:selected {{ background: {c['hover']}; }}
    QMenu {{
        background: {c['base']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: {r}px;
        padding: 4px;
    }}
    QMenu::item {{
        color: {c['text']};
        padding: 6px 28px 6px 12px;
        border-radius: 8px;
    }}
    QMenu::item:selected {{
        background: {c['highlight']};
        color: {c['highlight_text']};
    }}
    QMenu::separator {{
        height: 1px;
        background: {c['border']};
        margin: 4px 8px;
    }}
    QTabWidget#documentTabs::pane {{
        border: none;
        background: {c['canvas']};
    }}
    QTabWidget#documentTabs QTabBar::tab {{
        background: transparent;
        color: {c['muted']};
        padding: 8px 16px;
        margin-right: 4px;
        border: none;
        border-radius: 10px;
    }}
    QTabWidget#documentTabs QTabBar::tab:hover {{
        background: {c['hover']};
        color: {c['text']};
    }}
    QTabWidget#documentTabs QTabBar::tab:selected {{
        color: {c['accent']};
        background: transparent;
        font-weight: 600;
        border: none;
        border-bottom: 2px solid {c['accent']};
        border-radius: 0;
    }}
    QWidget#appSidebar {{
        background: {c['sidebar']};
        border-right: 1px solid {c['border']};
    }}
    QLabel#sidebarBrand {{
        color: {c['window_text']};
        font-weight: 600;
        font-size: 14px;
        letter-spacing: 0.04em;
        background: transparent;
    }}
    QLabel#sidebarSection {{
        color: {c['muted']};
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 0.16em;
        background: transparent;
        padding: 18px 10px 4px 10px;
    }}
    QToolButton#sidebarNav {{
        background: transparent;
        color: {c['sidebar_text']};
        border: none;
        border-radius: 10px;
        padding: 8px 12px;
        text-align: left;
        font-weight: 500;
    }}
    QToolButton#sidebarNav:hover {{
        background: {c['sidebar_hover']};
        color: {c['window_text']};
    }}
    QToolButton#sidebarNav:checked {{
        background: {c['sidebar_active']};
        color: {c['accent']};
        font-weight: 600;
    }}
    QWidget#appTopBar {{
        background: {c['topbar']};
        border-bottom: 1px solid {c['border']};
    }}
    QLineEdit#topSearch {{
        background: {c['panel']};
        border: 1px solid {c['border']};
        border-radius: 12px;
        padding: 8px 14px;
        min-height: 18px;
    }}
    QLineEdit#topSearch:focus {{
        border: 1px solid {c['accent']};
    }}
    QLabel#topDocTitle {{
        color: {c['window_text']};
        font-weight: 600;
        font-size: 13px;
        background: transparent;
        padding-right: 8px;
    }}
    QPushButton#primaryCta, QPushButton#sidebarOpen, QPushButton#welcomePrimary {{
        background: {c['cta']};
        color: {c['cta_text']};
        border: none;
        border-radius: 10px;
        padding: 10px 18px;
        font-weight: 600;
    }}
    QPushButton#primaryCta:hover, QPushButton#sidebarOpen:hover, QPushButton#welcomePrimary:hover {{
        background: #4338ca;
        color: {c['cta_text']};
    }}
    QPushButton#sidebarGhost, QPushButton#welcomeGhost {{
        background: transparent;
        color: {c['sidebar_text']};
        border: none;
        border-radius: {r}px;
        padding: 6px 10px;
        font-weight: 500;
    }}
    QPushButton#sidebarGhost:hover, QPushButton#welcomeGhost:hover {{
        color: {c['window_text']};
        background: {c['sidebar_hover']};
    }}
    QFrame#welcomeDropZone {{
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 16px;
    }}
    QFrame#welcomeDropZone[dragActive="true"] {{
        border-color: {c['accent']};
        background: {c['accent_soft']};
    }}
    """


def apply_theme(app: QGuiApplication, scheme: str) -> None:
    """Apply the palette and stylesheet for ``scheme`` to the application."""
    apply_app_font(app)
    app.setPalette(build_palette(scheme))
    app.setStyleSheet(build_stylesheet(scheme))
    logger.info("Applied %s theme", scheme)
