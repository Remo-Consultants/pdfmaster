"""Context tool rail — mode content without a visible ribbon tab strip.

Sidebar selects the active mode; this widget shows only that mode's groups.
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
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.theme import color as theme_color

RIBBON_HEIGHT = 78
RIBBON_COMPACT_HEIGHT = 68


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
    """One mode's content area containing multiple groups."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._groups: List[RibbonGroup] = []
        self._separators: List[QFrame] = []
        self._scheme = "light"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 2)
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
    """Context tool rail — stacked mode panels without a tab strip."""

    current_tab_changed = Signal(int)
    mode_changed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("contextRail")
        self._tabs: Dict[str, RibbonTab] = {}
        self._tab_indices: Dict[str, int] = {}
        self._index_to_mode: Dict[int, str] = {}
        self._scheme = "light"
        self._compact = False
        self._current_mode = "home"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stack = QStackedWidget()
        self._stack.currentChanged.connect(self._on_stack_changed)
        layout.addWidget(self._stack)

        self.setFixedHeight(RIBBON_HEIGHT)

    def add_tab(self, name: str, title: str) -> RibbonTab:
        """Add a mode panel to the context rail (``title`` kept for API compat)."""
        del title  # Sidebar owns the visible labels.
        tab = RibbonTab()
        self._tabs[name] = tab
        idx = self._stack.addWidget(tab)
        self._tab_indices[name] = idx
        self._index_to_mode[idx] = name
        return tab

    def get_tab(self, name: str) -> Optional[RibbonTab]:
        """Get a tab by its internal name."""
        return self._tabs.get(name)

    def set_mode(self, name: str) -> None:
        """Show the tool groups for ``name`` (sidebar-driven)."""
        idx = self._tab_indices.get(name)
        if idx is None:
            return
        if self._compact and name != "home":
            return
        self._current_mode = name
        self._stack.setCurrentIndex(idx)

    @property
    def current_mode(self) -> str:
        return self._current_mode

    def set_compact(self, compact: bool) -> None:
        """Home-only essentials when no document is open."""
        if compact == self._compact:
            return
        self._compact = compact
        self.setFixedHeight(RIBBON_COMPACT_HEIGHT if compact else RIBBON_HEIGHT)
        if compact:
            self.set_mode("home")

    @property
    def is_compact(self) -> bool:
        return self._compact

    def _on_stack_changed(self, index: int) -> None:
        self.current_tab_changed.emit(index)
        mode = self._index_to_mode.get(index)
        if mode:
            self._current_mode = mode
            self.mode_changed.emit(mode)

    def apply_scheme(self, scheme: str) -> None:
        """Update colours for the current theme."""
        self._scheme = scheme
        bg = theme_color("topbar", scheme)
        border = theme_color("border", scheme)

        self.setStyleSheet(f"""
            Ribbon#contextRail {{
                background: {bg};
                border-bottom: 1px solid {border};
            }}
            RibbonGroup {{
                background: transparent;
            }}
        """)
        for tab in self._tabs.values():
            tab.apply_scheme(scheme)
            for group in tab._groups:
                for btn in group._buttons:
                    btn.setAutoRaise(True)
                    btn.setStyleSheet("")
