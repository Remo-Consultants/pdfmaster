"""OCR service for extracting text from scanned PDF pages."""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import pymupdf as fitz
from PIL import Image

from src.core.document import Document
from src.services.bundled_tools import configure_tesseract
from src.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_DPI = 300


class OCRResult:
    """Result from OCR processing of a page."""

    def __init__(
        self,
        page: int,
        text: str,
        confidence: float = 0.0,
        boxes: Optional[List[Tuple[int, int, int, int, str]]] = None,
    ) -> None:
        self.page = page
        self.text = text
        self.confidence = confidence
        self.boxes = boxes or []


class SearchableReport:
    """What ``make_pages_searchable`` did to the open document."""

    def __init__(self) -> None:
        self.results: List[OCRResult] = []
        self.pages_skipped = 0
        self.pages_rotated = 0
        self.pages_deskewed = 0


class OCRService:
    """Service for performing OCR on PDF pages.

    Supports multiple backends:
    - tesseract shipped in vendor/ (default)
    - easyocr (optional extra; not required)
    """

    BACKENDS = ["tesseract", "easyocr"]
    DEFAULT_DPI = 300

    def __init__(self, backend: str = "tesseract", language: str = "eng") -> None:
        self._backend = backend
        self._language = language
        self._tesseract_available: Optional[bool] = None
        self._easyocr_reader = None

    @property
    def is_available(self) -> bool:
        """Check if OCR is available on this system."""
        if self._backend == "tesseract":
            return self._check_tesseract()
        elif self._backend == "easyocr":
            return self._check_easyocr()
        return False

    def _check_tesseract(self) -> bool:
        """Check if the bundled Tesseract engine can be started."""
        if self._tesseract_available is not None:
            return self._tesseract_available

        tesseract_path = configure_tesseract()
        if not tesseract_path:
            self._tesseract_available = False
            logger.debug("Bundled Tesseract not available")
            return False
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self._tesseract_available = True
            logger.debug("Tesseract found at %s", tesseract_path)
        except Exception:
            self._tesseract_available = False
            logger.debug("Tesseract not available")

        return self._tesseract_available

    def _check_easyocr(self) -> bool:
        """Check if easyocr is available."""
        try:
            import easyocr
            return True
        except ImportError:
            return False

    def get_available_backends(self) -> List[str]:
        """Return list of available OCR backends."""
        available = []
        if self._check_tesseract():
            available.append("tesseract")
        if self._check_easyocr():
            available.append("easyocr")
        return available

    def ocr_page(
        self,
        document: Document,
        page_num: int,
        dpi: int = DEFAULT_DPI,
    ) -> OCRResult:
        """Perform OCR on a single page."""
        if not self.is_available:
            raise RuntimeError(f"OCR backend '{self._backend}' is not available")

        zoom = dpi / 72.0
        image = document.render_page_to_image(page_num, zoom=zoom)

        if self._backend == "tesseract":
            return self._ocr_tesseract(image, page_num)
        elif self._backend == "easyocr":
            return self._ocr_easyocr(image, page_num)
        else:
            raise ValueError(f"Unknown OCR backend: {self._backend}")

    def _ocr_image(self, image: Image.Image) -> OCRResult:
        """OCR a raster that has already been rendered, rotated, or deskewed."""
        if self._backend == "tesseract":
            return self._ocr_tesseract(image, page_num=0)
        if self._backend == "easyocr":
            return self._ocr_easyocr(image, page_num=0)
        raise ValueError(f"Unknown OCR backend: {self._backend}")

    def _ocr_tesseract(self, image: Image.Image, page_num: int) -> OCRResult:
        """Perform OCR using pytesseract."""
        import pytesseract

        try:
            data = pytesseract.image_to_data(
                image,
                lang=self._language,
                output_type=pytesseract.Output.DICT,
            )

            text_parts = []
            boxes = []
            confidences = []

            for i, word in enumerate(data["text"]):
                if word.strip():
                    text_parts.append(word)
                    conf = data["conf"][i]
                    if isinstance(conf, (int, float)) and conf >= 0:
                        confidences.append(conf)
                        x, y, w, h = (
                            data["left"][i],
                            data["top"][i],
                            data["width"][i],
                            data["height"][i],
                        )
                        boxes.append((x, y, x + w, y + h, word))

            text = pytesseract.image_to_string(image, lang=self._language)
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

            logger.info(
                "Tesseract OCR page %d: %d words, %.1f%% avg confidence",
                page_num + 1,
                len(text_parts),
                avg_conf,
            )

            return OCRResult(
                page=page_num,
                text=text,
                confidence=avg_conf,
                boxes=boxes,
            )

        except Exception as exc:
            logger.error("Tesseract OCR failed on page %d: %s", page_num + 1, exc)
            raise RuntimeError(f"OCR failed: {exc}") from exc

    def _ocr_easyocr(self, image: Image.Image, page_num: int) -> OCRResult:
        """Perform OCR using easyocr."""
        import easyocr
        import numpy as np

        if self._easyocr_reader is None:
            lang_list = [self._language] if self._language != "eng" else ["en"]
            self._easyocr_reader = easyocr.Reader(lang_list, gpu=False)

        img_array = np.array(image)
        results = self._easyocr_reader.readtext(img_array)

        text_parts = []
        boxes = []
        confidences = []

        for bbox, text, conf in results:
            text_parts.append(text)
            confidences.append(conf * 100)
            x_coords = [p[0] for p in bbox]
            y_coords = [p[1] for p in bbox]
            boxes.append((
                int(min(x_coords)),
                int(min(y_coords)),
                int(max(x_coords)),
                int(max(y_coords)),
                text,
            ))

        full_text = "\n".join(text_parts)
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        logger.info(
            "EasyOCR page %d: %d items, %.1f%% avg confidence",
            page_num + 1,
            len(text_parts),
            avg_conf,
        )

        return OCRResult(
            page=page_num,
            text=full_text,
            confidence=avg_conf,
            boxes=boxes,
        )

    def ocr_pages(
        self,
        document: Document,
        page_numbers: Optional[List[int]] = None,
        dpi: int = DEFAULT_DPI,
        progress_callback=None,
    ) -> List[OCRResult]:
        """Perform OCR on multiple pages."""
        if page_numbers is None:
            page_numbers = list(range(document.page_count))

        results = []
        total = len(page_numbers)

        for i, page_num in enumerate(page_numbers):
            if progress_callback:
                progress_callback(i, total, page_num)

            try:
                result = self.ocr_page(document, page_num, dpi)
                results.append(result)
            except Exception as exc:
                logger.warning("OCR failed for page %d: %s", page_num + 1, exc)
                results.append(OCRResult(page=page_num, text="", confidence=0.0))

        return results

    def create_searchable_pdf(
        self,
        document: Document,
        output_path,
        page_numbers: Optional[List[int]] = None,
        dpi: int = DEFAULT_DPI,
    ):
        """Write a new PDF that copies the pages and adds an invisible text layer."""
        if page_numbers is None:
            page_numbers = list(range(document.page_count))

        with document.transaction(mark_modified=False) as pdf:
            new_doc = fitz.open()
            for page_num in page_numbers:
                page = pdf.load_page(page_num)
                new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
                new_page.show_pdf_page(new_page.rect, pdf, page_num)
                try:
                    result = self.ocr_page(document, page_num, dpi)
                    _insert_invisible_words(new_page, result.boxes, 72.0 / dpi)
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Could not add OCR layer to page %d: %s",
                        page_num + 1,
                        exc,
                    )
            new_doc.save(output_path)
            new_doc.close()

        logger.info("Created searchable PDF at %s", output_path)
        return output_path

    def make_pages_searchable(
        self,
        document: Document,
        page_numbers: List[int],
        dpi: int = DEFAULT_DPI,
        skip_text: bool = True,
        deskew: bool = False,
        rotate_pages: bool = False,
        progress_callback: Optional[Callable[[int, int, int], None]] = None,
    ) -> SearchableReport:
        """Add an invisible text layer to pages of the open document.

        Pages that already contain extractable text are left unchanged when
        ``skip_text`` is set. Deskew redraws a crooked scan as an image.
        Sideways pages are turned using Tesseract orientation detection.
        """
        report = SearchableReport()
        total = len(page_numbers)
        for index, page_num in enumerate(page_numbers):
            if progress_callback:
                progress_callback(index, total, page_num)
            if skip_text and page_has_extractable_text(document, page_num):
                report.pages_skipped += 1
                existing = document.get_page_text(page_num)
                report.results.append(
                    OCRResult(page=page_num, text=existing, confidence=100.0)
                )
                continue
            try:
                image = document.render_page_to_image(page_num, zoom=dpi / 72.0)
                if rotate_pages:
                    turn = orientation_correction(image)
                    if turn:
                        current = document.get_page_rotation(page_num)
                        document.rotate_page(page_num, (current + turn) % 360)
                        image = document.render_page_to_image(page_num, zoom=dpi / 72.0)
                        report.pages_rotated += 1
                if deskew:
                    angle = estimate_skew_degrees(image)
                    if abs(angle) >= 0.5:
                        image = image.rotate(angle, expand=True, fillcolor=(255, 255, 255))
                        _replace_page_with_image(document, page_num, image, dpi)
                        report.pages_deskewed += 1
                result = self._ocr_image(image)
                result.page = page_num
                _insert_invisible_words_on_document(document, page_num, result.boxes, 72.0 / dpi)
                report.results.append(result)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Searchable OCR failed for page %d: %s", page_num + 1, exc)
                report.results.append(OCRResult(page=page_num, text="", confidence=0.0))
        return report


