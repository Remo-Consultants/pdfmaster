"""Tests for printing helpers and image export.

Constructing a QPrinter crashes hard under the offscreen Qt platform, so
these tests drive the pure logic with a lightweight stub instead.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage
from PySide6.QtPrintSupport import QPrinter

from src.core.document import Document
from src.services.print_service import PrintService
from src.utils.exceptions import PrintError


class FakePrinter:
    """Just enough of QPrinter for the range and layout logic."""

    def __init__(self, print_range=QPrinter.PrintRange.AllPages,
                 first=0, last=0, paper=(0, 0, 600, 800), resolution=300):
        self._range = print_range
        self._first = first
        self._last = last
        self._paper = QRectF(*paper)
        self._resolution = resolution

    def printRange(self):  # noqa: N802
        return self._range

    def fromPage(self) -> int:  # noqa: N802
        return self._first

    def toPage(self) -> int:  # noqa: N802
        return self._last

    def pageRect(self, _unit) -> QRectF:  # noqa: N802
        return self._paper

    def resolution(self) -> int:
        return self._resolution

    def printerName(self) -> str:
        return "Fake Printer"


# ----------------------------------------------------------------------
# Page range resolution
# ----------------------------------------------------------------------
def test_resolve_all_pages(make_pdf) -> None:
    with Document(make_pdf(pages=5)) as doc:
        pages = PrintService.resolve_pages(FakePrinter(), doc)
        assert pages == [0, 1, 2, 3, 4]


def test_resolve_current_page(make_pdf) -> None:
    with Document(make_pdf(pages=5)) as doc:
        printer = FakePrinter(print_range=QPrinter.PrintRange.CurrentPage)
        assert PrintService.resolve_pages(printer, doc, current_page=2) == [2]


def test_resolve_current_page_is_clamped(make_pdf) -> None:
    with Document(make_pdf(pages=2)) as doc:
        printer = FakePrinter(print_range=QPrinter.PrintRange.CurrentPage)
        assert PrintService.resolve_pages(printer, doc, current_page=99) == [1]


def test_resolve_explicit_range(make_pdf) -> None:
    with Document(make_pdf(pages=6)) as doc:
        printer = FakePrinter(
            print_range=QPrinter.PrintRange.PageRange, first=2, last=4
        )
        assert PrintService.resolve_pages(printer, doc) == [1, 2, 3]


def test_resolve_range_is_clamped_to_document(make_pdf) -> None:
    with Document(make_pdf(pages=3)) as doc:
        printer = FakePrinter(
            print_range=QPrinter.PrintRange.PageRange, first=1, last=99
        )
        assert PrintService.resolve_pages(printer, doc) == [0, 1, 2]


def test_resolve_rejects_inverted_range(make_pdf) -> None:
    with Document(make_pdf(pages=5)) as doc:
        printer = FakePrinter(
            print_range=QPrinter.PrintRange.PageRange, first=4, last=2
        )
        with pytest.raises(PrintError):
            PrintService.resolve_pages(printer, doc)


# ----------------------------------------------------------------------
# Layout
# ----------------------------------------------------------------------
def test_fit_to_paper_preserves_aspect_and_centres() -> None:
    printer = FakePrinter(paper=(0, 0, 600, 800))
    image = QImage(300, 300, QImage.Format.Format_RGB888)
    rect = PrintService._target_rect(printer, image, fit_to_paper=True)

    assert rect.width() == pytest.approx(rect.height()), "square stays square"
    assert rect.width() <= 600 and rect.height() <= 800
    assert rect.left() == pytest.approx((600 - rect.width()) / 2)


def test_fit_to_paper_scales_down_oversized_pages() -> None:
    printer = FakePrinter(paper=(0, 0, 600, 800))
    image = QImage(2400, 3200, QImage.Format.Format_RGB888)
    rect = PrintService._target_rect(printer, image, fit_to_paper=True)
    assert rect.width() == pytest.approx(600)
    assert rect.height() == pytest.approx(800)


def test_actual_size_ignores_paper() -> None:
    printer = FakePrinter(paper=(0, 0, 600, 800))
    image = QImage(1000, 1000, QImage.Format.Format_RGB888)
    rect = PrintService._target_rect(printer, image, fit_to_paper=False)
    assert (rect.width(), rect.height()) == (1000, 1000)


def test_empty_image_falls_back_to_paper_rect() -> None:
    printer = FakePrinter(paper=(0, 0, 600, 800))
    rect = PrintService._target_rect(printer, QImage(), fit_to_paper=True)
    assert rect.width() == 600


# ----------------------------------------------------------------------
# Printer discovery
# ----------------------------------------------------------------------
def test_printer_discovery_does_not_raise() -> None:
    names = PrintService.available_printers()
    assert isinstance(names, list)
    assert isinstance(PrintService.has_printer(), bool)
    assert isinstance(PrintService.default_printer(), str)


def test_build_printer_without_printers(make_pdf, monkeypatch) -> None:
    monkeypatch.setattr(PrintService, "has_printer", staticmethod(lambda: False))
    with Document(make_pdf(pages=1)) as doc:
        with pytest.raises(PrintError, match="No printer"):
            PrintService.build_printer(doc)


# ----------------------------------------------------------------------
# Image export
# ----------------------------------------------------------------------
def test_export_all_pages(make_pdf, tmp_path) -> None:
    out = tmp_path / "exported"
    with Document(make_pdf(pages=3)) as doc:
        written = PrintService.export_images(doc, out, dpi=72)
    assert len(written) == 3
    assert all(path.exists() and path.stat().st_size > 0 for path in written)
    assert written[0].name.endswith("_page001.png")


def test_export_selected_pages_as_jpeg(make_pdf, tmp_path) -> None:
    out = tmp_path / "jpegs"
    with Document(make_pdf(pages=4)) as doc:
        written = PrintService.export_images(
            doc, out, pages=[1, 3], dpi=72, image_format="JPEG"
        )
    assert [p.name for p in written] == [
        written[0].name, written[1].name
    ]
    assert len(written) == 2
    assert all(p.suffix == ".jpg" for p in written)


def test_export_dpi_changes_image_size(make_pdf, tmp_path) -> None:
    from PIL import Image

    with Document(make_pdf(pages=1)) as doc:
        low = PrintService.export_images(doc, tmp_path / "low", dpi=72)[0]
        high = PrintService.export_images(doc, tmp_path / "high", dpi=150)[0]

    with Image.open(low) as small, Image.open(high) as large:
        assert large.width > small.width


def test_export_rejects_unknown_format(make_pdf, tmp_path) -> None:
    with Document(make_pdf(pages=1)) as doc:
        with pytest.raises(PrintError, match="Unsupported image format"):
            PrintService.export_images(doc, tmp_path, image_format="TIFF")


def test_export_rejects_empty_selection(make_pdf, tmp_path) -> None:
    with Document(make_pdf(pages=2)) as doc:
        with pytest.raises(PrintError, match="No pages"):
            PrintService.export_images(doc, tmp_path, pages=[])


def test_export_creates_missing_folder(make_pdf, tmp_path) -> None:
    target = tmp_path / "deep" / "nested" / "folder"
    with Document(make_pdf(pages=1)) as doc:
        written = PrintService.export_images(doc, target, dpi=72)
    assert target.is_dir()
    assert written[0].parent == target


def test_paint_pages_requires_pages(make_pdf) -> None:
    with Document(make_pdf(pages=1)) as doc:
        with pytest.raises(PrintError, match="No pages"):
            PrintService.paint_pages(FakePrinter(), doc, [])
