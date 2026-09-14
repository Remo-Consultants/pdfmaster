"""Quiet paper-studio theming that follows the Windows colour scheme.

Brand accent matches the product site (teal). Qt 6.5+ reports the OS
preference through ``QStyleHints.colorScheme()`` so PDFMaster can follow
along without a restart.
"""

from __future__ import annotations

from typing import Dict

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPalette

from src.utils.logger import get_logger

logger = get_logger(__name__)

LIGHT = "light"
DARK = "dark"

# Corner radius used across QSS (stored as a digit string for the token table).
RADIUS_PX = 12

# Every colour the UI needs, per scheme. Keeping them in one table makes
# it obvious when a scheme is missing a value.
COLORS: Dict[str, Dict[str, str]] = {
    LIGHT: {
        "window": "#f1f4f7",
        "window_text": "#0f172a",
        "base": "#ffffff",
        "alternate_base": "#f1f5f9",
        "text": "#0f172a",
        "button": "#ffffff",
        "button_text": "#0f172a",
        "bright_text": "#ffffff",
        "highlight": "#0f766e",
        "highlight_text": "#ffffff",
        "disabled_text": "#94a3b8",
        "border": "#e2e8f0",
        "canvas": "#e6ebf0",
        "page_border": "#cbd5e1",
        "shadow": "#64748b",
        "icon": "#1e293b",
        "icon_disabled": "#94a3b8",
        "accent": "#0f766e",
        "accent_soft": "#ccfbf1",
        "panel": "#f8fafc",
        "hover": "#eef2f6",
        "checked": "#ccfbf1",
        "paper": "#ffffff",
        "surface": "#ffffff",
        "muted": "#64748b",
        "danger": "#dc2626",
        "success": "#059669",
        "sidebar": "#eef1f5",
        "sidebar_text": "#334155",
        "sidebar_active": "#ffffff",
        "sidebar_hover": "#e4e9ef",
        "topbar": "#ffffff",
        "cta": "#0f172a",
        "cta_text": "#ffffff",
        "radius": str(RADIUS_PX),
    },
    DARK: {
        "window": "#0f1419",
        "window_text": "#e8eef2",
        "base": "#1a222c",
        "alternate_base": "#222b36",
        "text": "#e8eef2",
        "button": "#1e2732",
        "button_text": "#e8eef2",
        "bright_text": "#ffffff",
        "highlight": "#14b8a6",
        "highlight_text": "#042f2e",
        "disabled_text": "#64748b",
        "border": "#2d3744",
        "canvas": "#121820",
        "page_border": "#0a0e12",
        "shadow": "#000000",
        "icon": "#e2e8f0",
        "icon_disabled": "#64748b",
        "accent": "#14b8a6",
        "accent_soft": "#134e4a",
        "panel": "#161d26",
        "hover": "#243040",
        "checked": "#134e4a",
        "paper": "#1a222c",
        "surface": "#161d26",
        "muted": "#94a3b8",
        "danger": "#f87171",
        "success": "#34d399",
        "sidebar": "#0c1016",
        "sidebar_text": "#cbd5e1",
        "sidebar_active": "#1a222c",
        "sidebar_hover": "#161d26",
        "topbar": "#141a22",
        "cta": "#e8eef2",
        "cta_text": "#0f1419",
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
        font-weight: 600;
    }}
    QDockWidget::title {{
        background: {c['panel']};
        padding: 10px 12px;
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
        color: {c['text']};
        background: {c['surface']};
        font-weight: 600;
        border: 1px solid {c['border']};
    }}
    QWidget#appSidebar {{
        background: {c['sidebar']};
        border-right: 1px solid {c['border']};
    }}
    QLabel#sidebarBrand {{
        color: {c['window_text']};
        font-weight: 700;
        font-size: 15px;
        background: transparent;
    }}
    QLabel#sidebarSection {{
        color: {c['muted']};
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.06em;
        background: transparent;
        padding: 12px 12px 6px 12px;
    }}
    QToolButton#sidebarNav {{
        background: transparent;
        color: {c['sidebar_text']};
        border: 1px solid transparent;
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
        color: {c['window_text']};
        border-color: {c['border']};
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
    QPushButton#primaryCta {{
        background: {c['cta']};
        color: {c['cta_text']};
        border: none;
        border-radius: 12px;
        padding: 10px 18px;
        font-weight: 600;
    }}
    QPushButton#primaryCta:hover {{
        background: {c['accent']};
        color: {c['bright_text']};
    }}
    QPushButton#sidebarOpen {{
        background: {c['cta']};
        color: {c['cta_text']};
        border: none;
        border-radius: 12px;
        padding: 10px 14px;
        font-weight: 600;
    }}
    QPushButton#sidebarOpen:hover {{
        background: {c['accent']};
        color: {c['bright_text']};
    }}
    QPushButton#sidebarGhost {{
        background: transparent;
        color: {c['sidebar_text']};
        border: 1px solid {c['border']};
        border-radius: 12px;
        padding: 8px 14px;
        font-weight: 500;
    }}
    QPushButton#sidebarGhost:hover {{
        background: {c['sidebar_hover']};
        color: {c['window_text']};
    }}
    QPushButton#welcomePrimary {{
        background: {c['cta']};
        color: {c['cta_text']};
        border: none;
        border-radius: 12px;
        padding: 12px 22px;
        font-weight: 600;
        font-size: 13px;
    }}
    QPushButton#welcomePrimary:hover {{
        background: {c['accent']};
        color: {c['bright_text']};
    }}
    QPushButton#welcomeGhost {{
        background: transparent;
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 12px;
        padding: 10px 18px;
        font-weight: 500;
    }}
    QPushButton#welcomeGhost:hover {{
        background: {c['hover']};
        border-color: {c['accent']};
    }}
    QFrame#welcomeDropZone {{
        background: {c['surface']};
        border: 1.5px dashed {c['border']};
        border-radius: 18px;
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