def page_has_extractable_text(document: Document, page_num: int, minimum: int = 1) -> bool:
    """True when the page already has enough text to skip OCR."""
    text = document.get_page_text(page_num) or ""
    compact = re.sub(r"\s+", "", text)
    return len(compact) >= minimum


def orientation_correction(image: Image.Image) -> int:
    """Clockwise degrees (0/90/180/270) that make the scan upright.

    Returns 0 when Tesseract orientation detection is unavailable.
    """
    try:
        from src.services.bundled_tools import configure_tesseract
        configure_tesseract()
        import pytesseract
    except ImportError:
        return 0
    try:
        osd = pytesseract.image_to_osd(image)
    except Exception:  # noqa: BLE001
        return 0
    match = re.search(r"Rotate:\s+(\d+)", osd or "")
    if not match:
        return 0
    turn = int(match.group(1)) % 360
    return turn if turn in (90, 180, 270) else 0


def estimate_skew_degrees(image: Image.Image) -> float:
    """Return the Pillow rotation, in degrees, that straightens text lines.

    The search is a few degrees either side of upright. Projection variance
    is highest when dark pixels line up in horizontal rows.
    """
    gray = image.convert("L")
    gray.thumbnail((500, 500))
    binary = gray.point(lambda pixel: 0 if pixel < 180 else 255)
    best_angle = 0.0
    best_score = -1.0
    for step in range(-12, 13):
        angle = step * 0.5
        rotated = binary.rotate(angle, expand=False, fillcolor=255)
        score = _row_variance(rotated.tobytes(), rotated.width, rotated.height)
        if score > best_score:
            best_score = score
            best_angle = angle
    return best_angle


