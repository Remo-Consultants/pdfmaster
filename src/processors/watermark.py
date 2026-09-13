"""Watermark and stamp operations for PDF pages.

Text watermarks are drawn into the page content stream (visible when
printed/flattened). Image and label stamps are placed as overlay content
or named stamp annotations where appropriate.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import pymupdf as fitz

from src.core.document import Document
from src.utils.exceptions import AnnotationError, PageOperationError
from src.utils.logger import get_logger

logger = get_logger(__name__)

RectLike = Tuple[float, float, float, float]

# Preset rubber-stamp labels shown in the UI.
STAMP_PRESETS: Tuple[str, ...] = (
    "DRAFT",
    "CONFIDENTIAL",
    "APPROVED",
    "REJECTED",
    "VOID",
    "COPY",
    "FINAL",
    "FOR REVIEW",
)


def _resolve_pages(
    document: Document, pages: Optional[Sequence[int]]
) -> List[int]:
    """Normalize page indices; raise if any are out of range."""
    count = document.page_count
    if pages is None:
        return list(range(count))
    resolved = [int(p) for p in pages]
    for page in resolved:
        if page < 0 or page >= count:
            raise PageOperationError(
                f"Page {page + 1} is out of range (1-{count})."
            )
    if not resolved:
        raise PageOperationError("No pages selected for the watermark.")
    return resolved


class WatermarkProcessor:
    """Apply text watermarks and stamps to open documents."""

    @staticmethod
    def add_text_watermark(
        document: Document,
        text: str,
        *,
        pages: Optional[Sequence[int]] = None,
        fontsize: float = 64.0,
        angle: float = 45.0,
        color: Tuple[float, float, float] = (0.55, 0.55, 0.55),
        opacity: float = 0.25,
    ) -> int:
        """Draw a diagonal text watermark on each selected page.

        Returns the number of pages updated.
        """
        label = (text or "").strip()
        if not label:
            raise AnnotationError("Watermark text cannot be empty.")
        opacity = max(0.05, min(1.0, float(opacity)))
        fontsize = max(8.0, float(fontsize))
        targets = _resolve_pages(document, pages)

        with document.transaction() as pdf:
            for page_num in targets:
                page = pdf.load_page(page_num)
                rect = page.rect
                center = fitz.Point(
                    (rect.x0 + rect.x1) / 2.0,
                    (rect.y0 + rect.y1) / 2.0,
                )
                # insert_textbox only allows 90° steps; morph gives arbitrary angles.
                morph = (center, fitz.Matrix(angle))
                # Anchor slightly left of centre so the morph spins around mid-page.
                anchor = fitz.Point(center.x - fontsize * max(len(label), 1) * 0.28, center.y)
                shape = page.new_shape()
                shape.insert_text(
                    anchor,
                    label,
                    fontsize=fontsize,
                    fontname="helv",
                    color=color,
                    morph=morph,
                )
                shape.finish(
                    width=0,
                    color=color,
                    fill=color,
                    fill_opacity=opacity,
                    stroke_opacity=opacity,
                )
                shape.commit(overlay=True)

        logger.info(
            "Added text watermark on %s page(s) of %s",
            len(targets),
            document.filename,
        )
        return len(targets)

    @staticmethod
    def add_text_stamp(
        document: Document,
        page_num: int,
        text: str,
        *,
        rect: Optional[RectLike] = None,
        color: Tuple[float, float, float] = (0.75, 0.1, 0.1),
        fontsize: float = 18.0,
    ) -> None:
        """Place a bordered rubber-stamp label on one page."""
        label = (text or "").strip()
        if not label:
            raise AnnotationError("Stamp text cannot be empty.")
        if page_num < 0 or page_num >= document.page_count:
            raise PageOperationError(f"Page {page_num + 1} is out of range.")

        with document.transaction() as pdf:
            page = pdf.load_page(page_num)
            page_rect = page.rect
            if rect is None:
                width = min(220.0, page_rect.width * 0.45)
                height = max(36.0, fontsize * 2.2)
                cx = (page_rect.x0 + page_rect.x1) / 2
                cy = (page_rect.y0 + page_rect.y1) / 2
                area = fitz.Rect(
                    cx - width / 2,
                    cy - height / 2,
                    cx + width / 2,
                    cy + height / 2,
                )
            else:
                area = fitz.Rect(*rect)
                if area.is_empty or area.width < 10 or area.height < 10:
                    raise AnnotationError("Drag a larger area for the stamp.")

            shape = page.new_shape()
            shape.draw_rect(area)
            shape.finish(width=2.0, color=color, fill=None)
            shape.insert_textbox(
                area + (4, 4, -4, -4),
                label,
                fontsize=fontsize,
                fontname="hebo",
                color=color,
                align=fitz.TEXT_ALIGN_CENTER,
            )
            shape.finish(width=0, color=color)
            shape.commit(overlay=True)

        logger.info("Added text stamp on page %s", page_num + 1)

    @staticmethod
    def add_image_stamp(
        document: Document,
        page_num: int,
        image_path: Path | str,
        *,
        rect: Optional[RectLike] = None,
        opacity: float = 1.0,
    ) -> None:
        """Place an image stamp (logo / signature image) on a page."""
        path = Path(image_path)
        if not path.is_file():
            raise PageOperationError(f"Image not found: {path}")
        if page_num < 0 or page_num >= document.page_count:
            raise PageOperationError(f"Page {page_num + 1} is out of range.")
        _ = max(0.05, min(1.0, float(opacity)))  # reserved for future alpha blend

        with document.transaction() as pdf:
            page = pdf.load_page(page_num)
            page_rect = page.rect
            if rect is None:
                # Default: lower-right quarter-sized box.
                w = min(180.0, page_rect.width * 0.3)
                h = min(90.0, page_rect.height * 0.15)
                area = fitz.Rect(
                    page_rect.x1 - w - 36,
                    page_rect.y1 - h - 36,
                    page_rect.x1 - 36,
                    page_rect.y1 - 36,
                )
            else:
                area = fitz.Rect(*rect)
                if area.is_empty:
                    raise AnnotationError("Drag an area for the image stamp.")

            page.insert_image(
                area,
                filename=str(path),
                keep_proportion=True,
                overlay=True,
            )

        logger.info("Added image stamp on page %s from %s", page_num + 1, path.name)
