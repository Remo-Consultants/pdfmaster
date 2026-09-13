"""Compare two PDF files page-by-page (text-oriented diff)."""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher, unified_diff
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import pymupdf as fitz

from src.utils.exceptions import FileOperationError, ValidationError
from src.utils.file_handler import FileHandler
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PageDiff:
    """Difference summary for one page index."""

    page: int  # 0-based
    status: str  # equal | changed | only_left | only_right
    similarity: float
    left_preview: str = ""
    right_preview: str = ""
    unified: str = ""


@dataclass
class CompareReport:
    """Full comparison between two PDFs."""

    left_path: str
    right_path: str
    left_pages: int
    right_pages: int
    pages: List[PageDiff] = field(default_factory=list)

    @property
    def identical(self) -> bool:
        return (
            self.left_pages == self.right_pages
            and all(p.status == "equal" for p in self.pages)
        )

    @property
    def changed_count(self) -> int:
        return sum(1 for p in self.pages if p.status != "equal")


class CompareService:
    """Text-based PDF comparison (no cloud, no external tools)."""

    @staticmethod
    def compare_files(
        left: Path | str,
        right: Path | str,
        *,
        max_pages: Optional[int] = None,
        preview_chars: int = 160,
    ) -> CompareReport:
        """Compare two PDF paths and return a structured report."""
        left_path = Path(left)
        right_path = Path(right)
        if left_path.resolve() == right_path.resolve():
            raise ValidationError("Choose two different PDF files to compare.")

        try:
            FileHandler.validate_pdf(str(left_path))
            FileHandler.validate_pdf(str(right_path))
        except Exception as exc:  # noqa: BLE001
            raise FileOperationError(str(exc)) from exc

        left_doc = fitz.open(left_path)
        right_doc = fitz.open(right_path)
        try:
            left_count = left_doc.page_count
            right_count = right_doc.page_count
            limit = max(left_count, right_count)
            if max_pages is not None:
                limit = min(limit, max(1, int(max_pages)))

            pages: List[PageDiff] = []
            for index in range(limit):
                left_text = (
                    left_doc.load_page(index).get_text("text") if index < left_count else ""
                )
                right_text = (
                    right_doc.load_page(index).get_text("text")
                    if index < right_count
                    else ""
                )

                if index >= left_count:
                    status = "only_right"
                    similarity = 0.0
                elif index >= right_count:
                    status = "only_left"
                    similarity = 0.0
                else:
                    similarity = SequenceMatcher(
                        None, left_text, right_text
                    ).ratio()
                    status = "equal" if left_text == right_text else "changed"

                unified = ""
                if status == "changed":
                    unified = "\n".join(
                        unified_diff(
                            left_text.splitlines(),
                            right_text.splitlines(),
                            fromfile=f"left:p{index + 1}",
                            tofile=f"right:p{index + 1}",
                            lineterm="",
                        )
                    )

                pages.append(
                    PageDiff(
                        page=index,
                        status=status,
                        similarity=similarity,
                        left_preview=_preview(left_text, preview_chars),
                        right_preview=_preview(right_text, preview_chars),
                        unified=unified,
                    )
                )

            report = CompareReport(
                left_path=str(left_path),
                right_path=str(right_path),
                left_pages=left_count,
                right_pages=right_count,
                pages=pages,
            )
            logger.info(
                "Compared %s vs %s — %s page(s) differ",
                left_path.name,
                right_path.name,
                report.changed_count,
            )
            return report
        finally:
            left_doc.close()
            right_doc.close()

    @staticmethod
    def compare_documents(
        left_doc,
        right_path: Path | str,
        *,
        max_pages: Optional[int] = None,
    ) -> CompareReport:
        """Compare the open document against another file on disk."""
        return CompareService.compare_files(
            left_doc.file_path, right_path, max_pages=max_pages
        )


def _preview(text: str, limit: int) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"
