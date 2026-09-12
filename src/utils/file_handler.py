"""Filesystem helpers and PDF file validation."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union

from src.constants import (
    MAX_RECENT_FILES,
    PDF_EXTENSIONS,
    PDF_HEADER_SEARCH_BYTES,
    PDF_MAGIC,
)
from src.utils.exceptions import FileOperationError, ValidationError
from src.utils.logger import get_logger

logger = get_logger(__name__)

PathLike = Union[str, Path]


class FileHandler:
    """Static helpers for validating, measuring, and tracking files."""

    @staticmethod
    def validate_file_exists(path: PathLike) -> Path:
        """Check that ``path`` exists and is a file.

        Args:
            path: File path to validate.

        Returns:
            The resolved ``Path``.

        Raises:
            FileOperationError: If the path is missing or not a file.
        """
        try:
            resolved = Path(path).expanduser().resolve()
        except OSError as exc:
            logger.error("Could not resolve path %s: %s", path, exc)
            raise FileOperationError(f"Invalid path: {path}") from exc

        if not resolved.exists():
            logger.error("File does not exist: %s", resolved)
            raise FileOperationError(f"File does not exist: {resolved}")
        if not resolved.is_file():
            logger.error("Path is not a file: %s", resolved)
            raise FileOperationError(f"Path is not a file: {resolved}")
        logger.debug("Validated file exists: %s", resolved)
        return resolved

    @staticmethod
    def validate_pdf(path: PathLike) -> Path:
        """Validate that ``path`` is an existing PDF (extension + magic bytes).

        Per the PDF specification the ``%PDF-`` header may be preceded by
        junk bytes, so the first kilobyte is searched rather than only
        byte zero. Real-world scanners and web servers emit such files.

        Args:
            path: Candidate PDF path.

        Returns:
            The resolved ``Path``.

        Raises:
            ValidationError: If the file is not a PDF.
            FileOperationError: If the file cannot be read.
        """
        resolved = FileHandler.validate_file_exists(path)
        if resolved.suffix.lower() not in PDF_EXTENSIONS:
            logger.warning("Rejected non-PDF extension: %s", resolved)
            raise ValidationError(f"Unsupported file type: {resolved.suffix}")

        try:
            with resolved.open("rb") as handle:
                head = handle.read(PDF_HEADER_SEARCH_BYTES)
        except OSError as exc:
            logger.error("Could not read PDF header for %s: %s", resolved, exc)
            raise FileOperationError(f"Could not read file: {resolved}") from exc

        offset = head.find(PDF_MAGIC)
        if offset < 0:
            logger.warning("No %%PDF- header found in first %s bytes of %s",
                           PDF_HEADER_SEARCH_BYTES, resolved)
            raise ValidationError(f"File is not a valid PDF: {resolved}")
        if offset > 0:
            logger.info("PDF header found at byte offset %s in %s", offset, resolved)

        logger.info("Validated PDF: %s", resolved)
        return resolved

    @staticmethod
    def ensure_pdf_suffix(path: PathLike) -> Path:
        """Return ``path`` with a ``.pdf`` suffix, adding one if missing."""
        candidate = Path(path)
        if candidate.suffix.lower() in PDF_EXTENSIONS:
            return candidate
        return candidate.with_name(candidate.name + PDF_EXTENSIONS[0])

    @staticmethod
    def get_file_size(path: PathLike) -> int:
        """Return file size in bytes.

        Raises:
            FileOperationError: If the size cannot be read.
        """
        resolved = FileHandler.validate_file_exists(path)
        try:
            size = resolved.stat().st_size
        except OSError as exc:
            logger.error("Could not stat %s: %s", resolved, exc)
            raise FileOperationError(f"Could not read file size: {resolved}") from exc
        logger.debug("File size of %s is %s bytes", resolved, size)
        return size

    @staticmethod
    def get_file_size_mb(path: PathLike) -> float:
        """Return file size in megabytes (decimal MB)."""
        return FileHandler.get_file_size(path) / (1024 * 1024)

    @staticmethod
    def ensure_directory_exists(directory: PathLike) -> Path:
        """Create ``directory`` (and parents) if it does not exist.

        Raises:
            FileOperationError: If the directory cannot be created.
        """
        target = Path(directory).expanduser()
        try:
            target.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.error("Could not create directory %s: %s", target, exc)
            raise FileOperationError(f"Could not create directory: {target}") from exc
        logger.debug("Ensured directory exists: %s", target)
        return target.resolve()

    @staticmethod
    def get_output_path(input_path: PathLike, suffix: str = "_edited") -> Path:
        """Build an output filename next to the input, inserting ``suffix``.

        Example: ``report.pdf`` + ``_edited`` -> ``report_edited.pdf``.
        """
        source = Path(input_path)
        return source.with_name(f"{source.stem}{suffix}{source.suffix}")

    @staticmethod
    def safe_delete(path: PathLike) -> bool:
        """Delete a file if it exists. Missing files are not an error.

        Returns:
            True if a file was deleted, False if it did not exist.

        Raises:
            FileOperationError: If deletion fails for another reason.
        """
        target = Path(path).expanduser()
        if not target.exists():
            logger.debug("safe_delete: file already absent: %s", target)
            return False
        if not target.is_file():
            raise FileOperationError(f"Refusing to delete non-file path: {target}")
        try:
            target.unlink()
        except OSError as exc:
            logger.error("Could not delete %s: %s", target, exc)
            raise FileOperationError(f"Could not delete file: {target}") from exc
        logger.info("Deleted file: %s", target)
        return True

    @staticmethod
    def get_recent_files(config_dir: PathLike) -> List[str]:
        """Read the recent-files list from ``config_dir``.

        Missing files yield an empty list. Entries that no longer exist
        on disk are skipped.
        """
        recent_path = Path(config_dir) / "recent_files.txt"
        if not recent_path.exists():
            logger.debug("No recent-files list at %s", recent_path)
            return []

        try:
            raw_lines = recent_path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            logger.error("Could not read recent files: %s", exc)
            raise FileOperationError("Could not read recent files list") from exc

        existing: List[str] = []
        for line in raw_lines:
            candidate = line.strip()
            if candidate and Path(candidate).is_file():
                existing.append(candidate)
        logger.debug("Loaded %s recent files", len(existing))
        return existing

    @staticmethod
    def save_recent_file(
        path: PathLike,
        config_dir: PathLike,
        max_files: int = MAX_RECENT_FILES,
    ) -> None:
        """Insert ``path`` at the top of the recent-files list.

        Duplicates are removed. The list is trimmed to ``max_files``.
        """
        resolved = FileHandler.validate_file_exists(path)
        directory = FileHandler.ensure_directory_exists(config_dir)
        recent_path = directory / "recent_files.txt"

        try:
            current = FileHandler.get_recent_files(directory)
        except FileOperationError:
            current = []

        as_text = str(resolved)
        updated = [as_text] + [item for item in current if item != as_text]
        updated = updated[: max(1, max_files)]

        try:
            recent_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
        except OSError as exc:
            logger.error("Could not write recent files: %s", exc)
            raise FileOperationError("Could not update recent files list") from exc
        logger.info("Recorded recent file: %s", resolved)

    @staticmethod
    def sanitize_path(path: PathLike) -> Path:
        """Resolve a user-supplied path and reject empty values."""
        if not str(path).strip():
            raise ValidationError("File path must not be empty")
        return Path(path).expanduser().resolve()
