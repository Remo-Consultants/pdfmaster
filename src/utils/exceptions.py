"""Custom exception hierarchy for PDFMaster.

Raise these instead of generic Exception so callers can handle failures
precisely and the UI can show useful messages.
"""


class PDFMasterException(Exception):
    """Base exception for every PDFMaster error.

    Catch this class when you want to handle any application-specific
    failure without also swallowing unrelated Python errors.
    """


class PDFLoadError(PDFMasterException):
    """Raised when a PDF cannot be opened or initialized.

    Typical causes: missing file, corrupt header, unsupported encryption,
    or PyMuPDF failing to parse the document.
    """


class PDFRenderError(PDFMasterException):
    """Raised when a page cannot be rendered to an image.

    Typical causes: invalid page index, out-of-memory on large pages,
    or a damaged page stream inside an otherwise valid PDF.
    """


class PageOperationError(PDFMasterException):
    """Raised when a page-level edit fails.

    Typical causes: deleting the last page, rotating an invalid index,
    or extracting a range that is outside the document.
    """


class FileOperationError(PDFMasterException):
    """Raised when a filesystem operation fails.

    Typical causes: permission errors, missing paths, disk full, or
    inability to read/write the recent-files list.
    """


class ValidationError(PDFMasterException):
    """Raised when input values fail validation.

    Typical causes: non-PDF files, empty paths, out-of-range page
    numbers, or zoom values outside the supported limits.
    """


class AnnotationError(PDFMasterException):
    """Raised when an annotation cannot be added, updated, or removed.

    Typical causes: an empty selection, coordinates outside the page, or
    an annotation type the document does not support.
    """


class ContentEditError(PDFMasterException):
    """Raised when page content cannot be edited.

    Typical causes: replacement text that will not fit its box at any
    readable size, a missing font, or an unreadable image file.
    """


class FormError(PDFMasterException):
    """Raised when a form field cannot be read or filled.

    Typical causes: the PDF has no AcroForm, an unknown field name, or a
    value that is invalid for the field type.
    """


class PrintError(PDFMasterException):
    """Raised when a document cannot be sent to a printer.

    Typical causes: no printer configured, the print job was cancelled,
    or the painter could not be started on the print device.
    """
