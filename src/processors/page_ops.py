"""Page organisation: reorder, insert, duplicate, rotate, and import pages.

All page numbers in this module are **0-based**, matching
:class:`~src.core.document.Document`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Sequence, Union

import pymupdf as fitz

from src.core.document import Document
from src.utils.exceptions import PageOperationError, ValidationError
from src.utils.file_handler import FileHandler
from src.utils.logger import get_logger

logger = get_logger(__name__)

PathLike = Union[str, Path]

# US Letter in points, used for blank pages when no size is given.
DEFAULT_PAGE_WIDTH = 612.0
DEFAULT_PAGE_HEIGHT = 792.0


class PageOrganizer:
    """In-place page structure edits on an open document."""

    @staticmethod
    def move_page(document: Document, from_index: int, to_index: int) -> None:
        """Move a page to a new position."""
        count = document.page_count
        PageOrganizer._check_index(from_index, count, "Source")
        if to_index < 0 or to_index >= count:
            raise PageOperationError(
                f"Target position {to_index + 1} is out of range (1-{count})."
            )
        if from_index == to_index:
            return
        with document.transaction() as pdf:
            # PyMuPDF inserts *before* the target index, so moving down
            # needs one extra step to land past the vacated slot. Landing
            # past the final page has no "before" index; -1 means append.
            target = to_index
            if to_index > from_index:
                target = to_index + 1
                if target >= count:
                    target = -1
            pdf.move_page(from_index, target)
        logger.info("Moved page %s to %s", from_index + 1, to_index + 1)

    @staticmethod
    def reorder(document: Document, order: Sequence[int]) -> None:
        """Apply an explicit new page order.

        ``order`` must be a permutation of the current page indices; any
        omitted page would be silently dropped, which is never what the
        caller means.
        """
        count = document.page_count
        requested = list(order)
        if sorted(requested) != list(range(count)):
            raise PageOperationError(
                "The new order must list every page exactly once."
            )
        if requested == list(range(count)):
            return
        with document.transaction() as pdf:
            pdf.select(requested)
        logger.info("Reordered %s pages", count)

    @staticmethod
    def insert_blank_page(
        document: Document,
        index: int,
        width: float = 0.0,
        height: float = 0.0,
    ) -> None:
        """Insert an empty page at ``index``.

        Size defaults to the neighbouring page so the new sheet matches
        the rest of the document.
        """
        count = document.page_count
        if index < 0 or index > count:
            raise PageOperationError(
                f"Cannot insert at position {index + 1}; valid range is 1-{count + 1}."
            )
        if width <= 0 or height <= 0:
            reference = min(max(index - 1, 0), count - 1)
            width, height = document.get_page_size(reference)
        with document.transaction() as pdf:
            pdf.new_page(pno=index, width=width, height=height)
        logger.info("Inserted blank page at position %s", index + 1)

    @staticmethod
    def duplicate_page(document: Document, index: int) -> None:
        """Copy a page and place the copy directly after the original."""
        count = document.page_count
        PageOrganizer._check_index(index, count)
        with document.transaction() as pdf:
            # -1 appends, which is the only way to place the copy after
            # the final page.
            destination = index + 1 if index + 1 < count else -1
            pdf.fullcopy_page(index, destination)
        logger.info("Duplicated page %s", index + 1)

    @staticmethod
    def delete_pages(document: Document, indices: Iterable[int]) -> int:
        """Delete several pages at once, keeping at least one page."""
        count = document.page_count
        targets = sorted({int(i) for i in indices}, reverse=True)
        if not targets:
            raise ValidationError("Select at least one page to delete.")
        for index in targets:
            PageOrganizer._check_index(index, count)
        if len(targets) >= count:
            raise PageOperationError("A document must keep at least one page.")
        with document.transaction() as pdf:
            for index in targets:
                pdf.delete_page(index)
        logger.info("Deleted %s page(s)", len(targets))
        return len(targets)

    @staticmethod
    def rotate_pages(document: Document, indices: Iterable[int], degrees: int) -> int:
        """Rotate several pages by a relative amount."""
        targets = sorted({int(i) for i in indices})
        if not targets:
            raise ValidationError("Select at least one page to rotate.")
        for index in targets:
            current = document.get_page_rotation(index)
            document.rotate_page(index, current + degrees)
        logger.info("Rotated %s page(s) by %s degrees", len(targets), degrees)
        return len(targets)

    @staticmethod
    def import_pages(
        document: Document,
        source_path: PathLike,
        at_index: int = -1,
        from_page: int = 0,
        to_page: int = -1,
    ) -> int:
        """Insert pages from another PDF into this document.

        Args:
            source_path: PDF to read pages from.
            at_index: Where to insert; ``-1`` appends to the end.
            from_page: First source page (0-based).
            to_page: Last source page (0-based); ``-1`` means the last.

        Returns:
            How many pages were added.
        """
        source = FileHandler.validate_pdf(source_path)
        count = document.page_count
        if at_index < 0 or at_index > count:
            at_index = count

        try:
            other = fitz.open(source)
        except Exception as exc:  # noqa: BLE001
            raise PageOperationError(f"Could not open {source.name}") from exc

        try:
            if other.is_encrypted and not other.authenticate(""):
                raise PageOperationError(
                    f"{source.name} is password-protected and cannot be imported."
                )
            last = other.page_count - 1 if to_page < 0 else to_page
            if from_page < 0 or last >= other.page_count or last < from_page:
                raise PageOperationError(
                    f"Invalid page range for {source.name} "
                    f"(it has {other.page_count} pages)."
                )
            added = last - from_page + 1
            with document.transaction() as pdf:
                pdf.insert_pdf(
                    other,
                    from_page=from_page,
                    to_page=last,
                    start_at=at_index,
                )
        finally:
            other.close()

        logger.info("Imported %s page(s) from %s", added, source.name)
        return added

    @staticmethod
    def page_summaries(document: Document) -> List[dict]:
        """Return light metadata for every page, for the organiser dialog."""
        summaries = []
        for index in range(document.page_count):
            width, height = document.get_page_size(index)
            summaries.append(
                {
                    "index": index,
                    "number": index + 1,
                    "width": round(width, 1),
                    "height": round(height, 1),
                    "rotation": document.get_page_rotation(index),
                    "orientation": "landscape" if width > height else "portrait",
                }
            )
        return summaries

    @staticmethod
    def _check_index(index: int, count: int, label: str = "Page") -> None:
        if index < 0 or index >= count:
            raise PageOperationError(
                f"{label} {index + 1} is out of range (1-{count})."
            )
