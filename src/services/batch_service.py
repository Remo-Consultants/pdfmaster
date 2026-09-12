"""Batch processing service for folder-wide PDF operations."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

import pymupdf as fitz

from src.core.document import Document
from src.core.pdf_handler import PDFHandler
from src.utils.exceptions import PageOperationError, ValidationError
from src.utils.file_handler import FileHandler
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BatchResult:
    """Result of processing a single file."""

    source: Path
    output: Optional[Path] = None
    success: bool = False
    error: str = ""
    original_size: int = 0
    final_size: int = 0


@dataclass
class BatchSummary:
    """Summary of a batch operation."""

    total: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    total_input_bytes: int = 0
    total_output_bytes: int = 0
    results: List[BatchResult] = field(default_factory=list)

    @property
    def compression_ratio(self) -> float:
        if self.total_input_bytes == 0:
            return 0.0
        return 1.0 - (self.total_output_bytes / self.total_input_bytes)


@dataclass
class CompressionPreset:
    """Preset for PDF compression settings."""

    name: str
    description: str
    image_quality: int = 80
    image_dpi: int = 150
    garbage_collect: int = 4
    deflate: bool = True
    clean: bool = True
    linearize: bool = False


COMPRESSION_PRESETS = {
    "screen": CompressionPreset(
        name="Screen",
        description="Lowest quality, smallest files (72 dpi images)",
        image_quality=40,
        image_dpi=72,
        garbage_collect=4,
        deflate=True,
        clean=True,
    ),
    "ebook": CompressionPreset(
        name="E-book",
        description="Medium quality for digital reading (150 dpi)",
        image_quality=60,
        image_dpi=150,
        garbage_collect=4,
        deflate=True,
        clean=True,
    ),
    "printer": CompressionPreset(
        name="Printer",
        description="High quality for printing (300 dpi)",
        image_quality=80,
        image_dpi=300,
        garbage_collect=3,
        deflate=True,
        clean=False,
    ),
    "prepress": CompressionPreset(
        name="Prepress",
        description="Maximum quality for professional printing",
        image_quality=95,
        image_dpi=300,
        garbage_collect=2,
        deflate=True,
        clean=False,
        linearize=True,
    ),
    "default": CompressionPreset(
        name="Default",
        description="Balanced compression and quality",
        image_quality=75,
        image_dpi=150,
        garbage_collect=4,
        deflate=True,
        clean=True,
    ),
}


class BatchService:
    """Service for batch processing PDF files in folders."""

    @staticmethod
    def find_pdfs(
        folder: Path,
        recursive: bool = True,
        pattern: str = "*.pdf",
    ) -> List[Path]:
        """Find all PDF files in a folder."""
        folder = Path(folder)
        if not folder.is_dir():
            raise ValidationError(f"Not a directory: {folder}")

        if recursive:
            files = list(folder.rglob(pattern))
        else:
            files = list(folder.glob(pattern))

        valid = [f for f in files if f.is_file()]
        valid.sort()
        logger.info("Found %d PDF file(s) in %s", len(valid), folder)
        return valid

    @staticmethod
    def compress_pdf(
        source: Path,
        output: Path,
        preset: CompressionPreset,
    ) -> BatchResult:
        """Compress a single PDF using the given preset."""
        result = BatchResult(source=source)

        try:
            result.original_size = source.stat().st_size

            doc = fitz.open(source)
            try:
                doc.save(
                    output,
                    garbage=preset.garbage_collect,
                    deflate=preset.deflate,
                    clean=preset.clean,
                    linear=preset.linearize,
                )
            finally:
                doc.close()

            result.output = output
            result.final_size = output.stat().st_size
            result.success = True

            ratio = 1.0 - (result.final_size / result.original_size) if result.original_size else 0
            logger.info(
                "Compressed %s: %d -> %d bytes (%.1f%% reduction)",
                source.name,
                result.original_size,
                result.final_size,
                ratio * 100,
            )

        except Exception as exc:
            result.error = str(exc)
            logger.error("Failed to compress %s: %s", source, exc)

        return result

    @staticmethod
    def batch_compress(
        source_folder: Path,
        output_folder: Path,
        preset_name: str = "default",
        recursive: bool = True,
        preserve_structure: bool = True,
        overwrite: bool = False,
        progress_callback: Optional[Callable[[int, int, Path], None]] = None,
    ) -> BatchSummary:
        """Compress all PDFs in a folder."""
        preset = COMPRESSION_PRESETS.get(preset_name, COMPRESSION_PRESETS["default"])
        source_folder = Path(source_folder)
        output_folder = Path(output_folder)

        output_folder.mkdir(parents=True, exist_ok=True)

        files = BatchService.find_pdfs(source_folder, recursive)
        summary = BatchSummary(total=len(files))

        for i, source in enumerate(files):
            if progress_callback:
                progress_callback(i, len(files), source)

            if preserve_structure:
                relative = source.relative_to(source_folder)
                output = output_folder / relative
            else:
                output = output_folder / source.name

            output.parent.mkdir(parents=True, exist_ok=True)

            if output.exists() and not overwrite:
                summary.skipped += 1
                summary.results.append(
                    BatchResult(source=source, error="Output exists, skipped")
                )
                continue

            result = BatchService.compress_pdf(source, output, preset)
            summary.results.append(result)

            if result.success:
                summary.successful += 1
                summary.total_input_bytes += result.original_size
                summary.total_output_bytes += result.final_size
            else:
                summary.failed += 1

        logger.info(
            "Batch compression complete: %d/%d successful, %.1f%% average reduction",
            summary.successful,
            summary.total,
            summary.compression_ratio * 100,
        )
        return summary

    @staticmethod
    def batch_merge(
        source_folder: Path,
        output_file: Path,
        recursive: bool = False,
        sort_by: str = "name",
    ) -> Path:
        """Merge all PDFs in a folder into a single file."""
        files = BatchService.find_pdfs(source_folder, recursive)
        if len(files) < 2:
            raise ValidationError("Need at least 2 PDFs to merge")

        if sort_by == "name":
            files.sort(key=lambda p: p.name.lower())
        elif sort_by == "date":
            files.sort(key=lambda p: p.stat().st_mtime)
        elif sort_by == "size":
            files.sort(key=lambda p: p.stat().st_size)

        return PDFHandler.merge_documents(output_file, *files)

    @staticmethod
    def batch_extract_text(
        source_folder: Path,
        output_folder: Path,
        recursive: bool = True,
        progress_callback: Optional[Callable[[int, int, Path], None]] = None,
    ) -> BatchSummary:
        """Extract text from all PDFs into .txt files."""
        source_folder = Path(source_folder)
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        files = BatchService.find_pdfs(source_folder, recursive)
        summary = BatchSummary(total=len(files))

        for i, source in enumerate(files):
            if progress_callback:
                progress_callback(i, len(files), source)

            result = BatchResult(source=source)

            try:
                relative = source.relative_to(source_folder)
                output = output_folder / relative.with_suffix(".txt")
                output.parent.mkdir(parents=True, exist_ok=True)

                doc = fitz.open(source)
                try:
                    text_parts = []
                    for page_num in range(doc.page_count):
                        page = doc.load_page(page_num)
                        text = page.get_text("text")
                        text_parts.append(f"--- Page {page_num + 1} ---\n{text}")
                    full_text = "\n\n".join(text_parts)
                finally:
                    doc.close()

                output.write_text(full_text, encoding="utf-8")
                result.output = output
                result.success = True
                result.final_size = len(full_text.encode("utf-8"))
                summary.successful += 1

            except Exception as exc:
                result.error = str(exc)
                summary.failed += 1
                logger.error("Failed to extract text from %s: %s", source, exc)

            summary.results.append(result)

        logger.info(
            "Batch text extraction complete: %d/%d successful",
            summary.successful,
            summary.total,
        )
        return summary

    @staticmethod
    def batch_convert_to_images(
        source_folder: Path,
        output_folder: Path,
        image_format: str = "PNG",
        dpi: int = 150,
        recursive: bool = True,
        progress_callback: Optional[Callable[[int, int, Path], None]] = None,
    ) -> BatchSummary:
        """Convert all PDFs to image files."""
        source_folder = Path(source_folder)
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        files = BatchService.find_pdfs(source_folder, recursive)
        summary = BatchSummary(total=len(files))

        zoom = dpi / 72.0
        ext = ".png" if image_format.upper() == "PNG" else ".jpg"

        for i, source in enumerate(files):
            if progress_callback:
                progress_callback(i, len(files), source)

            result = BatchResult(source=source)

            try:
                relative = source.relative_to(source_folder)
                base_output = output_folder / relative.parent / relative.stem
                base_output.parent.mkdir(parents=True, exist_ok=True)

                doc = fitz.open(source)
                try:
                    for page_num in range(doc.page_count):
                        page = doc.load_page(page_num)
                        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
                        output_path = base_output.parent / f"{base_output.name}_page{page_num + 1:04d}{ext}"
                        pix.save(output_path)
                finally:
                    doc.close()

                result.output = base_output.parent
                result.success = True
                summary.successful += 1

            except Exception as exc:
                result.error = str(exc)
                summary.failed += 1
                logger.error("Failed to convert %s to images: %s", source, exc)

            summary.results.append(result)

        logger.info(
            "Batch image conversion complete: %d/%d successful",
            summary.successful,
            summary.total,
        )
        return summary
