"""Page thumbnail sidebar.

Thumbnails render on a background thread at a small fixed width, so
opening a long document does not stall the window. A generation counter
discards results that arrive after the document changed.
"""

from __future__ import annotations

from typing import Dict, Optional

from PySide6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, Signal
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QListWidget, QListWidgetItem

from src.core.document import Document
from src.utils.image_utils import pil_to_qimage
from src.utils.logger import get_logger

logger = get_logger(__name__)

THUMB_WIDTH = 116
THUMB_PADDING = 10
# Cap the work for very long documents; the rest render as the user scrolls.
INITIAL_BATCH = 40


def _untinted_icon(pixmap: QPixmap) -> QIcon:
    """Wrap a pixmap so selecting the row does not tint the preview.

    Item views draw icons in ``QIcon.Mode.Selected``, which blends the
    highlight colour over the image. Registering the same pixmap for
    that mode keeps the page readable when it is the current one.
    """
    icon = QIcon()
    icon.addPixmap(pixmap, QIcon.Mode.Normal)
    icon.addPixmap(pixmap, QIcon.Mode.Selected)
    icon.addPixmap(pixmap, QIcon.Mode.Active)
    return icon


class _ThumbSignals(QObject):
    done = Signal(int, int, QImage)  # generation, page, image


class _ThumbTask(QRunnable):
    """Renders one thumbnail off the GUI thread."""

    def __init__(self, document: Document, page: int, generation: int,
                 signals: _ThumbSignals) -> None:
        super().__init__()
        self._document = document
        self._page = page
        self._generation = generation
        self._signals = signals
        self.setAutoDelete(True)

    def run(self) -> None:
        try:
            if not self._document.is_open:
                return
            width, _ = self._document.get_page_size(self._page)
            zoom = THUMB_WIDTH / max(1.0, width)
            image = self._document.render_page_to_image(self._page, zoom=zoom)
            self._signals.done.emit(
                self._generation, self._page, pil_to_qimage(image)
            )
        except Exception as exc:  # noqa: BLE001 - worker must never raise
            logger.debug("Thumbnail for page %s failed: %s", self._page, exc)


class ThumbnailPanel(QListWidget):
    """A clickable list of page thumbnails."""

    page_selected = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._document: Optional[Document] = None
        self._generation = 0
        self._requested: set = set()
        self._items: Dict[int, QListWidgetItem] = {}
        self._syncing = False

        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._signals = _ThumbSignals()
        self._signals.done.connect(self._on_thumb)

        # Named so the theme can mark selection with a border instead of
        # a fill, which would otherwise cover the page image.
        self.setObjectName("thumbnailPanel")
        self.setViewMode(QListWidget.ViewMode.ListMode)
        self.setIconSize(QSize(THUMB_WIDTH, int(THUMB_WIDTH * 1.5)))
        self.setSpacing(4)
        self.setUniformItemSizes(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.setMinimumWidth(THUMB_WIDTH + 54)
        self.setMaximumWidth(THUMB_WIDTH + 120)
        self.currentRowChanged.connect(self._on_row_changed)
        self.verticalScrollBar().valueChanged.connect(self._request_visible)

    # ------------------------------------------------------------------
    def set_document(self, document: Optional[Document]) -> None:
        """Rebuild the list for a new document, or clear it for ``None``.

        The rebuild is fully guarded: clearing and repopulating the list
        makes Qt move the current row, and an unguarded
        ``currentRowChanged`` would scroll the viewer to an unrelated
        page after every edit.
        """
        self._generation += 1
        self._requested.clear()
        self._items.clear()
        self._syncing = True
        try:
            self.clear()
            self._document = document
            if document is None:
                return

            placeholder = self._placeholder_icon(document)
            for page in range(document.page_count):
                item = QListWidgetItem(f"{page + 1}")
                item.setIcon(placeholder)
                item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter
                                      | Qt.AlignmentFlag.AlignBottom)
                item.setData(Qt.ItemDataRole.UserRole, page)
                self.addItem(item)
                self._items[page] = item
        finally:
            self._syncing = False
        self._request_visible()
        logger.debug("Thumbnail panel built for %s pages", document.page_count)

    def refresh(self) -> None:
        """Re-render every thumbnail after the document was edited."""
        if self._document is None:
            return
        current = self.currentRow()
        self.set_document(self._document)
        if 0 <= current < self.count():
            self.set_current_page(current)

    def set_current_page(self, page: int) -> None:
        """Highlight a page without re-emitting ``page_selected``."""
        if not (0 <= page < self.count()) or page == self.currentRow():
            return
        was_syncing = self._syncing
        self._syncing = True
        try:
            self.setCurrentRow(page)
            item = self._items.get(page)
            if item is not None:
                self.scrollToItem(item, QListWidget.ScrollHint.EnsureVisible)
        finally:
            self._syncing = was_syncing

    def wait_for_render(self, timeout_ms: int = 15_000) -> bool:
        """Block until queued thumbnails finish. Used on shutdown and tests."""
        return self._pool.waitForDone(timeout_ms)

    # ------------------------------------------------------------------
    def _placeholder_icon(self, document: Document) -> QIcon:
        """A blank sheet sized like page one, so rows do not jump."""
        try:
            width, height = document.get_page_size(0)
            ratio = height / max(1.0, width)
        except Exception:  # noqa: BLE001 - fall back to A4-ish
            ratio = 1.414
        pixmap = QPixmap(THUMB_WIDTH, int(THUMB_WIDTH * ratio))
        pixmap.fill(QColor("#ffffff"))
        painter = QPainter(pixmap)
        try:
            painter.setPen(QColor("#c8c8c8"))
            painter.drawRect(0, 0, pixmap.width() - 1, pixmap.height() - 1)
        finally:
            painter.end()
        return _untinted_icon(pixmap)

    def _visible_rows(self) -> range:
        """Rows on screen, padded so scrolling stays ahead of the user."""
        if self.count() == 0:
            return range(0)
        first = self.indexAt(self.viewport().rect().topLeft())
        last = self.indexAt(self.viewport().rect().bottomLeft())
        start = first.row() if first.isValid() else 0
        end = last.row() if last.isValid() else min(self.count(), INITIAL_BATCH)
        return range(max(0, start - 3), min(self.count(), end + 6))

    def _request_visible(self) -> None:
        if self._document is None:
            return
        for page in self._visible_rows():
            if page in self._requested:
                continue
            self._requested.add(page)
            self._pool.start(
                _ThumbTask(self._document, page, self._generation, self._signals)
            )

    def _on_thumb(self, generation: int, page: int, image: QImage) -> None:
        if generation != self._generation:
            return
        item = self._items.get(page)
        if item is None:
            return
        item.setIcon(_untinted_icon(QPixmap.fromImage(image)))

    def _on_row_changed(self, row: int) -> None:
        if self._syncing or row < 0:
            return
        self.page_selected.emit(row)
