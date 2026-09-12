"""Core PDF document model backed by PyMuPDF (fitz)."""

from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple, Union

import pymupdf as fitz
from PIL import Image

from src.constants import MAX_FILE_SIZE_MB
from src.utils.exceptions import PageOperationError, PDFLoadError, PDFRenderError
from src.utils.file_handler import FileHandler
from src.utils.logger import get_logger

logger = get_logger(__name__)

PathLike = Union[str, Path]


class Document:
    """In-memory representation of an open PDF file.

    Page numbers accepted by public methods are **0-based**. The UI layer
    is responsible for converting 1-based user values.

    PyMuPDF is not thread-safe, so every access to the underlying handle
    is serialized through ``self._lock``. This lets a background render
    run while the GUI thread queries page geometry.

    The instance is a context manager and must be closed to release the
    underlying PyMuPDF document.
    """

    def __init__(self, file_path: PathLike) -> None:
        """Load and validate a PDF from disk.

        Args:
            file_path: Path to the PDF file.

        Raises:
            PDFLoadError: If the file cannot be opened as a PDF.
        """
        self._logger = logger
        self._pdf: Optional[fitz.Document] = None
        self._is_open = False
        self._modified = False
        self._was_repaired = False
        self._lock = threading.RLock()

        try:
            resolved = FileHandler.validate_pdf(file_path)
        except Exception as exc:  # noqa: BLE001 - wrap all load failures
            raise PDFLoadError(str(exc)) from exc

        size_mb = FileHandler.get_file_size_mb(resolved)
        if size_mb > MAX_FILE_SIZE_MB:
            raise PDFLoadError(
                f"PDF is {size_mb:.1f} MB, which exceeds the "
                f"{MAX_FILE_SIZE_MB} MB limit."
            )

        self._file_path = resolved
        self._filename = resolved.name

        try:
            self._pdf = fitz.open(self._file_path)
        except Exception as exc:  # noqa: BLE001
            self._logger.error("PyMuPDF failed to open %s: %s", self._file_path, exc)
            raise PDFLoadError(f"Could not open PDF: {self._file_path}") from exc

        if self._pdf.is_encrypted:
            authenticated = False
            try:
                authenticated = bool(self._pdf.authenticate(""))
            except Exception:  # noqa: BLE001
                authenticated = False
            if not authenticated:
                self._pdf.close()
                self._pdf = None
                raise PDFLoadError("This PDF is password-protected and cannot be opened.")

        if self._pdf.page_count < 1:
            self._pdf.close()
            self._pdf = None
            raise PDFLoadError("The PDF contains no pages.")

        self._was_repaired = bool(getattr(self._pdf, "is_repaired", False))
        self._is_open = True
        self._logger.info(
            "Loaded PDF '%s' (%s pages, %.2f MB, repaired=%s)",
            self._filename,
            self._pdf.page_count,
            size_mb,
            self._was_repaired,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def file_path(self) -> Path:
        """Absolute path of the opened file."""
        return self._file_path

    @property
    def filename(self) -> str:
        """File name without the directory."""
        return self._filename

    @property
    def page_count(self) -> int:
        """Number of pages currently in the document."""
        with self._lock:
            self._ensure_open()
            return self._pdf.page_count

    @property
    def is_open(self) -> bool:
        """Whether the underlying PDF handle is still usable."""
        return self._is_open and self._pdf is not None and not self._pdf.is_closed

    @property
    def is_modified(self) -> bool:
        """Whether unsaved page operations have been applied."""
        return self._modified

    @property
    def was_repaired(self) -> bool:
        """Whether PyMuPDF had to repair a damaged file to open it."""
        return self._was_repaired

    # ------------------------------------------------------------------
    # Page access
    # ------------------------------------------------------------------
    def get_page_count(self) -> int:
        """Return the total number of pages."""
        return self.page_count

    def get_page(self, page_num: int) -> fitz.Page:
        """Return the PyMuPDF page object for ``page_num`` (0-based)."""
        with self._lock:
            self._ensure_open()
            self._validate_page_index(page_num)
            try:
                return self._pdf.load_page(page_num)
            except Exception as exc:  # noqa: BLE001
                self._logger.error("Failed to load page %s: %s", page_num, exc)
                raise PageOperationError(f"Could not load page {page_num + 1}") from exc

    def get_metadata(self) -> Dict[str, Any]:
        """Return document metadata plus basic file facts."""
        with self._lock:
            self._ensure_open()
            meta = dict(self._pdf.metadata or {})
            meta["page_count"] = self._pdf.page_count
            meta["file_path"] = str(self._file_path)
            meta["file_size_bytes"] = FileHandler.get_file_size(self._file_path)
            meta["encrypted"] = bool(self._pdf.is_encrypted)
            meta["repaired"] = self._was_repaired
        self._logger.debug("Metadata for %s: %s", self._filename, meta)
        return meta

    def get_page_text(self, page_num: int) -> str:
        """Extract plain text from a page."""
        with self._lock:
            page = self.get_page(page_num)
            try:
                text = page.get_text("text") or ""
            except Exception as exc:  # noqa: BLE001
                self._logger.error("Text extraction failed on page %s: %s", page_num, exc)
                raise PageOperationError(
                    f"Could not extract text from page {page_num + 1}"
                ) from exc
        self._logger.debug("Extracted %s characters from page %s", len(text), page_num)
        return text

    def get_page_size(self, page_num: int) -> Tuple[float, float]:
        """Return the page's displayed ``(width, height)`` in PDF points.

        The rectangle already accounts for the page's stored rotation, so
        callers must not swap the values again for rotated pages.
        """
        with self._lock:
            page = self.get_page(page_num)
            rect = page.rect
            return (rect.width, rect.height)

    def render_page_to_image(
        self,
        page_num: int,
        zoom: float = 1.0,
        rotation: int = 0,
    ) -> Image.Image:
        """Render a page to a PIL RGB image.

        Args:
            page_num: 0-based page index.
            zoom: Scale factor (1.0 = 100% / 72 DPI).
            rotation: Additional clockwise rotation in degrees.

        Returns:
            A PIL ``Image`` in RGB mode.

        Raises:
            PDFRenderError: If rendering fails.
        """
        with self._lock:
            page = self.get_page(page_num)
            try:
                matrix = fitz.Matrix(zoom, zoom)
                rot = int(rotation) % 360
                if rot:
                    matrix = matrix.prerotate(rot)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                if pix.n == 1:
                    mode = "L"
                elif pix.n == 4:
                    mode = "RGBA"
                else:
                    mode = "RGB"
                image = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
                if image.mode != "RGB":
                    image = image.convert("RGB")
            except Exception as exc:  # noqa: BLE001
                self._logger.error("Render failed for page %s: %s", page_num, exc)
                raise PDFRenderError(f"Could not render page {page_num + 1}: {exc}") from exc
        self._logger.debug(
            "Rendered page %s at zoom=%.2f rotation=%s (%sx%s)",
            page_num,
            zoom,
            rotation,
            image.width,
            image.height,
        )
        return image

    # ------------------------------------------------------------------
    # Editing support
    # ------------------------------------------------------------------
    @contextmanager
    def transaction(self, mark_modified: bool = True) -> Iterator[fitz.Document]:
        """Hold the document lock while mutating the raw PyMuPDF handle.

        Processors use this instead of touching ``_pdf`` directly, so all
        edits stay serialized against background rendering and the
        modified flag is set consistently.

        Args:
            mark_modified: Set the unsaved-changes flag on success.

        Yields:
            The underlying ``fitz.Document``.
        """
        with self._lock:
            self._ensure_open()
            yield self._pdf
            if mark_modified:
                self._modified = True

    def snapshot(self) -> bytes:
        """Serialize the current state for the undo history."""
        with self._lock:
            self._ensure_open()
            try:
                return self._pdf.tobytes()
            except Exception as exc:  # noqa: BLE001
                self._logger.error("Could not snapshot %s: %s", self._filename, exc)
                raise PageOperationError("Could not capture document state.") from exc

    def restore(self, payload: bytes, mark_modified: bool = True) -> None:
        """Replace the in-memory document with a previous snapshot."""
        with self._lock:
            try:
                restored = fitz.open(stream=payload, filetype="pdf")
            except Exception as exc:  # noqa: BLE001
                self._logger.error("Could not restore snapshot: %s", exc)
                raise PageOperationError("Could not restore the previous state.") from exc
            if self._pdf is not None and not self._pdf.is_closed:
                self._pdf.close()
            self._pdf = restored
            self._is_open = True
            self._modified = mark_modified
        self._logger.info("Restored %s from snapshot", self._filename)

    def mark_modified(self) -> None:
        """Flag the document as having unsaved changes."""
        self._modified = True

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------
    def delete_page(self, page_num: int) -> None:
        """Delete a page and update the page count.

        Raises:
            PageOperationError: If the index is invalid or only one page remains.
        """
        with self._lock:
            self._ensure_open()
            self._validate_page_index(page_num)
            if self._pdf.page_count <= 1:
                raise PageOperationError("Cannot delete the last remaining page.")
            try:
                self._pdf.delete_page(page_num)
            except Exception as exc:  # noqa: BLE001
                self._logger.error("Delete page %s failed: %s", page_num, exc)
                raise PageOperationError(f"Could not delete page {page_num + 1}") from exc
            self._modified = True
        self._logger.info("Deleted page %s from %s", page_num + 1, self._filename)

    def rotate_page(self, page_num: int, rotation: int) -> int:
        """Set the page rotation to ``rotation`` degrees (0/90/180/270).

        Returns:
            The applied rotation.
        """
        normalized = int(rotation) % 360
        if normalized not in (0, 90, 180, 270):
            raise PageOperationError("Rotation must be 0, 90, 180, or 270 degrees.")
        with self._lock:
            self._ensure_open()
            self._validate_page_index(page_num)
            try:
                page = self._pdf.load_page(page_num)
                if int(page.rotation) == normalized:
                    return normalized
                page.set_rotation(normalized)
            except Exception as exc:  # noqa: BLE001
                self._logger.error("Rotate page %s failed: %s", page_num, exc)
                raise PageOperationError(f"Could not rotate page {page_num + 1}") from exc
            self._modified = True
        self._logger.info("Rotated page %s to %s degrees", page_num + 1, normalized)
        return normalized

    def get_page_rotation(self, page_num: int) -> int:
        """Return the stored rotation of a page in degrees."""
        with self._lock:
            page = self.get_page(page_num)
            return int(page.rotation)

    def extract_pages(self, start: int, end: int) -> fitz.Document:
        """Return a new PyMuPDF document containing pages ``start``..``end`` (inclusive)."""
        with self._lock:
            self._ensure_open()
            self._validate_page_index(start)
            self._validate_page_index(end)
            if end < start:
                raise PageOperationError(
                    "End page must be greater than or equal to start page."
                )
            try:
                new_doc = fitz.open()
                new_doc.insert_pdf(self._pdf, from_page=start, to_page=end)
            except Exception as exc:  # noqa: BLE001
                self._logger.error("Extract pages %s-%s failed: %s", start, end, exc)
                raise PageOperationError("Could not extract the requested pages.") from exc
        self._logger.info("Extracted pages %s-%s from %s", start + 1, end + 1, self._filename)
        return new_doc

    def save(self, output_path: Optional[PathLike] = None, incremental: bool = False) -> Path:
        """Save the document to ``output_path`` (or overwrite the original).

        Overwriting the original is done atomically: the edited PDF is
        serialized to memory, written to a sibling temp file, and swapped
        in with ``os.replace``. If any step fails the temp file is removed
        and the document is reopened from the in-memory copy, so the
        caller keeps both its unsaved edits and a usable handle.

        Args:
            output_path: Destination path; defaults to the original file.
            incremental: Try a fast incremental write when overwriting.

        Returns:
            The path actually written.

        Raises:
            PageOperationError: If the document could not be written.
        """
        with self._lock:
            self._ensure_open()
            target = Path(output_path).expanduser() if output_path else self._file_path
            target.parent.mkdir(parents=True, exist_ok=True)
            same_file = self._same_path(target, self._file_path)

            if not same_file:
                try:
                    self._pdf.save(
                        target, garbage=4, deflate=True, encryption=fitz.PDF_ENCRYPT_KEEP
                    )
                except Exception as exc:  # noqa: BLE001
                    self._logger.error("Save failed for %s: %s", target, exc)
                    raise PageOperationError(f"Could not save PDF to {target}") from exc
                self._file_path = target.resolve()
                self._filename = self._file_path.name
                self._modified = False
                self._logger.info("Saved PDF to %s", self._file_path)
                return self._file_path

            if incremental:
                try:
                    self._pdf.saveIncr()
                    self._modified = False
                    self._logger.info("Incrementally saved PDF to %s", self._file_path)
                    return self._file_path
                except Exception as incr_exc:  # noqa: BLE001
                    self._logger.warning(
                        "Incremental save unavailable (%s); rewriting file", incr_exc
                    )

            return self._overwrite_atomically(target)

    def _overwrite_atomically(self, target: Path) -> Path:
        """Replace ``target`` with the edited document without risking data loss."""
        tmp = target.with_name(f"{target.stem}.__pdfmaster_tmp__{target.suffix}")
        try:
            payload = self._pdf.tobytes(garbage=4, deflate=True)
        except Exception as exc:  # noqa: BLE001
            self._logger.error("Could not serialize %s: %s", self._filename, exc)
            raise PageOperationError(f"Could not save PDF to {target}") from exc

        try:
            tmp.write_bytes(payload)
            self._pdf.close()
            os.replace(tmp, target)
        except Exception as exc:  # noqa: BLE001
            self._logger.error("Atomic overwrite failed for %s: %s", target, exc)
            self._recover_from_memory(payload)
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                self._logger.warning("Could not remove temp file %s", tmp)
            raise PageOperationError(
                f"Could not save PDF to {target}. The file may be open in "
                f"another program. Your changes are still loaded, so you can "
                f"use Save As instead."
            ) from exc

        try:
            self._pdf = fitz.open(target)
            self._is_open = True
        except Exception as exc:  # noqa: BLE001
            self._logger.error("Could not reopen %s after save: %s", target, exc)
            self._recover_from_memory(payload)

        self._modified = False
        self._logger.info("Saved PDF to %s", self._file_path)
        return self._file_path

    def _recover_from_memory(self, payload: bytes) -> None:
        """Reopen the document from an in-memory copy after a failed write."""
        try:
            self._pdf = fitz.open(stream=payload, filetype="pdf")
            self._is_open = True
            self._logger.info("Recovered %s from memory after failed save", self._filename)
        except Exception as exc:  # noqa: BLE001
            self._pdf = None
            self._is_open = False
            self._logger.error("Could not recover document after failed save: %s", exc)

    @staticmethod
    def _same_path(left: Path, right: Path) -> bool:
        """Compare two paths, tolerating one of them not existing yet."""
        try:
            return left.resolve() == right.resolve()
        except OSError:
            return str(left) == str(right)

    def close(self) -> None:
        """Close the PDF handle and release resources."""
        with self._lock:
            if self._pdf is not None:
                try:
                    if not self._pdf.is_closed:
                        self._pdf.close()
                except Exception as exc:  # noqa: BLE001
                    self._logger.warning("Error while closing PDF: %s", exc)
                self._pdf = None
            self._is_open = False
        self._logger.info("Closed document %s", self._filename)

    def __enter__(self) -> "Document":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _ensure_open(self) -> None:
        if not self.is_open:
            raise PDFLoadError("The document is closed.")

    def _validate_page_index(self, page_num: int) -> None:
        count = self._pdf.page_count
        if page_num < 0 or page_num >= count:
            raise PageOperationError(f"Page {page_num + 1} is out of range (1-{count}).")
