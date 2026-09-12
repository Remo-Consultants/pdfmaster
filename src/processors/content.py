"""Page content editing: new text boxes, images, and replacing existing text.

Replacing text in a PDF is inherently lossy. A PDF stores positioned
glyphs, not editable sentences, so a replacement is really "redact the
old glyphs, draw new ones in the same place". Two consequences the UI
must communicate:

* If the original font is not one of the base-14 fonts, a similar font
  is substituted and the result will not match exactly.
* Longer replacements have to be shrunk to fit, because there is no
  reflow. This module expands the box into available space first and
  only then reduces the font size.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pymupdf as fitz

from src.constants import (
    ANNOT_COLORS,
    DEFAULT_FONT,
    DEFAULT_FONT_SIZE,
    DEFAULT_TEXT_COLOR,
    MIN_FONT_SIZE,
    TEXT_FIT_STEPS,
)
from src.core.document import Document
from src.processors.annotations import resolve_color
from src.utils.exceptions import ContentEditError
from src.utils.logger import get_logger

logger = get_logger(__name__)

PathLike = Union[str, Path]
RectLike = Tuple[float, float, float, float]

# Subset-embedded fonts look like "ABCDEF+Arial-BoldMT".
_SUBSET_PREFIX = re.compile(r"^[A-Z]{6}\+")
_SERIF_HINTS = ("times", "serif", "georgia", "garamond", "book", "roman", "minion")
_MONO_HINTS = ("courier", "mono", "consol")
_BASE14 = {
    ("sans", False, False): "helv",
    ("sans", True, False): "hebo",
    ("sans", False, True): "heit",
    ("sans", True, True): "hebo",
    ("serif", False, False): "tiro",
    ("serif", True, False): "tibo",
    ("serif", False, True): "tiit",
    ("serif", True, True): "tibo",
    ("mono", False, False): "cour",
    ("mono", True, False): "cobo",
    ("mono", False, True): "cour",
    ("mono", True, True): "cobo",
}


def color_int_to_rgb(value: int) -> Tuple[float, float, float]:
    """Convert PyMuPDF's packed sRGB integer to an RGB float triple."""
    return (
        ((value >> 16) & 255) / 255.0,
        ((value >> 8) & 255) / 255.0,
        (value & 255) / 255.0,
    )


def map_to_base14(font_name: str) -> Tuple[str, bool]:
    """Pick the closest always-available font for ``font_name``.

    Returns:
        ``(base14_code, was_substituted)``. ``was_substituted`` is False
        only when the original already is a standard font.
    """
    cleaned = _SUBSET_PREFIX.sub("", font_name or "").lower()
    bold = "bold" in cleaned or cleaned.endswith("bd")
    italic = "italic" in cleaned or "oblique" in cleaned or cleaned.endswith("it")

    if any(hint in cleaned for hint in _MONO_HINTS):
        family = "mono"
    elif any(hint in cleaned for hint in _SERIF_HINTS):
        family = "serif"
    else:
        family = "sans"

    code = _BASE14[(family, bold, italic)]
    exact = cleaned in ("helvetica", "arial", "times", "times-roman", "courier")
    return code, not exact