def _row_variance(raw: bytes, width: int, height: int) -> float:
    if width <= 0 or height <= 0:
        return 0.0
    totals = []
    for y in range(height):
        row = raw[y * width : (y + 1) * width]
        totals.append(sum(1 for value in row if value < 128))
    mean = sum(totals) / len(totals)
    return sum((value - mean) ** 2 for value in totals) / len(totals)


def _insert_invisible_words(page, boxes, scale: float) -> None:
    for x0, y0, x1, y1, word in boxes:
        if not word or not str(word).strip():
            continue
        rect = fitz.Rect(x0 * scale, y0 * scale, x1 * scale, y1 * scale)
        if rect.width <= 0 or rect.height <= 0:
            continue
        fontsize = max(1.0, min(rect.height * 0.9, 72.0))
        page.insert_text(
            (rect.x0, rect.y1 - 1),
            str(word),
            fontsize=fontsize,
            render_mode=3,
        )


def _insert_invisible_words_on_document(document: Document, page_num: int, boxes, scale: float) -> None:
    with document.transaction() as pdf:
        _insert_invisible_words(pdf.load_page(page_num), boxes, scale)


def _replace_page_with_image(document: Document, page_num: int, image: Image.Image, dpi: int) -> None:
    """Replace page content with a raster. Used only when a scan is deskewed."""
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    payload = buffer.getvalue()
    width = image.width * 72.0 / dpi
    height = image.height * 72.0 / dpi
    with document.transaction() as pdf:
        page = pdf.load_page(page_num)
        page.set_rotation(0)
        page.set_mediabox(fitz.Rect(0, 0, width, height))
        page.add_redact_annot(page.rect)
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)
        page.insert_image(page.rect, stream=payload)
