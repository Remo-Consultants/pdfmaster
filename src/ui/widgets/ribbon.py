"""Ribbon-style toolbar with tabbed sections and labelled groups.

Slim, icon-first command bar — keeps Acrobat-style tabs without the
dense height tax of classic office ribbons.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QAction, QColor, QPalette
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.theme import color as theme_color

RIBBON_HEIGHT = 82
RIBBON_COMPACT_HEIGHT = 72


class RibbonGroup(QFrame):
    """A labelled group of controls within a ribbon tab."""

    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._title = title
        self._buttons: List[QToolButton] = []
        self._scheme = "light"

        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(1)

        self._content = QWidget()
        self._content.setMinimumHeight(44)
        self._content_layout = QHBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(2)
        self._content_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        layout.addWidget(self._content, 1)

        label = QLabel(title)
        label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        label.setFixedHeight(13)
        layout.addWidget(label)
        self._label = label

    def add_action(
        self,
        action: QAction,
        large: bool = False,
        label: Optional[str] = None,
    ) -> QToolButton:
        """Add a tool button for an action.

        ``label`` overrides the text shown under a large icon (menus keep
        the action's full text). Pass ``""`` for icon-only even when large.
        """
        btn = QToolButton()
        btn.setDefaultAction(action)
        btn.setAutoRaise(True)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        if large:
            if label is not None:
                action.setIconText(label)
                caption = label
            else:
                caption = (action.iconText() or action.text()).replace("&", "")

            btn.setIconSize(QSize(22, 22))
            if caption:
                btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
                width = max(56, min(76, 10 + len(caption) * 7))
                btn.setFixedSize(width, 48)
            else:
                # Icon-only large button — same height as labelled neighbours.
                btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
                btn.setFixedSize(36, 48)
        else:
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            btn.setIconSize(QSize(18, 18))
            btn.setFixedSize(30, 30)

        self._apply_button_palette(btn)
        self._content_layout.addWidget(btn)
        self._buttons.append(btn)
        return btn

    def add_widget(self, widget: QWidget) -> None:
        """Add a custom widget to the group."""
        self._content_layout.addWidget(widget)

    def add_separator(self) -> None:
        """Add a vertical separator line."""
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Plain)
        sep.setFixedWidth(1)
        sep.setStyleSheet(
            f"background-color: {theme_color('border', self._scheme)};"
        )
        self._content_layout.addWidget(sep)

    def _apply_button_palette(self, btn: QToolButton) -> None:
        """Keep caption text readable in light and dark themes."""
        text = QColor(theme_color("window_text", self._scheme))
        disabled = QColor(theme_color("disabled_text", self._scheme))
        pal = btn.palette()
        for role in (
            QPalette.ColorRole.ButtonText,
            QPalette.ColorRole.WindowText,
            QPalette.ColorRole.Text,
        ):
            pal.setColor(QPalette.ColorGroup.Active, role, text)
            pal.setColor(QPalette.ColorGroup.Inactive, role, text)
            pal.setColor(QPalette.ColorGroup.Disabled, role, disabled)
        btn.setPalette(pal)

    def apply_scheme(self, scheme: str) -> None:
        """Update colours for the current theme."""
        self._scheme = scheme
        muted = theme_color("disabled_text", scheme)
        self._label.setStyleSheet(
            f"font-size: 9px; color: {muted}; background: transparent;"
        )
        for btn in self._buttons:
            self._apply_button_palette(btn)


class RibbonTab(QWidget):
    """One tab's content area containing multiple groups."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._groups: List[RibbonGroup] = []
        self._separators: List[QFrame] = []
        self._scheme = "light"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(0)
        layout.addStretch(1)
        self._layout = layout

    def add_group(self, title: str) -> RibbonGroup:
        """Add a labelled group to this tab."""
        if self._groups:
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.VLine)
            sep.setFrameShadow(QFrame.Shadow.Plain)
            sep.setFixedWidth(1)
            sep.setStyleSheet(
                f"background-color: {theme_color('border', self._scheme)};"
            )
            self._layout.insertWidget(self._layout.count() - 1, sep)
            self._separators.append(sep)

        group = RibbonGroup(title, self)
        self._layout.insertWidget(self._layout.count() - 1, group)
        self._groups.append(group)
        return group

    def apply_scheme(self, scheme: str) -> None:
        """Update colours for the current theme."""
        self._scheme = scheme
        border = theme_color("border", scheme)
        for sep in self._separators:
            sep.setStyleSheet(f"background-color: {border};")
        for group in self._groups:
            group.apply_scheme(scheme)


class Ribbon(QWidget):
    """A tabbed ribbon toolbar with groups of commands."""

    current_tab_changed = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._tabs: Dict[str, RibbonTab] = {}
        self._tab_indices: Dict[str, int] = {}
        self._scheme = "light"
        self._compact = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tab_widget = QTabWidget()
        self._tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self._tab_widget.setDocumentMode(True)
        self._tab_widget.currentChanged.connect(self.current_tab_changed.emit)
        layout.addWidget(self._tab_widget)

        self.setFixedHeight(RIBBON_HEIGHT)

    def add_tab(self, name: str, title: str) -> RibbonTab:
        """Add a tab to the ribbon."""
        tab = RibbonTab()
        self._tabs[name] = tab
        idx = self._tab_widget.addTab(tab, title)
        self._tab_indices[name] = idx
        return tab

    def get_tab(self, name: str) -> Optional[RibbonTab]:
        """Get a tab by its internal name."""
        return self._tabs.get(name)

    def set_compact(self, compact: bool) -> None:
        """Home-only essentials when no document is open."""
        if compact == self._compact:
            return
        self._compact = compact
        self.setFixedHeight(RIBBON_COMPACT_HEIGHT if compact else RIBBON_HEIGHT)
        for name, idx in self._tab_indices.items():
            if name == "home":
                continue
            self._tab_widget.setTabVisible(idx, not compact)
        if compact:
            home_idx = self._tab_indices.get("home", 0)
            self._tab_widget.setCurrentIndex(home_idx)

    @property
    def is_compact(self) -> bool:
        return self._compact

    def apply_scheme(self, scheme: str) -> None:
        """Update colours for the current theme."""
        self._scheme = scheme
        bg = theme_color("window", scheme)
        border = theme_color("border", scheme)
        text = theme_color("window_text", scheme)
        muted = theme_color("muted", scheme)
        accent = theme_color("accent", scheme)
        hover = theme_color("hover", scheme)

        self.setStyleSheet(f"""
            Ribbon {{
                background: {bg};
                border-bottom: 1px solid {border};
            }}
            QTabWidget::pane {{
                border: none;
                background: {bg};
            }}
            QTabBar {{
                background: {bg};
            }}
            QTabBar::tab {{
                background: transparent;
                color: {muted};
                padding: 5px 12px;
                border: none;
                border-bottom: 2px solid transparent;
                margin-right: 1px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }}
            QTabBar::tab:hover {{
                background: {hover};
                color: {text};
            }}
            QTabBar::tab:selected {{
                color: {text};
                border-bottom: 2px solid {accent};
                font-weight: 600;
            }}
            RibbonGroup {{
                background: transparent;
            }}
        """)
        # Do NOT style QToolButton via stylesheets — that forces Qt's
        # classic engine and disables HiDPI icon pixmaps (blurry icons).
        for tab in self._tabs.values():
            tab.apply_scheme(scheme)
            for group in tab._groups:
                for btn in group._buttons:
                    btn.setAutoRaise(True)
                    btn.setStyleSheet("")
