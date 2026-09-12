"""High-level PDF operations built on Document, PyMuPDF, and PyPDF."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Union

import pymupdf as fitz
from pypdf import PdfReader, PdfWriter

from src.core.document import Document
from src.utils.exceptions import PageOperationError, ValidationError
from src.utils.file_handler import FileHandler
from src.utils.logger import get_logger

logger = get_logger(__name__)

PathLike = Union[str, Path]


class PDFHandler:
    """Stateless helpers for common PDF workflows."""

    @staticmethod
    def open_document(file_path: PathLike) -> Document:
        """Validate ``file_path`` and return an open ``Document``."""
        if not str(file_path).strip():
            raise ValidationError("File path must not be empty")
        logger.info("Opening document: %s", file_path)
        return Document(file_path)

    @staticmethod
    def merge_documents(output_path: PathLike, *pdf_paths: PathLike) -> Path:
        """Merge two or more PDFs into ``output_path`` using PyPDF.

        Returns:
            The resolved output path.
        """
        if len(pdf_paths) < 2:
            raise ValidationError("At least two PDF files are required to merge.")

        validated: List[Path] = [FileHandler.validate_pdf(path) for path in pdf_paths]
        destination = Path(output_path)
        FileHandler.ensure_directory_exists(destination.parent)

        writer = PdfWriter()
        try:
            for source in validated:
                reader = PdfReader(str(source))
                if reader.is_encrypted:
                    raise PageOperationError(f"Cannot merge encrypted PDF: {source}")
                for page in reader.pages:
                    writer.add_page(page)
            with destination.open("wb") as handle:
                writer.write(handle)
        except PageOperationError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("Merge failed: %s", exc)
            raise PageOperationError(f"Could not merge PDFs: {exc}") from exc

        logger.info("Merged %s files into %s", len(validated), destination)
        return destination.resolve()

    @staticmethod
    def split_document(
        pdf_path: PathLike,
        page_ranges: Sequence[Sequence[int]],
        output_dir: PathLike,
    ) -> List[Path]:
        """Split ``pdf_path`` into one file per range.

        Each range is ``(start, end)`` with **1-based inclusive** page numbers.
        """
        source = FileHandler.validate_pdf(pdf_path)
        if not page_ranges:
            raise ValidationError("At least one page range is required.")
        directory = FileHandler.ensure_directory_exists(output_dir)

        outputs: List[Path] = []
        with Document(source) as document:
            for index, raw_range in enumerate(page_ranges, start=1):
                if len(raw_range) != 2:
                    raise ValidationError("Each page range must be a (start, end) pair.")
                start_ui, end_ui = int(raw_range[0]), int(raw_range[1])
                start, end = start_ui - 1, end_ui - 1
                extracted = document.extract_pages(start, end)
                dest = directory / f"{source.stem}_part{index}.pdf"
                extracted.save(dest)
                extracted.close()
                outputs.append(dest)
                logger.info("Wrote split part %s: %s", index, dest)
        return outputs

    @staticmethod
    def extract_pages(
        pdf_path: PathLike,
        page_numbers: Iterable[int],
        output_path: PathLike,
    ) -> Path:
        """Extract 1-based ``page_numbers`` into a new PDF at ``output_path``."""
        source = FileHandler.validate_pdf(pdf_path)
        pages = sorted({int(num) for num in page_numbers})
        if not pages:
            raise ValidationError("At least one page number is required.")

        destination = Path(output_path)
        FileHandler.ensure_directory_exists(destination.parent)

        with Document(source) as document:
            new_doc = fitz.open()
            try:
                for number in pages:
                    index = number - 1
                    document._validate_page_index(index)
                    new_doc.insert_pdf(document._pdf, from_page=index, to_page=index)
                new_doc.save(destination)
            except Exception as exc:  # noqa: BLE001
                raise PageOperationError(f"Could not extract pages: {exc}") from exc
            finally:
                new_doc.close()

        logger.info("Extracted pages %s from %s to %s", pages, source, destination)
        return destination.resolve()

    @staticmethod
    def rotate_pages(
        pdf_path: PathLike,
        page_numbers: Iterable[int],
        rotation: int,
        output: PathLike,
    ) -> Path:
        """Rotate 1-based ``page_numbers`` and save to ``output``."""
        source = FileHandler.validate_pdf(pdf_path)
        pages = sorted({int(num) for num in page_numbers})
        if not pages:
            raise ValidationError("At least one page number is required.")

        destination = Path(output)
        FileHandler.ensure_directory_exists(destination.parent)

        with Document(source) as document:
            for number in pages:
                document.rotate_page(number - 1, rotation)
            document.save(destination)

        logger.info("Rotated pages %s by %s° -> %s", pages, rotation, destination)
        return destination.resolve()

    @staticmethod
    def get_pdf_info(pdf_path: PathLike) -> Dict[str, Any]:
        """Return a summary dictionary for ``pdf_path``."""
        source = FileHandler.validate_pdf(pdf_path)
        with Document(source) as document:
            meta = document.get_metadata()
            first_width, first_height = document.get_page_size(0)
            info = {
                "path": str(source),
                "filename": document.filename,
                "page_count": document.page_count,
                "file_size_bytes": FileHandler.get_file_size(source),
                "file_size_mb": round(FileHandler.get_file_size_mb(source), 3),
                "page_width": first_width,
                "page_height": first_height,
                "title": meta.get("title") or "",
                "author": meta.get("author") or "",
                "creator": meta.get("creator") or "",
                "producer": meta.get("producer") or "",
                "encrypted": meta.get("encrypted", False),
            }
        logger.debug("PDF info for %s: %s", source, info)
        return info
