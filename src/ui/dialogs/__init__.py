"""Dialogs used by the PDFMaster main window."""

from src.ui.dialogs.export_dialog import ExportImagesDialog, parse_page_range
from src.ui.dialogs.form_dialog import FormDialog
from src.ui.dialogs.page_organizer import PageOrganizerDialog
from src.ui.dialogs.text_dialogs import (
    AddTextDialog,
    FindReplaceDialog,
    ReplaceTextDialog,
    StickyNoteDialog,
)

__all__ = [
    "AddTextDialog",
    "ExportImagesDialog",
    "FindReplaceDialog",
    "FormDialog",
    "PageOrganizerDialog",
    "ReplaceTextDialog",
    "StickyNoteDialog",
    "parse_page_range",
]
