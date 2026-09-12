"""Unit tests for FileHandler and validation helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.utils.exceptions import FileOperationError, ValidationError
from src.utils.file_handler import FileHandler


def test_validate_file_exists(tmp_path: Path) -> None:
    missing = tmp_path / "missing.pdf"
    with pytest.raises(FileOperationError):
        FileHandler.validate_file_exists(missing)

    present = tmp_path / "present.txt"
    present.write_text("ok", encoding="utf-8")
    assert FileHandler.validate_file_exists(present) == present.resolve()


def test_validate_pdf_rejects_non_pdf(tmp_path: Path) -> None:
    text_file = tmp_path / "notes.txt"
    text_file.write_text("not a pdf", encoding="utf-8")
    with pytest.raises(ValidationError):
        FileHandler.validate_pdf(text_file)


def test_validate_pdf_rejects_bad_magic(tmp_path: Path) -> None:
    fake = tmp_path / "fake.pdf"
    fake.write_bytes(b"XXXX-this-is-not-a-pdf")
    with pytest.raises(ValidationError):
        FileHandler.validate_pdf(fake)


def test_validate_pdf_accepts_magic(tmp_path: Path) -> None:
    realish = tmp_path / "ok.pdf"
    realish.write_bytes(b"%PDF-1.7\n%stub")
    assert FileHandler.validate_pdf(realish) == realish.resolve()


def test_file_size_helpers(tmp_path: Path) -> None:
    payload = b"a" * 2048
    file_path = tmp_path / "blob.bin"
    file_path.write_bytes(payload)
    assert FileHandler.get_file_size(file_path) == 2048
    assert FileHandler.get_file_size_mb(file_path) == pytest.approx(2048 / (1024 * 1024))


def test_get_output_path() -> None:
    source = Path("C:/docs/report.pdf")
    assert FileHandler.get_output_path(source, "_edited").name == "report_edited.pdf"


def test_ensure_directory_exists(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b" / "c"
    created = FileHandler.ensure_directory_exists(nested)
    assert created.is_dir()


def test_safe_delete(tmp_path: Path) -> None:
    target = tmp_path / "gone.txt"
    target.write_text("x", encoding="utf-8")
    assert FileHandler.safe_delete(target) is True
    assert FileHandler.safe_delete(target) is False


def test_recent_files_roundtrip(tmp_path: Path) -> None:
    first = tmp_path / "one.pdf"
    second = tmp_path / "two.pdf"
    first.write_bytes(b"%PDF-1.4")
    second.write_bytes(b"%PDF-1.4")
    config = tmp_path / "config"
    FileHandler.save_recent_file(first, config, max_files=5)
    FileHandler.save_recent_file(second, config, max_files=5)
    FileHandler.save_recent_file(first, config, max_files=5)
    recent = FileHandler.get_recent_files(config)
    assert recent[0] == str(first.resolve())
    assert recent[1] == str(second.resolve())
    assert len(recent) == 2
