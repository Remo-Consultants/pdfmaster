"""Multi-document tab bar for opening several PDFs at once.

Each tab owns its own viewer, document, and edit history. Closing a tab
with unsaved changes prompts the user.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QMessageBox,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.document import Document
from src.core.history import DocumentHistory
from src.ui.tools import ToolMode
from src.ui.widgets.document_viewer import DocumentViewer
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentTab(QWidget):
    """One open document with its own viewer, history, and state."""

    def __init__(
        self,
        document: Document,
        scheme: str = "light",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._document = document
        self._history = DocumentHistory()
        self._tool = ToolMode.PAN
        self._highlight_color = "yellow"
        self._ink_color = "red"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.viewer = DocumentViewer(self)
        self.viewer.apply_scheme(scheme)
        self.viewer.open_document(document)
        layout.addWidget(self.viewer)

    @property
    def document(self) -> Document:
        return self._document

    @property
    def history(self) -> DocumentHistory:
        return self._history

    @property
    def tool(self) -> ToolMode:
        return self._tool

    @tool.setter
    def tool(self, mode: ToolMode) -> None:
        self._tool = mode
        self.viewer.set_tool(mode)

    @property
    def highlight_color(self) -> str:
        return self._highlight_color

    @highlight_color.setter
    def highlight_color(self, value: str) -> None:
        self._highlight_color = value

    @property
    def ink_color(self) -> str:
        return self._ink_color

    @ink_color.setter
    def ink_color(self, value: str) -> None:
        self._ink_color = value

    @property
    def filename(self) -> str:
        return self._document.filename

    @property
    def is_modified(self) -> bool:
        return self._document.is_modified

    def apply_scheme(self, scheme: str) -> None:
        self.viewer.apply_scheme(scheme)

    def close_document(self) -> None:
        """Drain renders and close the PyMuPDF handle."""
        self.viewer.close_document(close_handle=True)
        self._history.clear()


class DocumentTabs(QTabWidget):
    """Manages multiple open documents in a tab bar."""

    # Emitted when the active document changes, with the new tab index
    # (-1 if no tabs remain).
    active_tab_changed = Signal(int)
    # Emitted when a document is opened or closed.
    tab_count_changed = Signal(int)
    # Emitted when the current document's modified state changes.
    modified_changed = Signal(bool)

    def __init__(self, scheme: str = "light", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._scheme = scheme
        self._tabs: list[DocumentTab] = []

        self.setObjectName("documentTabs")
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setDocumentMode(True)
        self.setElideMode(Qt.TextElideMode.ElideRight)
        self.tabBar().setExpanding(False)

        self.tabCloseRequested.connect(self._on_close_requested)
        self.currentChanged.connect(self._on_current_changed)

    @property
    def current_tab(self) -> Optional[DocumentTab]:
        """The currently visible tab, or None if empty."""
        idx = self.currentIndex()
        return self._tabs[idx] if 0 <= idx < len(self._tabs) else None

    @property
    def current_document(self) -> Optional[Document]:
        tab = self.current_tab
        return tab.document if tab else None

    @property
    def current_viewer(self) -> Optional[DocumentViewer]:
        tab = self.current_tab
        return tab.viewer if tab else None

    @property
    def current_history(self) -> Optional[DocumentHistory]:
        tab = self.current_tab
        return tab.history if tab else None

    def open_document(self, document: Document) -> int:
        """Add a new tab for a document and make it current.

        Returns the new tab's index.
        """
        tab = DocumentTab(document, self._scheme, self)
        self._tabs.append(tab)
        idx = self.addTab(tab, document.filename)
        self.setCurrentIndex(idx)
        self._update_tab_title(idx)
        self.tab_count_changed.emit(self.count())
        logger.info("Opened tab for %s (index %d)", document.filename, idx)
        return idx

    def close_tab(self, index: int, force: bool = False) -> bool:
        """Close a tab, prompting if there are unsaved changes.

        Returns True if the tab was closed.
        """
        if not (0 <= index < len(self._tabs)):
            return False

        tab = self._tabs[index]
        if not force and tab.is_modified:
            result = QMessageBox.question(
                self,
                "Unsaved changes",
                f"{tab.filename} has unsaved changes. Close anyway?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if result == QMessageBox.StandardButton.Cancel:
                return False
            if result == QMessageBox.StandardButton.Save:
                try:
                    tab.document.save()
                except Exception as exc:
                    QMessageBox.critical(
                        self, "Save failed", str(exc)
                    )
                    return False

        tab.close_document()
        self._tabs.pop(index)
        self.removeTab(index)
        self.tab_count_changed.emit(self.count())
        logger.info("Closed tab %d", index)
        return True

    def close_all(self, force: bool = False) -> bool:
        """Close every tab, prompting for unsaved changes.

        Returns True if all tabs were closed.
        """
        while self.count() > 0:
            if not self.close_tab(0, force=force):
                return False
        return True

    def find_tab(self, file_path: Path) -> int:
        """Return the index of the tab for a file, or -1 if not open."""
        for idx, tab in enumerate(self._tabs):
            if tab.document.file_path == file_path:
                return idx
        return -1

    def apply_scheme(self, scheme: str) -> None:
        """Retheme all tabs."""
        self._scheme = scheme
        for tab in self._tabs:
            tab.apply_scheme(scheme)

    def refresh_current(self) -> None:
        """Re-render the current tab after an edit."""
        tab = self.current_tab
        if tab:
            tab.viewer.refresh()
            self._update_tab_title(self.currentIndex())

    def _update_tab_title(self, index: int) -> None:
        """Mark the tab with a dot if the document is modified."""
        if not (0 <= index < len(self._tabs)):
            return
        tab = self._tabs[index]
        title = tab.filename
        if tab.is_modified:
            title = f"● {title}"
        self.setTabText(index, title)

    def _on_close_requested(self, index: int) -> None:
        self.close_tab(index)

    def _on_current_changed(self, index: int) -> None:
        self.active_tab_changed.emit(index)
        tab = self.current_tab
        if tab:
            self.modified_changed.emit(tab.is_modified)
