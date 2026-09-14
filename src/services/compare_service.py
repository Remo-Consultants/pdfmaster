"""Compare two PDF files page-by-page (text and optional visual diff)."""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher, unified_diff
from pathlib import Path
from typing import List, Optional, Sequence

import pymupdf as fitz
from PIL import Image, ImageChops, ImageStat

from src.utils.exceptions import FileOperationError, ValidationError
from src.utils.file_handler import FileHandler
from src.utils.logger import get_logger

logger = get_logger(__name__)

VISUAL_MATCH_THRESHOLD = 0.985


@dataclass
class PageDiff:
    """Difference summary for one page index."""

    page: int  # 0-based
    status: str  # equal | changed | only_left | only_right
    similarity: float  # text similarity 0..1
    left_preview: str = ""
    right_preview: str = ""
    unified: str = ""
    visual_similarity: Optional[float] = None


@dataclass
class CompareReport:
    """Full comparison between two PDFs."""

    left_path: str
    right_path: str
    left_pages: int
    right_pages: int
    include_visual: bool = False
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
    """Text- and render-based PDF comparison (no cloud, no external tools)."""

    @staticmethod
    def compare_files(
        left: Path | str,
        right: Path | str,
        *,
        max_pages: Optional[int] = None,
        preview_chars: int = 160,
        include_visual: bool = False,
        visual_max_side: int = 480,
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
                    left_doc.load_page(index).get_text("text")
                    if index < left_count
                    else ""
                )
                right_text = (
                    right_doc.load_page(index).get_text("text")
                    if index < right_count
                    else ""
                )

                visual_sim: Optional[float] = None
                if index >= left_count:
                    status = "only_right"
                    text_sim = 0.0
                elif index >= right_count:
                    status = "only_left"
                    text_sim = 0.0
                else:
                    text_sim = SequenceMatcher(None, left_text, right_text).ratio()
                    text_equal = left_text == right_text

                    if include_visual:
                        left_page = left_doc.load_page(index)
                        right_page = right_doc.load_page(index)
                        visual_sim = _visual_similarity(
                            left_page, right_page, visual_max_side
                        )
                        if text_equal and visual_sim >= VISUAL_MATCH_THRESHOLD:
                            status = "equal"
                        else:
                            status = "changed"
                    else:
                        status = "equal" if text_equal else "changed"

                unified = ""
                if status == "changed" and left_text != right_text:
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
                        similarity=text_sim,
                        left_preview=_preview(left_text, preview_chars),
                        right_preview=_preview(right_text, preview_chars),
                        unified=unified,
                        visual_similarity=visual_sim,
                    )
                )

            report = CompareReport(
                left_path=str(left_path),
                right_path=str(right_path),
                left_pages=left_count,
                right_pages=right_count,
                include_visual=include_visual,
                pages=pages,
            )
            logger.info(
                "Compared %s vs %s — %s page(s) differ (visual=%s)",
                left_path.name,
                right_path.name,
                report.changed_count,
                include_visual,
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
        include_visual: bool = False,
    ) -> CompareReport:
        """Compare the open document against another file on disk."""
        return CompareService.compare_files(
            left_doc.file_path,
            right_path,
            max_pages=max_pages,
            include_visual=include_visual,
        )


def _preview(text: str, limit: int) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"


def _render_page_image(page: fitz.Page, max_side: int) -> Image.Image:
    rect = page.rect
    longest = max(rect.width, rect.height, 1.0)
    scale = max_side / longest
    matrix = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    mode = "RGB" if pix.n >= 3 else "L"
    image = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
    if image.mode != "RGB":
        image = image.convert("RGB")
    return image


def _visual_similarity(
    left_page: fitz.Page, right_page: fitz.Page, max_side: int
) -> float:
    """Return 1.0 for identical renders, lower when pixels diverge."""
    img1 = _render_page_image(left_page, max_side)
    img2 = _render_page_image(right_page, max_side)
    if img2.size != img1.size:
        img2 = img2.resize(img1.size, Image.Resampling.LANCZOS)
    diff = ImageChops.difference(img1, img2)
    stat = ImageStat.Stat(diff)
    mean = sum(stat.mean) / max(len(stat.mean), 1)
    return max(0.0, 1.0 - mean / 255.0)
