"""Printing and image export.

Pages are rasterized with PyMuPDF and painted onto the print device.
Rendering is capped at ``PRINT_MAX_DPI`` because a full-bleed A4 page at
a 600 dpi device resolution is a 33-megapixel image per sheet, which
costs far more memory than it adds visible quality.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional, Sequence, Union

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QPageLayout, QPainter
from PySide6.QtPrintSupport import (
    QAbstractPrintDialog,
    QPrintDialog,
    QPrintPreviewDialog,
    QPrinter,
    QPrinterInfo,
)

from src.constants import (
    DEFAULT_EXPORT_DPI,
    PRINT_MAX_DPI,
)
from src.core.document import Document
from src.utils.exceptions import PrintError
from src.utils.file_handler import FileHandler
from src.utils.image_utils import pil_to_qimage
from src.utils.logger import get_logger

logger = get_logger(__name__)

PathLike = Union[str, Path]


class PrintService:
    """Sends documents to a printer and exports pages as images."""

    # ------------------------------------------------------------------
    # Printer discovery
    # ------------------------------------------------------------------
    @staticmethod
    def available_printers() -> List[str]:
        """Names of every printer the system exposes."""
        return [info.printerName() for info in QPrinterInfo.availablePrinters()]

    @staticmethod
    def default_printer() -> str:
        """Name of the default printer, or an empty string if none."""
        return QPrinterInfo.defaultPrinter().printerName()

    @staticmethod
    def has_printer() -> bool:
        return bool(QPrinterInfo.availablePrinters())

    # ------------------------------------------------------------------
    # Page selection
    # ------------------------------------------------------------------
    @staticmethod
    def resolve_pages(
        printer: QPrinter, document: Document, current_page: int = 0
    ) -> List[int]:
        """Translate the printer's range settings into 0-based page indices."""
        count = document.page_count
        print_range = printer.printRange()

        if print_range == QPrinter.PrintRange.CurrentPage:
            return [max(0, min(current_page, count - 1))]

        if print_range == QPrinter.PrintRange.PageRange:
            first = printer.fromPage()
            last = printer.toPage()
            if first or last:
                first = max(1, first or 1)
                last = min(count, last or count)
                if last < first:
                    raise PrintError(
                        f"Invalid page range {first}-{last}."
                    )
                return list(range(first - 1, last))

        return list(range(count))

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------
    @staticmethod
    def paint_pages(
        printer: QPrinter,
        document: Document,
        pages: Sequence[int],
        fit_to_paper: bool = True,
        progress: Optional[Callable[[int, int], bool]] = None,
    ) -> int:
        """Render ``pages`` onto ``printer``.

        Args:
            fit_to_paper: Scale each page to the printable area. When
                False, pages print at their true size and may clip.
            progress: Optional callback ``(done, total) -> keep_going``.

        Returns:
            The number of pages actually painted.

        Raises:
            PrintError: If the painter cannot be started.
        """
        if not pages:
            raise PrintError("No pages selected to print.")

        painter = QPainter()
        if not painter.begin(printer):
            raise PrintError(
                "Could not start the print job. The printer may be offline "
                "or in use."
            )

        dpi = min(printer.resolution() or DEFAULT_EXPORT_DPI, PRINT_MAX_DPI)
        zoom = dpi / 72.0
        painted = 0

        try:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            for position, page_index in enumerate(pages):
                if position > 0 and not printer.newPage():
                    logger.warning("Printer refused a new page after %s", painted)
                    break

                image = pil_to_qimage(
                    document.render_page_to_image(page_index, zoom=zoom)
                )
                target = PrintService._target_rect(printer, image, fit_to_paper)
                painter.drawImage(target, image)
                painted += 1

                if progress and not progress(painted, len(pages)):
                    logger.info("Print cancelled by user after %s page(s)", painted)
                    break
        finally:
            painter.end()

        logger.info("Painted %s page(s) to %s", painted, printer.printerName())
        return painted

    @staticmethod
    def _target_rect(printer: QPrinter, image: QImage, fit_to_paper: bool) -> QRectF:
        """Centre the page image inside the printable area."""
        paper = printer.pageRect(QPrinter.Unit.DevicePixel)
        if image.width() <= 0 or image.height() <= 0:
            return QRectF(paper)

        if not fit_to_paper:
            return QRectF(0, 0, image.width(), image.height())

        scale = min(paper.width() / image.width(), paper.height() / image.height())
        width = image.width() * scale
        height = image.height() * scale
        left = (paper.width() - width) / 2.0
        top = (paper.height() - height) / 2.0
        return QRectF(left, top, width, height)

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------
    @staticmethod
    def build_printer(document: Document) -> QPrinter:
        """Create a printer pre-configured for this document."""
        if not PrintService.has_printer():
            raise PrintError(
                "No printer is available on this system. Install a printer, "
                "or use 'Microsoft Print to PDF'."
            )
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setDocName(document.filename)
        printer.setFromTo(1, document.page_count)

        # Match the paper orientation to the document so a landscape PDF
        # is not shrunk to fit a portrait sheet.
        try:
            width, height = document.get_page_size(0)
            printer.setPageOrientation(
                QPageLayout.Orientation.Landscape
                if width > height
                else QPageLayout.Orientation.Portrait
            )
        except Exception as exc:  # noqa: BLE001 - orientation is a nicety
            logger.debug("Could not set print orientation: %s", exc)
        return printer

    @staticmethod
    def print_with_dialog(
        document: Document,
        parent=None,
        current_page: int = 0,
        fit_to_paper: bool = True,
    ) -> int:
        """Show the system print dialog and print the chosen pages.

        Returns:
            Pages printed, or 0 if the user cancelled.
        """
        printer = PrintService.build_printer(document)
        dialog = QPrintDialog(printer, parent)
        dialog.setWindowTitle(f"Print {document.filename}")
        dialog.setOption(QAbstractPrintDialog.PrintDialogOption.PrintPageRange, True)
        dialog.setOption(QAbstractPrintDialog.PrintDialogOption.PrintCurrentPage, True)
        dialog.setOption(QAbstractPrintDialog.PrintDialogOption.PrintCollateCopies, True)

        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            logger.info("Print dialog cancelled")
            return 0

        pages = PrintService.resolve_pages(printer, document, current_page)
        return PrintService.paint_pages(printer, document, pages, fit_to_paper)

    @staticmethod
    def show_preview(
        document: Document,
        parent=None,
        current_page: int = 0,
        fit_to_paper: bool = True,
    ) -> None:
        """Open a print preview window backed by the same paint routine."""
        printer = PrintService.build_printer(document)
        preview = QPrintPreviewDialog(printer, parent)
        preview.setWindowTitle(f"Print Preview - {document.filename}")
        preview.resize(900, 700)

        def render(target: QPrinter) -> None:
            pages = PrintService.resolve_pages(target, document, current_page)
            PrintService.paint_pages(target, document, pages, fit_to_paper)

        preview.paintRequested.connect(render)
        preview.exec()
        logger.info("Closed print preview for %s", document.filename)

    # ------------------------------------------------------------------
    # Image export
    # ------------------------------------------------------------------
    @staticmethod
    def export_images(
        document: Document,
        output_dir: PathLike,
        pages: Optional[Sequence[int]] = None,
        dpi: int = DEFAULT_EXPORT_DPI,
        image_format: str = "PNG",
    ) -> List[Path]:
        """Save pages as image files.

        Returns:
            The paths written, in page order.
        """
        fmt = image_format.upper()
        if fmt not in ("PNG", "JPEG", "JPG"):
            raise PrintError(f"Unsupported image format: {image_format}")
        if fmt == "JPG":
            fmt = "JPEG"

        folder = FileHandler.ensure_directory_exists(output_dir)
        targets = list(pages) if pages is not None else list(range(document.page_count))
        if not targets:
            raise PrintError("No pages selected to export.")

        suffix = ".png" if fmt == "PNG" else ".jpg"
        stem = Path(document.filename).stem
        zoom = max(1, int(dpi)) / 72.0
        written: List[Path] = []

        for index in targets:
            image = document.render_page_to_image(index, zoom=zoom)
            destination = folder / f"{stem}_page{index + 1:03d}{suffix}"
            try:
                image.save(destination, format=fmt)
            except Exception as exc:  # noqa: BLE001
                raise PrintError(f"Could not write {destination.name}: {exc}") from exc
            written.append(destination)

        logger.info("Exported %s image(s) to %s at %s dpi", len(written), folder, dpi)
        return written
