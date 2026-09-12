"""Annotation processor: highlight, underline, strikeout, notes, and ink.

All coordinates passed in are **unrotated PDF points**. The UI is
responsible for mapping screen pixels through the page's derotation
matrix before calling in; see ``DocumentViewer.widget_to_pdf``.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import pymupdf as fitz

from src.constants import (
    ANNOT_COLORS,
    DEFAULT_HIGHLIGHT_COLOR,
    DEFAULT_INK_COLOR,
    DEFAULT_INK_WIDTH,
)
from src.core.document import Document
from src.utils.exceptions import AnnotationError
from src.utils.logger import get_logger

logger = get_logger(__name__)

Point = Tuple[float, float]
RectLike = Tuple[float, float, float, float]

# Markup annotations that need text quads rather than a plain rectangle.
_MARKUP_ADDERS = {
    "highlight": "add_highlight_annot",
    "underline": "add_underline_annot",
    "strikeout": "add_strikeout_annot",
    "squiggly": "add_squiggly_annot",
}


def resolve_color(color: Any, default: str) -> Tuple[float, float, float]:
    """Accept a palette name or an RGB triple and return an RGB triple."""
    if color is None:
        return ANNOT_COLORS[default]
    if isinstance(color, str):
        try:
            return ANNOT_COLORS[color.lower()]
        except KeyError as exc:
            raise AnnotationError(f"Unknown colour '{color}'") from exc
    values = tuple(float(component) for component in color)
    if len(values) != 3 or not all(0.0 <= v <= 1.0 for v in values):
        raise AnnotationError("Colour must be three values between 0 and 1")
    return values  # type: ignore[return-value]


class AnnotationProcessor:
    """Adds, lists, and removes annotations on a :class:`Document`."""

    @staticmethod
    def words_in_rect(
        document: Document, page_num: int, rect: RectLike
    ) -> List[fitz.Rect]:
        """Return the bounding boxes of words intersecting ``rect``.

        A word counts as selected when at least half of it falls inside
        the dragged area, which matches how users expect a rough drag to
        behave.
        """
        selection = fitz.Rect(*rect)
        if selection.is_empty:
            return []
        with document.transaction(mark_modified=False) as pdf:
            page = pdf.load_page(page_num)
            words = page.get_text("words")

        hits: List[fitz.Rect] = []
        for x0, y0, x1, y1, *_ in words:
            word_rect = fitz.Rect(x0, y0, x1, y1)
            overlap = word_rect & selection
            if overlap.is_empty:
                continue
            if word_rect.get_area() <= 0:
                continue
            if overlap.get_area() / word_rect.get_area() >= 0.5:
                hits.append(word_rect)
        logger.debug("Selected %s word(s) in %s on page %s", len(hits), rect, page_num)
        return hits

    @staticmethod
    def add_markup(
        document: Document,
        page_num: int,
        rect: RectLike,
        kind: str = "highlight",
        color: Any = None,
    ) -> int:
        """Highlight, underline, strike out, or squiggle the words in ``rect``.

        Returns:
            The number of words covered by the annotation.

        Raises:
            AnnotationError: If the area contains no text.
        """
        if kind not in _MARKUP_ADDERS:
            raise AnnotationError(f"Unsupported markup type '{kind}'")

        quads = AnnotationProcessor.words_in_rect(document, page_num, rect)
        if not quads:
            raise AnnotationError(
                "No text found in the selected area. Markup needs text to attach to."
            )

        rgb = resolve_color(color, DEFAULT_HIGHLIGHT_COLOR)
        with document.transaction() as pdf:
            page = pdf.load_page(page_num)
            adder = getattr(page, _MARKUP_ADDERS[kind])
            annot = adder(quads)
            annot.set_colors(stroke=rgb)
            annot.update()
        logger.info("Added %s over %s word(s) on page %s", kind, len(quads), page_num + 1)
        return len(quads)

    @staticmethod
    def add_sticky_note(
        document: Document,
        page_num: int,
        point: Point,
        text: str,
        title: str = "PDFMaster",
    ) -> None:
        """Attach a collapsible note icon at ``point``."""
        if not text.strip():
            raise AnnotationError("A note needs some text.")
        with document.transaction() as pdf:
            page = pdf.load_page(page_num)
            annot = page.add_text_annot(fitz.Point(*point), text)
            annot.set_info(title=title)
            annot.update()
        logger.info("Added sticky note on page %s", page_num + 1)

    @staticmethod
    def add_ink(
        document: Document,
        page_num: int,
        strokes: Sequence[Sequence[Point]],
        color: Any = None,
        width: float = DEFAULT_INK_WIDTH,
    ) -> None:
        """Draw freehand ink. ``strokes`` is a list of point lists."""
        usable = [list(stroke) for stroke in strokes if len(stroke) >= 2]
        if not usable:
            raise AnnotationError("Draw a line before releasing the mouse.")
        rgb = resolve_color(color, DEFAULT_INK_COLOR)
        with document.transaction() as pdf:
            page = pdf.load_page(page_num)
            annot = page.add_ink_annot(usable)
            annot.set_colors(stroke=rgb)
            annot.set_border(width=max(0.1, float(width)))
            annot.update()
        logger.info("Added ink with %s stroke(s) on page %s", len(usable), page_num + 1)

    @staticmethod
    def add_shape(
        document: Document,
        page_num: int,
        rect: RectLike,
        shape: str = "rect",
        color: Any = None,
        width: float = DEFAULT_INK_WIDTH,
    ) -> None:
        """Draw an empty rectangle or ellipse outline."""
        area = fitz.Rect(*rect)
        if area.is_empty:
            raise AnnotationError("Drag to define the shape first.")
        rgb = resolve_color(color, DEFAULT_INK_COLOR)
        with document.transaction() as pdf:
            page = pdf.load_page(page_num)
            if shape == "ellipse":
                annot = page.add_circle_annot(area)
            elif shape == "rect":
                annot = page.add_rect_annot(area)
            else:
                raise AnnotationError(f"Unsupported shape '{shape}'")
            annot.set_colors(stroke=rgb)
            annot.set_border(width=max(0.1, float(width)))
            annot.update()
        logger.info("Added %s annotation on page %s", shape, page_num + 1)

    @staticmethod
    def list_annotations(document: Document, page_num: int) -> List[Dict[str, Any]]:
        """Describe every annotation on a page, newest last."""
        results: List[Dict[str, Any]] = []
        with document.transaction(mark_modified=False) as pdf:
            page = pdf.load_page(page_num)
            for index, annot in enumerate(page.annots()):
                info = annot.info
                results.append(
                    {
                        "index": index,
                        "type": annot.type[1],
                        "rect": tuple(annot.rect),
                        "content": info.get("content", ""),
                        "title": info.get("title", ""),
                    }
                )
        return results

    @staticmethod
    def delete_annotation(document: Document, page_num: int, index: int) -> None:
        """Delete the annotation at ``index`` in page order."""
        with document.transaction() as pdf:
            page = pdf.load_page(page_num)
            annots = list(page.annots())
            if index < 0 or index >= len(annots):
                raise AnnotationError(f"No annotation at position {index}.")
            page.delete_annot(annots[index])
        logger.info("Deleted annotation %s on page %s", index, page_num + 1)

    @staticmethod
    def delete_annotations_at(
        document: Document, page_num: int, point: Point
    ) -> int:
        """Delete every annotation whose rectangle contains ``point``."""
        target = fitz.Point(*point)
        removed = 0
        with document.transaction() as pdf:
            page = pdf.load_page(page_num)
            for annot in list(page.annots()):
                if target in annot.rect:
                    page.delete_annot(annot)
                    removed += 1
        if removed:
            logger.info("Deleted %s annotation(s) at %s", removed, point)
        return removed

    @staticmethod
    def clear_page(document: Document, page_num: int) -> int:
        """Remove all annotations from a page."""
        removed = 0
        with document.transaction() as pdf:
            page = pdf.load_page(page_num)
            for annot in list(page.annots()):
                page.delete_annot(annot)
                removed += 1
        logger.info("Cleared %s annotation(s) from page %s", removed, page_num + 1)
        return removed

    @staticmethod
    def flatten(document: Document) -> None:
        """Bake annotations and form fields into the page content."""
        with document.transaction() as pdf:
            try:
                pdf.bake()
            except Exception as exc:  # noqa: BLE001
                raise AnnotationError(f"Could not flatten annotations: {exc}") from exc
        logger.info("Flattened annotations in %s", document.filename)
