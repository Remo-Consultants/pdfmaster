"""Tests for the custom exception hierarchy."""

from src.utils.exceptions import (
    FileOperationError,
    PageOperationError,
    PDFLoadError,
    PDFMasterException,
    PDFRenderError,
    ValidationError,
)


def test_all_exceptions_subclass_base() -> None:
    for cls in (
        PDFLoadError,
        PDFRenderError,
        PageOperationError,
        FileOperationError,
        ValidationError,
    ):
        assert issubclass(cls, PDFMasterException)
        assert issubclass(cls, Exception)


def test_exceptions_carry_message() -> None:
    err = PDFLoadError("broken")
    assert str(err) == "broken"
