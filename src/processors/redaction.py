"""Redaction: permanently remove content from a page.

Unlike a black rectangle drawn on top, applying a redaction deletes the
underlying text and image data, so it cannot be recovered by selecting
or copying from the saved file.
"""

from __future__ import annotations

from typing import Any, Iterable, List, Sequence, Tuple

import pymupdf as fitz

from src.constants import ANNOT_COLORS
from src.core.document import Document
from src.processors.annotations import resolve_color
from src.utils.exceptions import AnnotationError
from src.utils.logger import get_logger

logger = get_logger(__name__)

RectLike = Tuple[float, float, float, float]


class Redactor:
    """Marks and applies redactions."""

    @staticmethod
    def redact_areas(
        document: Document,
        page_num: int,
        rects: Sequence[RectLike],
        fill: Any = "black",
        remove_images: bool = True,
    ) -> int:
        """Permanently remove the content inside each rectangle.

        Args:
            rects: Areas to remove, in unrotated PDF points.
            fill: Colour painted over the removed area.
            remove_images: Also strip images that the areas cover.

        Returns:
            The number of areas redacted.
        """
        areas = [fitz.Rect(*r) for r in rects]
        areas = [r for r in areas if not r.is_empty]
        if not areas:
            raise AnnotationError("Drag over the content you want to remove.")

        rgb = resolve_color(fill, "black")
        with document.transaction() as pdf:
            page = pdf.load_page(page_num)
            for area in areas:
                page.add_redact_annot(area, fill=rgb)
            page.apply_redactions(**Redactor._image_option(remove_images))
        logger.info("Applied %s redaction(s) on page %s", len(areas), page_num + 1)
        return len(areas)

    @staticmethod
    def redact_text(
        document: Document,
        search: str,
        pages: Iterable[int] | None = None,
        fill: Any = "black",
    ) -> int:
        """Find and permanently remove every occurrence of ``search``.

        Returns:
            The total number of occurrences removed.
        """
        if not search.strip():
            raise AnnotationError("Enter the text to redact.")
        rgb = resolve_color(fill, "black")
        targets = list(pages) if pages is not None else list(range(document.page_count))

        removed = 0
        with document.transaction() as pdf:
            for page_index in targets:
                page = pdf.load_page(page_index)
                hits = page.search_for(search)
                if not hits:
                    continue
                for rect in hits:
                    page.add_redact_annot(rect, fill=rgb)
                page.apply_redactions(**Redactor._image_option(True))
                removed += len(hits)
        logger.info("Redacted %s occurrence(s) of %r", removed, search)
        return removed

    @staticmethod
    def preview_text(
        document: Document, page_num: int, rects: Sequence[RectLike]
    ) -> List[str]:
        """Return the text that would be destroyed, so the UI can confirm."""
        found: List[str] = []
        with document.transaction(mark_modified=False) as pdf:
            page = pdf.load_page(page_num)
            for rect in rects:
                text = page.get_textbox(fitz.Rect(*rect)).strip()
                if text:
                    found.append(text)
        return found

    @staticmethod
    def _image_option(remove_images: bool) -> dict:
        if remove_images:
            option = getattr(fitz, "PDF_REDACT_IMAGE_PIXELS", None)
        else:
            option = getattr(fitz, "PDF_REDACT_IMAGE_NONE", None)
        return {"images": option} if option is not None else {}
