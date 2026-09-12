"""Continuous-scrolling PDF viewer with background rendering.

All pages are laid out in one tall canvas, but only the pages touching
the viewport are rasterized and painted. That keeps a 1,000-page
document as cheap to show as a 3-page one, since cost scales with what
is on screen rather than with the page count.

Page rotation is stored on the document rather than the widget, so
``Document.get_page_size`` already reports rotated dimensions and the
fit calculations must not swap width and height themselves.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Dict, List, Optional, Tuple

import pymupdf as fitz
from PySide6.QtCore import (
    QObject,
    QPointF,
    QRect,
    QRectF,
    QRunnable,
    Qt,
    QThreadPool,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QImage,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
    QWheelEvent,
)
from PySide6.QtWidgets import QScrollArea, QSizePolicy, QWidget

from src.constants import (
    MAX_RENDER_CACHE,
    MAX_RENDER_CACHE_MB,
    ZOOM_DEFAULT_FACTOR,
    ZOOM_MAX_FACTOR,
    ZOOM_MIN_FACTOR,
    ZOOM_STEP_FACTOR,
)
from src.core.document import Document
from src.ui.theme import LIGHT, color as theme_color
from src.ui.tools import (
    CLICK_TOOLS,
    FILLED_PREVIEW,
    FREEHAND_TOOLS,
    ToolMode,
    is_interactive,
)
from src.utils.image_utils import pil_to_qimage
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Small slack when fitting. ``viewport()`` already excludes the
# scrollbars, so this only needs to cover rounding.
FIT_MARGIN_PX = 8
# Space around and between pages, in device pixels.
PAGE_GAP = 16
PAGE_MARGIN = 16
# Shadow is drawn as multiple layers for a soft, realistic look.
SHADOW_LAYERS = 5
SHADOW_BASE_OFFSET = 2
SHADOW_SPREAD = 6
# Minimum drag in device pixels before it counts as a selection.
MIN_DRAG_PX = 3
# Render this many screens beyond the viewport so scrolling stays smooth.
PREFETCH_SCREENS = 0.5
# Coalesce render requests while the user is still scrolling.
SCROLL_SETTLE_MS = 45


class _RenderSignals(QObject):
    """Signal carrier for render tasks (QRunnable cannot own signals)."""

    finished = Signal(int, int, float, QImage)  # generation, page, zoom, image
    failed = Signal(int, int, str)              # generation, page, message


class _RenderTask(QRunnable):
    """Rasterizes one page off the GUI thread."""

    def __init__(
        self,
        document: Document,
        page_num: int,
        zoom: float,
        generation: int,
        signals: _RenderSignals,
    ) -> None:
        super().__init__()
        self._document = document
        self._page_num = page_num
        self._zoom = zoom
        self._generation = generation
        self._signals = signals
        self.setAutoDelete(True)

    def run(self) -> None:
        try:
            if not self._document.is_open:
                return
            image = self._document.render_page_to_image(self._page_num, zoom=self._zoom)
            self._signals.finished.emit(
                self._generation, self._page_num, self._zoom, pil_to_qimage(image)
            )
        except Exception as exc:  # noqa: BLE001 - worker must never raise
            logger.error("Background render of page %s failed: %s", self._page_num, exc)
            self._signals.failed.emit(self._generation, self._page_num, str(exc))


class PageCanvas(QWidget):
    """The scrollable surface that paints every page and takes mouse input."""

    def __init__(self, viewer: "DocumentViewer") -> None:
        super().__init__()
        self._viewer = viewer
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        self._viewer.paint_canvas(self, event.rect())

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            if self._viewer.handle_press(event.position()):
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._viewer.handle_move(event.position()):
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            if self._viewer.handle_release(event.position()):
                event.accept()
                return
        super().mouseReleaseEvent(event)


class DocumentViewer(QScrollArea):
    """Scrolls continuously through a document, rendering pages on demand."""

    page_changed = Signal(int)
    zoom_changed = Signal(float)
    render_finished = Signal(int)
    render_failed = Signal(str)

    # Editing signals. Rectangles and points are unrotated PDF points, and
    # carry the page they belong to because in continuous mode the edited
    # page is not necessarily the "current" one.
    area_selected = Signal(object, int, object)   # ToolMode, page, (x0,y0,x1,y1)
    point_selected = Signal(object, int, object)  # ToolMode, page, (x, y)
    ink_drawn = Signal(int, object)               # page, [[(x, y), ...]]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._document: Optional[Document] = None
        self._current_page = 0
        self._zoom_level = ZOOM_DEFAULT_FACTOR
        self._scheme = LIGHT

        # page -> rect in canvas coordinates
        self._layout: Dict[int, QRectF] = {}
        self._cache: "OrderedDict[Tuple[int, float], QPixmap]" = OrderedDict()
        self._cache_bytes = 0
        self._size_cache: Dict[int, Tuple[float, float]] = {}
        self._pending: set = set()
        self._generation = 0

        self._tool = ToolMode.PAN
        self._drag_page: Optional[int] = None
        self._drag_origin: Optional[QPointF] = None
        self._drag_current: Optional[QPointF] = None
        self._ink_points: List[QPointF] = []
        self._dragging = False

        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._signals = _RenderSignals()
        self._signals.finished.connect(self._on_render_finished)
        self._signals.failed.connect(self._on_render_failed)

        self._settle = QTimer(self)
        self._settle.setSingleShot(True)
        self._settle.setInterval(SCROLL_SETTLE_MS)
        self._settle.timeout.connect(self._on_scroll_settled)

        self.setWidgetResizable(False)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFrameShape(QScrollArea.Shape.NoFrame)

        self._canvas = PageCanvas(self)
        self.setWidget(self._canvas)
        self.apply_scheme(LIGHT)
        logger.debug("DocumentViewer initialized (continuous mode)")

    # ------------------------------------------------------------------
    # Theming
    # ------------------------------------------------------------------
    def apply_scheme(self, scheme: str) -> None:
        """Recolour the canvas for the light or dark theme."""
        self._scheme = scheme
        canvas = theme_color("canvas", scheme)
        self.setStyleSheet(
            f"QScrollArea {{ background-color: {canvas}; border: 0px; }}"
        )
        self.viewport().setStyleSheet(f"background-color: {canvas};")
        self._canvas.update()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def document(self) -> Optional[Document]:
        return self._document

    @property
    def current_page(self) -> int:
        """0-based index of the page occupying the middle of the viewport."""
        return self._current_page

    @property
    def zoom_level(self) -> float:
        """Current zoom factor (1.0 = 100%)."""
        return self._zoom_level

    @property
    def rotation(self) -> int:
        """Stored rotation of the current page, in degrees."""
        if self._document is None:
            return 0
        return self._document.get_page_rotation(self._current_page)

    @property
    def is_rendering(self) -> bool:
        """Whether a background render is currently queued or running."""
        return self._pool.activeThreadCount() > 0 or bool(self._pending)

    @property
    def canvas(self) -> PageCanvas:
        """The widget that paints the pages and receives mouse input."""
        return self._canvas

    def page_origin(self, page: int) -> Optional[QPointF]:
        """Top-left corner of a page in canvas coordinates."""
        rect = self._layout.get(page)
        return None if rect is None else rect.topLeft()

    def page_rect(self, page: int) -> Optional[QRectF]:
        """A page's rectangle in canvas coordinates."""
        return self._layout.get(page)

    def page_pixmap(self, page: int) -> Optional[QPixmap]:
        """The rendered pixmap for a page at the current zoom, if cached."""
        return self._cache.get((page, round(self._zoom_level, 4)))

    # ------------------------------------------------------------------
    # Document lifecycle
    # ------------------------------------------------------------------
    def open_document(self, document: Document) -> None:
        """Load a document and show it from the first page."""
        self.close_document(close_handle=False)
        self._document = document
        self._current_page = 0
        self._zoom_level = ZOOM_DEFAULT_FACTOR
        self._rebuild_layout()
        self.verticalScrollBar().setValue(0)
        self._request_visible()
        self.page_changed.emit(self._current_page)
        self.zoom_changed.emit(self._zoom_level)
        logger.info("Viewer opened %s (%s pages)", document.filename,
                    document.page_count)

    def close_document(self, close_handle: bool = True) -> None:
        """Clear the viewer and optionally close the document handle.

        In-flight renders are drained first so no worker touches the
        PyMuPDF handle after it is closed.
        """
        self._generation += 1
        self._pending.clear()
        self.wait_for_render()
        if self._document is not None and close_handle:
            self._document.close()
        self._document = None
        self._current_page = 0
        self._zoom_level = ZOOM_DEFAULT_FACTOR
        self._layout.clear()
        self._clear_cache()
        self._canvas.setFixedSize(1, 1)
        self._canvas.update()
        logger.debug("Viewer document closed")

    def wait_for_render(self, timeout_ms: int = 30_000) -> bool:
        """Block until queued renders finish. Used on shutdown and in tests."""
        return self._pool.waitForDone(timeout_ms)

    def refresh(self) -> None:
        """Re-read page sizes and re-render, after the document changed."""
        if self._document is None:
            return
        self._generation += 1
        self._pending.clear()
        self._clear_cache()
        self._rebuild_layout()
        self._request_visible()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _page_size(self, page_num: int) -> Tuple[float, float]:
        """On-screen page size at 100% zoom, rotation included."""
        cached = self._size_cache.get(page_num)
        if cached is None:
            cached = self._document.get_page_size(page_num)
            self._size_cache[page_num] = cached
        return cached

    def _rebuild_layout(self) -> None:
        """Recompute every page rect and resize the canvas to match."""
        self._layout.clear()
        if self._document is None:
            self._canvas.setFixedSize(1, 1)
            return

        count = self._document.page_count
        zoom = self._zoom_level
        sizes = [self._page_size(i) for i in range(count)]
        widest = max((w for w, _ in sizes), default=0.0)
        content_width = max(widest * zoom, 1.0)
        canvas_width = content_width + PAGE_MARGIN * 2
        # Fill the viewport when the document is narrower, so the canvas
        # background covers the full width instead of leaving a seam.
        canvas_width = max(canvas_width, self.viewport().width())

        y = float(PAGE_MARGIN)
        for index, (width, height) in enumerate(sizes):
            page_width = width * zoom
            page_height = height * zoom
            x = (canvas_width - page_width) / 2.0
            self._layout[index] = QRectF(x, y, page_width, page_height)
            y += page_height + PAGE_GAP

        total_height = max(y - PAGE_GAP + PAGE_MARGIN, 1.0)
        self._canvas.setFixedSize(int(canvas_width), int(total_height))

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._document is None:
            return
        # Keep the current page anchored while the layout is recentred.
        anchor = self._current_page
        self._rebuild_layout()
        self._scroll_to_page(anchor, emit=False)
        self._schedule_request()

    # ------------------------------------------------------------------
    # Visibility and rendering
    # ------------------------------------------------------------------
    def _viewport_rect(self) -> QRectF:
        """The visible part of the canvas, in canvas coordinates."""
        top = self.verticalScrollBar().value()
        left = self.horizontalScrollBar().value()
        return QRectF(left, top, self.viewport().width(), self.viewport().height())

    def visible_pages(self, prefetch: float = PREFETCH_SCREENS) -> List[int]:
        """Pages touching the viewport, widened by a prefetch margin."""
        if not self._layout:
            return []
        view = self._viewport_rect()
        pad = view.height() * prefetch
        band = QRectF(view.left(), view.top() - pad,
                      max(view.width(), 1.0), view.height() + pad * 2)
        return [index for index, rect in self._layout.items()
                if rect.intersects(band)]

    def _schedule_request(self) -> None:
        self._settle.start()

    def _on_scroll_settled(self) -> None:
        self._request_visible()

    def _request_visible(self) -> None:
        """Queue renders for visible pages, nearest to the viewport first."""
        if self._document is None:
            return

        zoom = round(self._zoom_level, 4)
        centre = self._viewport_rect().center().y()
        wanted = sorted(
            self.visible_pages(),
            key=lambda i: abs(self._layout[i].center().y() - centre),
        )

        queued = 0
        for page in wanted:
            key = (page, zoom)
            if key in self._cache or key in self._pending:
                continue
            self._pending.add(key)
            self._pool.start(
                _RenderTask(self._document, page, zoom, self._generation, self._signals)
            )
            queued += 1

        self._release_offscreen(set(wanted))
        if queued == 0:
            # Everything on screen is already rasterized. Tests and the
            # status bar rely on hearing about the settled state.
            self.render_finished.emit(self._current_page)

    def _on_render_finished(
        self, generation: int, page: int, zoom: float, qimage: QImage
    ) -> None:
        """Store and show a completed render, discarding stale ones."""
        self._pending.discard((page, zoom))
        if generation != self._generation or self._document is None:
            logger.debug("Discarding stale render of page %s", page)
            return
        if abs(zoom - round(self._zoom_level, 4)) > 0.0001:
            return
        self._store_cache((page, zoom), QPixmap.fromImage(qimage))
        rect = self._layout.get(page)
        if rect is not None:
            self._canvas.update(self._to_widget_rect(rect))
        self.render_finished.emit(page)

    def _on_render_failed(self, generation: int, page: int, message: str) -> None:
        self._pending.discard((page, round(self._zoom_level, 4)))
        if generation != self._generation:
            return
        logger.warning("Render failed for page %s: %s", page, message)
        self.render_failed.emit(message)

    def _to_widget_rect(self, rect: QRectF) -> QRect:
        """Canvas rect padded to include the shadow, for repaint requests."""
        pad = SHADOW_BASE_OFFSET + SHADOW_SPREAD + 2
        return rect.adjusted(-2, -2, pad, pad).toRect()

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------
    def paint_canvas(self, widget: QWidget, dirty: QRect) -> None:
        """Paint the background, then every page touching ``dirty``."""
        painter = QPainter(widget)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        try:
            canvas_color = QColor(theme_color("canvas", self._scheme))
            painter.fillRect(dirty, canvas_color)
            if self._document is None:
                self._paint_empty_message(painter, widget)
                return

            zoom = round(self._zoom_level, 4)
            dirty_f = QRectF(dirty)
            shadow_base = QColor(theme_color("shadow", self._scheme))

            for page, rect in self._layout.items():
                if not rect.intersects(dirty_f):
                    continue

                # Multi-layer soft shadow for a realistic paper look.
                self._paint_soft_shadow(painter, rect, shadow_base)

                # White paper fill.
                painter.setBrush(QColor("#ffffff"))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRect(rect)

                # Page content.
                pixmap = self._cache.get((page, zoom))
                if pixmap is not None:
                    painter.drawPixmap(rect.topLeft(), pixmap)
                else:
                    self._paint_placeholder(painter, rect, page)

                # Subtle highlight on top and left edges (light source).
                self._paint_paper_edge(painter, rect)

            self._paint_overlay(painter)
        finally:
            painter.end()

    def _paint_soft_shadow(
        self, painter: QPainter, rect: QRectF, base_color: QColor
    ) -> None:
        """Draw multiple offset layers for a soft drop shadow."""
        painter.setPen(Qt.PenStyle.NoPen)
        for i in range(SHADOW_LAYERS, 0, -1):
            # Each layer is larger and more transparent.
            spread = SHADOW_SPREAD * (i / SHADOW_LAYERS)
            alpha = int(40 * (1 - (i - 1) / SHADOW_LAYERS))
            offset = SHADOW_BASE_OFFSET + spread * 0.4

            shadow = QColor(base_color)
            shadow.setAlpha(alpha)
            painter.setBrush(shadow)

            shadow_rect = rect.adjusted(
                -spread * 0.3,
                -spread * 0.2,
                spread + offset,
                spread + offset,
            )
            painter.drawRoundedRect(shadow_rect, 2, 2)

    def _paint_paper_edge(self, painter: QPainter, rect: QRectF) -> None:
        """Subtle highlight on top/left edges for a 3D paper effect."""
        # Light border around the page.
        if self._scheme == "dark":
            edge = QColor(80, 80, 80)
        else:
            edge = QColor(200, 200, 200)
        painter.setPen(QPen(edge, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)

    def _paint_placeholder(self, painter: QPainter, rect: QRectF, page: int) -> None:
        """A blank sheet with a label, shown until the render lands."""
        painter.fillRect(rect, QColor("#ffffff"))
        painter.setPen(QPen(QColor("#9a9a9a")))
        font = QFont()
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter,
                         f"Rendering page {page + 1}...")

    def _paint_empty_message(self, painter: QPainter, widget: QWidget) -> None:
        painter.setPen(QPen(QColor(theme_color("icon_disabled", self._scheme))))
        font = QFont()
        font.setPointSize(11)
        painter.setFont(font)
        painter.drawText(widget.rect(), Qt.AlignmentFlag.AlignCenter,
                         "Open a PDF to get started  (Ctrl+O)")

    def _paint_overlay(self, painter: QPainter) -> None:
        """Draw live feedback for the drag in progress."""
        if not self._dragging:
            return
        accent = QColor(theme_color("accent", self._scheme))
        pen = QPen(accent)
        pen.setWidth(2)
        painter.setPen(pen)

        if self._tool in FREEHAND_TOOLS and len(self._ink_points) >= 2:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for start, end in zip(self._ink_points, self._ink_points[1:]):
                painter.drawLine(start, end)
            return

        if self._drag_origin is None or self._drag_current is None:
            return
        rect = QRectF(self._drag_origin, self._drag_current).normalized()
        if self._tool in FILLED_PREVIEW:
            fill = QColor(accent)
            fill.setAlpha(70)
            painter.fillRect(rect, fill)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)

    # ------------------------------------------------------------------
    # Cache (bounded by entry count and total pixel memory)
    # ------------------------------------------------------------------
    @staticmethod
    def _pixmap_bytes(pixmap: QPixmap) -> int:
        return pixmap.width() * pixmap.height() * pixmap.depth() // 8

    def _store_cache(self, key: Tuple[int, float], pixmap: QPixmap) -> None:
        if key in self._cache:
            self._cache_bytes -= self._pixmap_bytes(self._cache[key])
        self._cache[key] = pixmap
        self._cache.move_to_end(key)
        self._cache_bytes += self._pixmap_bytes(pixmap)
        self._enforce_budget()

    def _enforce_budget(self, keep: Optional[set] = None) -> None:
        """Evict least-recently-used pages, never one that is on screen."""
        budget = MAX_RENDER_CACHE_MB * 1024 * 1024
        protected = keep if keep is not None else set(self.visible_pages(0.0))
        while len(self._cache) > 1 and (
            len(self._cache) > MAX_RENDER_CACHE or self._cache_bytes > budget
        ):
            victim = next(
                (k for k in self._cache if k[0] not in protected), None
            )
            if victim is None:
                break
            self._cache_bytes -= self._pixmap_bytes(self._cache.pop(victim))
        logger.debug("Render cache: %s entries, %.1f MB",
                     len(self._cache), self._cache_bytes / (1024 * 1024))

    def _release_offscreen(self, visible: set) -> None:
        """Drop pixmaps for other zoom levels and far-away pages."""
        zoom = round(self._zoom_level, 4)
        for key in [k for k in self._cache if abs(k[1] - zoom) > 0.0001]:
            self._cache_bytes -= self._pixmap_bytes(self._cache.pop(key))
        self._enforce_budget(visible)

    def _clear_cache(self) -> None:
        self._cache.clear()
        self._cache_bytes = 0
        self._size_cache.clear()

    def _invalidate_page(self, page_num: Optional[int] = None) -> None:
        if page_num is None:
            self._clear_cache()
            return
        for key in [k for k in self._cache if k[0] == page_num]:
            self._cache_bytes -= self._pixmap_bytes(self._cache.pop(key))
        self._size_cache.pop(page_num, None)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def scrollContentsBy(self, dx: int, dy: int) -> None:  # noqa: N802
        super().scrollContentsBy(dx, dy)
        if self._document is None:
            return
        self._update_current_page()
        self._schedule_request()

    def _update_current_page(self) -> None:
        """The current page is the one crossing the viewport's middle."""
        if not self._layout:
            return
        centre = self._viewport_rect().center().y()
        best = min(
            self._layout.items(),
            key=lambda item: abs(item[1].center().y() - centre),
        )
        for page, rect in self._layout.items():
            if rect.top() <= centre <= rect.bottom():
                best = (page, rect)
                break
        if best[0] != self._current_page:
            self._current_page = best[0]
            self.page_changed.emit(self._current_page)

    def _scroll_to_page(self, page_num: int, emit: bool = True) -> None:
        rect = self._layout.get(page_num)
        if rect is None:
            return
        self.verticalScrollBar().setValue(int(rect.top()) - PAGE_MARGIN)
        if self._current_page != page_num:
            self._current_page = page_num
            if emit:
                self.page_changed.emit(self._current_page)

    def go_to_page(self, page_num: int) -> None:
        """Scroll to a 0-based page index."""
        if self._document is None:
            return
        page_num = max(0, min(page_num, self._document.page_count - 1))
        self._scroll_to_page(page_num)
        self._request_visible()
        logger.debug("Viewer page -> %s", self._current_page + 1)

    def next_page(self) -> None:
        if self._document is None:
            return
        if self._current_page < self._document.page_count - 1:
            self.go_to_page(self._current_page + 1)

    def previous_page(self) -> None:
        if self._document is None:
            return
        if self._current_page > 0:
            self.go_to_page(self._current_page - 1)

    def first_page(self) -> None:
        self.go_to_page(0)

    def last_page(self) -> None:
        if self._document is None:
            return
        self.go_to_page(self._document.page_count - 1)

    # ------------------------------------------------------------------
    # Zoom
    # ------------------------------------------------------------------
    def set_zoom(self, zoom_level: float) -> None:
        """Set zoom factor, clamped to the supported range."""
        clamped = max(ZOOM_MIN_FACTOR, min(ZOOM_MAX_FACTOR, float(zoom_level)))
        if abs(clamped - self._zoom_level) < 0.0001:
            return
        anchor = self._current_page
        self._zoom_level = clamped
        self._rebuild_layout()
        self._scroll_to_page(anchor, emit=False)
        self._request_visible()
        self._canvas.update()
        self.zoom_changed.emit(self._zoom_level)
        logger.debug("Viewer zoom -> %.0f%%", self._zoom_level * 100)

    def zoom_in(self, step: float = ZOOM_STEP_FACTOR) -> None:
        self.set_zoom(self._zoom_level + step)

    def zoom_out(self, step: float = ZOOM_STEP_FACTOR) -> None:
        self.set_zoom(self._zoom_level - step)

    def fit_to_width(self) -> None:
        """Scale pages so their width fills the viewport."""
        if self._document is None:
            return
        width, _ = self._page_size(self._current_page)
        available = max(1, self.viewport().width() - FIT_MARGIN_PX - PAGE_MARGIN * 2)
        self.set_zoom(available / max(1.0, width))

    def fit_to_page(self) -> None:
        """Scale pages so one whole page fits in the viewport."""
        if self._document is None:
            return
        width, height = self._page_size(self._current_page)
        viewport = self.viewport().size()
        scale_x = max(1, viewport.width() - FIT_MARGIN_PX - PAGE_MARGIN * 2) / max(1.0, width)
        scale_y = max(1, viewport.height() - FIT_MARGIN_PX - PAGE_MARGIN * 2) / max(1.0, height)
        self.set_zoom(min(scale_x, scale_y))

    # ------------------------------------------------------------------
    # Rotation / reset
    # ------------------------------------------------------------------
    def rotate_page(self, degrees: int) -> int:
        """Rotate the current page in the document by ``degrees`` (relative)."""
        if self._document is None:
            return 0
        page = self._current_page
        current = self._document.get_page_rotation(page)
        applied = self._document.rotate_page(page, current + degrees)
        if applied == current:
            return applied
        self._invalidate_page(page)
        self._rebuild_layout()
        self._scroll_to_page(page, emit=False)
        self._request_visible()
        self._canvas.update()
        logger.info("Rotated displayed page to %s deg", applied)
        return applied

    def reset_view(self) -> None:
        """Return to 100% zoom and clear rotation on the current page."""
        if self._document is not None:
            page = self._current_page
            if self._document.get_page_rotation(page):
                self._document.rotate_page(page, 0)
                self._invalidate_page(page)
        self._zoom_level = ZOOM_DEFAULT_FACTOR
        self._rebuild_layout()
        self._request_visible()
        self._canvas.update()
        self.zoom_changed.emit(self._zoom_level)

    # ------------------------------------------------------------------
    # Tools and coordinate mapping
    # ------------------------------------------------------------------
    @property
    def tool(self) -> ToolMode:
        """The active editing tool."""
        return self._tool

    def set_tool(self, mode: ToolMode) -> None:
        """Switch the active tool and update the cursor."""
        self._tool = mode
        self._cancel_drag()
        if mode in CLICK_TOOLS:
            cursor = Qt.CursorShape.PointingHandCursor
        elif is_interactive(mode):
            cursor = Qt.CursorShape.CrossCursor
        else:
            cursor = Qt.CursorShape.ArrowCursor
        self._canvas.setCursor(cursor)
        logger.debug("Tool set to %s", mode.value)

    def page_at(self, position: QPointF) -> Optional[int]:
        """Which page a canvas position falls on, if any."""
        for page, rect in self._layout.items():
            if rect.contains(position):
                return page
        return None

    def locate(self, position: QPointF) -> Optional[Tuple[int, float, float]]:
        """Map a canvas position to ``(page, pdf_x, pdf_y)``.

        Returns ``None`` when the point is not on a page. The derotation
        matrix is what makes clicks land correctly on a rotated page,
        where the displayed rect is not the PDF rect.
        """
        if self._document is None or self._zoom_level <= 0:
            return None
        page = self.page_at(position)
        if page is None:
            return None

        rect = self._layout[page]
        local = QPointF(position.x() - rect.left(), position.y() - rect.top())
        point = fitz.Point(local.x() / self._zoom_level, local.y() / self._zoom_level)
        if self._document.get_page_rotation(page):
            with self._document.transaction(mark_modified=False) as pdf:
                matrix = pdf.load_page(page).derotation_matrix
            point = point * matrix
        return (page, point.x, point.y)

    def widget_to_pdf(self, position: QPointF) -> Optional[Tuple[float, float]]:
        """Map a canvas position to PDF coordinates, ignoring which page."""
        found = self.locate(position)
        return None if found is None else (found[1], found[2])

    # ------------------------------------------------------------------
    # Mouse handling (called by PageCanvas)
    # ------------------------------------------------------------------
    def handle_press(self, position: QPointF) -> bool:
        """Begin a tool interaction. Returns True if the event was used."""
        if self._document is None or not is_interactive(self._tool):
            return False
        found = self.locate(position)
        if found is None:
            return False
        page, x, y = found

        if self._tool in CLICK_TOOLS:
            self.point_selected.emit(self._tool, page, (x, y))
            return True

        self._drag_page = page
        self._drag_origin = QPointF(position)
        self._drag_current = QPointF(position)
        self._dragging = True
        if self._tool in FREEHAND_TOOLS:
            self._ink_points = [QPointF(position)]
        return True

    def handle_move(self, position: QPointF) -> bool:
        if not self._dragging:
            return False
        self._drag_current = QPointF(position)
        if self._tool in FREEHAND_TOOLS:
            last = self._ink_points[-1] if self._ink_points else None
            if last is None or (position - last).manhattanLength() >= 2:
                self._ink_points.append(QPointF(position))
        self._canvas.update()
        return True

    def handle_release(self, position: QPointF) -> bool:
        """Finish a drag and emit the resulting selection."""
        if not self._dragging:
            return False
        self._drag_current = QPointF(position)
        tool = self._tool
        page = self._drag_page

        if tool in FREEHAND_TOOLS:
            strokes = self._collect_ink(page)
            self._cancel_drag()
            if strokes and page is not None:
                self.ink_drawn.emit(page, [strokes])
            return True

        rect = self._pdf_rect_from_drag(page)
        origin, current = self._drag_origin, self._drag_current
        too_small = (
            origin is None
            or current is None
            or (abs(current.x() - origin.x()) < MIN_DRAG_PX
                and abs(current.y() - origin.y()) < MIN_DRAG_PX)
        )
        self._cancel_drag()
        if rect is None or too_small or page is None:
            logger.debug("Ignoring empty drag for tool %s", tool.value)
            return True
        self.area_selected.emit(tool, page, rect)
        return True

    def _pdf_on_page(self, page: int, position: QPointF) -> Optional[Tuple[float, float]]:
        """Map a position to PDF coords on a specific page, even if the
        pointer has since strayed outside that page's rectangle."""
        rect = self._layout.get(page)
        if rect is None or self._document is None:
            return None
        clamped = QPointF(
            min(max(position.x(), rect.left()), rect.right()),
            min(max(position.y(), rect.top()), rect.bottom()),
        )
        local = QPointF(clamped.x() - rect.left(), clamped.y() - rect.top())
        point = fitz.Point(local.x() / self._zoom_level, local.y() / self._zoom_level)
        if self._document.get_page_rotation(page):
            with self._document.transaction(mark_modified=False) as pdf:
                matrix = pdf.load_page(page).derotation_matrix
            point = point * matrix
        return (point.x, point.y)

    def _pdf_rect_from_drag(
        self, page: Optional[int]
    ) -> Optional[Tuple[float, float, float, float]]:
        if page is None or self._drag_origin is None or self._drag_current is None:
            return None
        start = self._pdf_on_page(page, self._drag_origin)
        end = self._pdf_on_page(page, self._drag_current)
        if start is None or end is None:
            return None
        x0, x1 = sorted((start[0], end[0]))
        y0, y1 = sorted((start[1], end[1]))
        return (x0, y0, x1, y1)

    def _collect_ink(self, page: Optional[int]) -> List[Tuple[float, float]]:
        if page is None:
            return []
        points: List[Tuple[float, float]] = []
        for widget_point in self._ink_points:
            mapped = self._pdf_on_page(page, widget_point)
            if mapped is not None:
                points.append(mapped)
        return points if len(points) >= 2 else []

    def _cancel_drag(self) -> None:
        self._drag_page = None
        self._drag_origin = None
        self._drag_current = None
        self._ink_points = []
        self._dragging = False
        self._canvas.update()

    # ------------------------------------------------------------------
    # Wheel
    # ------------------------------------------------------------------
    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        """Ctrl+wheel zooms; otherwise scroll normally."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            elif delta < 0:
                self.zoom_out()
            event.accept()
            return
        super().wheelEvent(event)