class ContentEditor:
    """Adds and replaces visible page content."""

    # ------------------------------------------------------------------
    # Reading text
    # ------------------------------------------------------------------
    @staticmethod
    def find_spans(
        document: Document,
        page_num: int,
        rect: Optional[RectLike] = None,
    ) -> List[Dict[str, Any]]:
        """Return the text spans on a page, optionally limited to ``rect``.

        A span is the unit PDFMaster can replace: a run of characters
        sharing one font, size, and colour.
        """
        area = fitz.Rect(*rect) if rect else None
        spans: List[Dict[str, Any]] = []
        with document.transaction(mark_modified=False) as pdf:
            page = pdf.load_page(page_num)
            data = page.get_text("dict")

        for block in data.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    bbox = fitz.Rect(span["bbox"])
                    if area is not None:
                        overlap = bbox & area
                        if overlap.is_empty or bbox.get_area() <= 0:
                            continue
                        if overlap.get_area() / bbox.get_area() < 0.4:
                            continue
                    spans.append(
                        {
                            "text": span["text"],
                            "bbox": tuple(bbox),
                            "font": span["font"],
                            "size": round(float(span["size"]), 2),
                            "color": color_int_to_rgb(int(span.get("color", 0))),
                        }
                    )
        logger.debug("Found %s span(s) on page %s", len(spans), page_num)
        return spans

    @staticmethod
    def text_in_rect(document: Document, page_num: int, rect: RectLike) -> str:
        """Return the plain text inside an area."""
        with document.transaction(mark_modified=False) as pdf:
            page = pdf.load_page(page_num)
            return page.get_textbox(fitz.Rect(*rect)).strip()

    # ------------------------------------------------------------------
    # Replacing text
    # ------------------------------------------------------------------
    @staticmethod
    def replace_text(
        document: Document,
        page_num: int,
        bbox: RectLike,
        new_text: str,
        font: Optional[str] = None,
        size: Optional[float] = None,
        color: Any = None,
        expand_right: float = 0.0,
    ) -> Dict[str, Any]:
        """Replace the text inside ``bbox`` with ``new_text``.

        The original glyphs are redacted and the new string is drawn into
        the same box, expanded into free space to the right and below so
        the font size does not have to shrink more than necessary.

        Returns:
            A report with the font used, the final size, and whether a
            substitute font had to be used.

        Raises:
            ContentEditError: If the text cannot be fitted legibly.
        """
        source = fitz.Rect(*bbox)
        if source.is_empty:
            raise ContentEditError("Select some text to replace.")

        spans = ContentEditor.find_spans(document, page_num, bbox)
        original_font = spans[0]["font"] if spans else DEFAULT_FONT
        original_size = spans[0]["size"] if spans else DEFAULT_FONT_SIZE
        original_color = spans[0]["color"] if spans else ANNOT_COLORS[DEFAULT_TEXT_COLOR]

        if font:
            font_code, substituted = font, False
        else:
            font_code, substituted = map_to_base14(original_font)
        base_size = float(size or original_size or DEFAULT_FONT_SIZE)
        rgb = resolve_color(color, DEFAULT_TEXT_COLOR) if color else original_color

        page_width, page_height = document.get_page_size(page_num)
        # Grow the target box into whitespace so shrinking is a last resort.
        right_limit = min(page_width - 4.0, source.x1 + max(expand_right, 0.0)) \
            if expand_right else min(page_width - 4.0, source.x1 + source.width)
        bottom_limit = min(page_height - 4.0, source.y1 + source.height * 0.6)
        target = fitz.Rect(
            source.x0,
            source.y0 - 1.0,
            max(right_limit, source.x1),
            max(bottom_limit, source.y1 + 2.0),
        )

        with document.transaction() as pdf:
            page = pdf.load_page(page_num)
            page.add_redact_annot(source)
            page.apply_redactions(**_redact_keep_images())

            used_size = base_size
            overflow = -1.0
            for factor in TEXT_FIT_STEPS:
                candidate = round(base_size * factor, 2)
                if candidate < MIN_FONT_SIZE:
                    break
                overflow = page.insert_textbox(
                    target,
                    new_text,
                    fontname=font_code,
                    fontsize=candidate,
                    color=rgb,
                    align=fitz.TEXT_ALIGN_LEFT,
                )
                if overflow >= 0:
                    used_size = candidate
                    break

            if overflow < 0:
                raise ContentEditError(
                    "The replacement text will not fit in that space, even at "
                    "the smallest readable size. Try shorter text or select a "
                    "larger area."
                )

        report = {
            "page": page_num + 1,
            "font": font_code,
            "original_font": original_font,
            "size": used_size,
            "original_size": original_size,
            "substituted": substituted,
            "shrunk": used_size < base_size,
        }
        logger.info("Replaced text on page %s: %s", page_num + 1, report)
        return report

    @staticmethod
    def replace_matching_text(
        document: Document,
        page_num: int,
        search: str,
        replacement: str,
    ) -> int:
        """Replace every occurrence of ``search`` on a page.

        Returns:
            The number of occurrences replaced.
        """
        if not search:
            raise ContentEditError("Enter the text to search for.")
        with document.transaction(mark_modified=False) as pdf:
            page = pdf.load_page(page_num)
            hits = page.search_for(search)
        if not hits:
            return 0
        # Work bottom-up so earlier replacements do not move later boxes.
        for rect in sorted(hits, key=lambda r: (-r.y0, -r.x0)):
            ContentEditor.replace_text(document, page_num, tuple(rect), replacement)
        logger.info("Replaced %s occurrence(s) of %r", len(hits), search)
        return len(hits)

    # ------------------------------------------------------------------
    # Adding content
    # ------------------------------------------------------------------
    @staticmethod
    def add_text(
        document: Document,
        page_num: int,
        rect: RectLike,
        text: str,
        font: str = DEFAULT_FONT,
        size: float = DEFAULT_FONT_SIZE,
        color: Any = None,
    ) -> float:
        """Draw a new text box on the page.

        Returns:
            The font size actually used, which may be smaller than
            requested if the text needed to be shrunk to fit.
        """
        if not text.strip():
            raise ContentEditError("Enter some text to add.")
        area = fitz.Rect(*rect)
        if area.is_empty:
            raise ContentEditError("Drag a box for the text first.")
        rgb = resolve_color(color, DEFAULT_TEXT_COLOR)

        with document.transaction() as pdf:
            page = pdf.load_page(page_num)
            for factor in TEXT_FIT_STEPS:
                candidate = round(size * factor, 2)
                if candidate < MIN_FONT_SIZE:
                    break
                overflow = page.insert_textbox(
                    area, text, fontname=font, fontsize=candidate, color=rgb
                )
                if overflow >= 0:
                    logger.info("Added text box on page %s at %spt",
                                page_num + 1, candidate)
                    return candidate
            raise ContentEditError(
                "That text does not fit in the box you drew. Draw a larger box "
                "or use a smaller font size."
            )

    @staticmethod
    def add_image(
        document: Document,
        page_num: int,
        rect: RectLike,
        image_path: PathLike,
        keep_aspect: bool = True,
    ) -> None:
        """Place an image (logo, scanned signature) on the page."""
        source = Path(image_path)
        if not source.is_file():
            raise ContentEditError(f"Image not found: {source}")
        area = fitz.Rect(*rect)
        if area.is_empty:
            raise ContentEditError("Drag a box for the image first.")
        with document.transaction() as pdf:
            page = pdf.load_page(page_num)
            try:
                page.insert_image(area, filename=str(source), keep_proportion=keep_aspect)
            except Exception as exc:  # noqa: BLE001
                raise ContentEditError(f"Could not place image: {exc}") from exc
        logger.info("Inserted image %s on page %s", source.name, page_num + 1)

    @staticmethod
    def erase_area(document: Document, page_num: int, rect: RectLike) -> None:
        """Blank out an area by redacting it with white fill."""
        area = fitz.Rect(*rect)
        if area.is_empty:
            raise ContentEditError("Drag over the area to erase.")
        with document.transaction() as pdf:
            page = pdf.load_page(page_num)
            page.add_redact_annot(area, fill=(1, 1, 1))
            page.apply_redactions(**_redact_keep_images())
        logger.info("Erased area on page %s", page_num + 1)


def _redact_keep_images() -> Dict[str, Any]:
    """Keep images intact when applying redactions, if this build allows it."""
    option = getattr(fitz, "PDF_REDACT_IMAGE_NONE", None)
    return {"images": option} if option is not None else {}
