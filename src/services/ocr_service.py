"""OCR service for extracting text from scanned PDF pages."""

from __future__ import annotations

import io
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image

from src.core.document import Document
from src.utils.logger import get_logger

logger = get_logger(__name__)


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


class OCRService:
    """Service for performing OCR on PDF pages.

    Supports multiple backends:
    - pytesseract (default, requires tesseract-ocr installed)
    - easyocr (optional, requires easyocr package)
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
        """Check if tesseract is installed."""
        if self._tesseract_available is not None:
            return self._tesseract_available

        tesseract_path = shutil.which("tesseract")
        if tesseract_path:
            self._tesseract_available = True
            logger.debug("Tesseract found at %s", tesseract_path)
        else:
            try:
                import pytesseract
                pytesseract.get_tesseract_version()
                self._tesseract_available = True
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
        output_path: Path,
        page_numbers: Optional[List[int]] = None,
        dpi: int = DEFAULT_DPI,
    ) -> Path:
        """Create a searchable PDF by adding OCR text layer.

        This is a basic implementation that adds invisible text behind the
        scanned image. For production use, consider pdf2searchablepdf.
        """
        import pymupdf as fitz

        if page_numbers is None:
            page_numbers = list(range(document.page_count))

        with document.transaction(mark_modified=False) as pdf:
            new_doc = fitz.open()

            for page_num in page_numbers:
                page = pdf.load_page(page_num)
                new_page = new_doc.new_page(
                    width=page.rect.width,
                    height=page.rect.height,
                )

                new_page.show_pdf_page(new_page.rect, pdf, page_num)

                try:
                    result = self.ocr_page(document, page_num, dpi)
                    scale = 72.0 / dpi

                    for x0, y0, x1, y1, word in result.boxes:
                        rect = fitz.Rect(
                            x0 * scale,
                            y0 * scale,
                            x1 * scale,
                            y1 * scale,
                        )
                        if rect.width > 0 and rect.height > 0:
                            fontsize = min(rect.height * 0.9, 12)
                            new_page.insert_text(
                                (rect.x0, rect.y1 - 2),
                                word,
                                fontsize=fontsize,
                                render_mode=3,
                            )
                except Exception as exc:
                    logger.warning(
                        "Could not add OCR layer to page %d: %s",
                        page_num + 1,
                        exc,
                    )

            new_doc.save(output_path)
            new_doc.close()

        logger.info("Created searchable PDF at %s", output_path)
        return output_path
