"""Dialogs used by the PDFMaster main window."""

from src.ui.dialogs.batch_dialog import BatchDialog
from src.ui.dialogs.compare_dialog import CompareDialog, PdfaDialog
from src.ui.dialogs.export_dialog import ExportImagesDialog, parse_page_range
from src.ui.dialogs.form_dialog import FormDialog
from src.ui.dialogs.ocr_dialog import OCRDialog
from src.ui.dialogs.page_organizer import PageOrganizerDialog
from src.ui.dialogs.search_dialog import SearchDialog
from src.ui.dialogs.security_dialog import (
    PasswordPromptDialog,
    SecurityInfoDialog,
    SetPasswordDialog,
)
from src.ui.dialogs.text_dialogs import (
    AddTextDialog,
    FindReplaceDialog,
    ReplaceTextDialog,
    StickyNoteDialog,
)
from src.ui.dialogs.watermark_dialog import StampDialog, WatermarkDialog

__all__ = [
    "AddTextDialog",
    "BatchDialog",
    "CompareDialog",
    "ExportImagesDialog",
    "FindReplaceDialog",
    "FormDialog",
    "OCRDialog",
    "PageOrganizerDialog",
    "PasswordPromptDialog",
    "PdfaDialog",
    "ReplaceTextDialog",
    "SearchDialog",
    "SecurityInfoDialog",
    "SetPasswordDialog",
    "StampDialog",
    "StickyNoteDialog",
    "WatermarkDialog",
    "parse_page_range",
]
