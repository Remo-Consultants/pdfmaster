"""Tests for watermarks and stamps (Phase 4)."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from src.core.document import Document
from src.processors.watermark import STAMP_PRESETS, WatermarkProcessor
from src.utils.exceptions import AnnotationError, PageOperationError


def test_text_watermark_all_pages(make_pdf) -> None:
    path = make_pdf(pages=3)
    with Document(path) as doc:
        count = WatermarkProcessor.add_text_watermark(doc, "CONFIDENTIAL")
        assert count == 3
        assert doc.is_modified
        # Watermark text is embedded in content.
        assert "CONFIDENTIAL" in doc.get_page_text(0)


def test_text_watermark_current_page_only(make_pdf) -> None:
    path = make_pdf(pages=2)
    with Document(path) as doc:
        count = WatermarkProcessor.add_text_watermark(
            doc, "DRAFT", pages=[1], fontsize=48, opacity=0.4
        )
        assert count == 1
        assert "DRAFT" in doc.get_page_text(1)
        assert "DRAFT" not in doc.get_page_text(0)


def test_text_watermark_rejects_empty(make_pdf) -> None:
    with Document(make_pdf()) as doc:
        with pytest.raises(AnnotationError):
            WatermarkProcessor.add_text_watermark(doc, "   ")


def test_text_stamp_and_presets(make_pdf) -> None:
    assert "CONFIDENTIAL" in STAMP_PRESETS
    with Document(make_pdf()) as doc:
        WatermarkProcessor.add_text_stamp(doc, 0, "APPROVED")
        assert "APPROVED" in doc.get_page_text(0)


def test_image_stamp(make_pdf, tmp_path: Path) -> None:
    image = tmp_path / "stamp.png"
    Image.new("RGB", (80, 40), color=(200, 30, 30)).save(image)
    with Document(make_pdf()) as doc:
        WatermarkProcessor.add_image_stamp(
            doc, 0, image, rect=(400, 700, 520, 760)
        )
        assert doc.is_modified


def test_image_stamp_missing_file(make_pdf, tmp_path: Path) -> None:
    with Document(make_pdf()) as doc:
        with pytest.raises(PageOperationError):
            WatermarkProcessor.add_image_stamp(doc, 0, tmp_path / "missing.png")
