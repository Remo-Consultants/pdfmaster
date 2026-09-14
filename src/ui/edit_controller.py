"""Coordinates editing actions between the UI, processors, and history.

The main window stays responsible for widgets and menus; this class owns
the "what happens when the user finishes a drag" logic, keeps the undo
history, and makes sure the viewer refreshes afterwards.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

from PySide6.QtWidgets import QFileDialog, QMessageBox

from src.constants import (
    APP_NAME,
    DEFAULT_HIGHLIGHT_COLOR,
    DEFAULT_INK_COLOR,
    IMAGE_IMPORT_FILTER,
    MSG_ANNOT_ADDED,
    MSG_EXPORTED,
    MSG_FORM_SAVED,
    MSG_NO_DOCUMENT,
    MSG_NO_FORM,
    MSG_NOTHING_TO_REDO,
    MSG_NOTHING_TO_UNDO,
    MSG_PRINT_CANCELLED,
    MSG_PRINT_SENT,
    MSG_REDACTED,
    MSG_REDONE,
    MSG_TEXT_NOT_FOUND,
    MSG_TEXT_REPLACED,
    MSG_UNDONE,
)
from src.core.history import DocumentHistory
from src.processors.annotations import AnnotationProcessor
from src.processors.content import ContentEditor
from src.processors.forms import FormProcessor
from src.processors.redaction import Redactor
from src.processors.watermark import WatermarkProcessor
from src.services.print_service import PrintService
from src.services.security_service import SignatureService
from src.ui.dialogs import (
    AddTextDialog,
    ExportImagesDialog,
    FindReplaceDialog,
    FormDialog,
    PageOrganizerDialog,
    ReplaceTextDialog,
    StampDialog,
    StickyNoteDialog,
    WatermarkDialog,
)
from src.ui.tools import ToolMode
from src.utils.exceptions import PDFMasterException
from src.utils.logger import get_logger

logger = get_logger(__name__)

RectLike = Tuple[float, float, float, float]


class EditController:
    """Applies editing tools to the open document on behalf of the window."""

    def __init__(self, window) -> None:
        self._window = window
        self.highlight_color = DEFAULT_HIGHLIGHT_COLOR
        self.ink_color = DEFAULT_INK_COLOR

    # ------------------------------------------------------------------
    # Plumbing
    # ------------------------------------------------------------------
    @property
    def document(self):
        return self._window.document

    @property
    def history(self) -> Optional[DocumentHistory]:
        """The history for the current tab, or None if no tab is open."""
        return self._window.history

    def reset(self) -> None:
        """Forget the undo history, e.g. when another file is opened."""
        if self.history:
            self.history.clear()
        self._window.update_history_actions()

    def _begin_edit(self) -> None:
        """Snapshot the document so the next change can be undone."""
        if self.document is not None and self.history is not None:
            self.history.record(self.document)

    def _finish(self, message: str) -> None:
        self._window.refresh_after_edit()
        self._window.statusBar().showMessage(message)
        self._window.update_history_actions()

    def _warn(self, message: str) -> None:
        self._window.statusBar().showMessage(message)
        QMessageBox.warning(self._window, APP_NAME, message)

    def _require_document(self) -> bool:
        if self.document is None:
            self._window.statusBar().showMessage(MSG_NO_DOCUMENT)
            return False
        return True

    # ------------------------------------------------------------------
    # Undo / redo
    # ------------------------------------------------------------------
    def undo(self) -> None:
        if not self._require_document():
            return
        if self.history is None or not self.history.undo(self.document):
            self._window.statusBar().showMessage(MSG_NOTHING_TO_UNDO)
            return
        self._finish(MSG_UNDONE)

    def redo(self) -> None:
        if not self._require_document():
            return
        if self.history is None or not self.history.redo(self.document):
            self._window.statusBar().showMessage(MSG_NOTHING_TO_REDO)
            return
        self._finish(MSG_REDONE)

    # ------------------------------------------------------------------
    # Tool dispatch
    # ------------------------------------------------------------------
    def handle_area(self, tool: ToolMode, page: int, rect: RectLike) -> None:
        """Apply the active drag tool to the selected rectangle.

        The page comes from the viewer rather than from "current page",
        because in continuous mode a drag can land on any visible page.
        """
        if not self._require_document():
            return
        try:
            handler = {
                ToolMode.HIGHLIGHT: self._markup,
                ToolMode.UNDERLINE: self._markup,
                ToolMode.STRIKEOUT: self._markup,
                ToolMode.SHAPE: self._shape,
                ToolMode.TEXT: self._add_text,
                ToolMode.IMAGE: self._add_image,
                ToolMode.EDIT_TEXT: self._edit_text,
                ToolMode.REDACT: self._redact,
                ToolMode.ERASE: self._erase,
            }[tool]
        except KeyError:
            logger.debug("No area handler for tool %s", tool)
            return

        try:
            handler(page, rect, tool)
        except PDFMasterException as exc:
            self._warn(str(exc))

    def handle_point(
        self, tool: ToolMode, page: int, point: Tuple[float, float]
    ) -> None:
        """Apply the active click tool at the given page point."""
        if not self._require_document():
            return
        try:
            if tool == ToolMode.NOTE:
                self._add_note(page, point)
            elif tool == ToolMode.DELETE_ANNOT:
                self._delete_annotation(page, point)
        except PDFMasterException as exc:
            self._warn(str(exc))

    def handle_ink(
        self, page: int, strokes: Sequence[Sequence[Tuple[float, float]]]
    ) -> None:
        """Store a freehand drawing."""
        if not self._require_document():
            return
        try:
            self._begin_edit()
            AnnotationProcessor.add_ink(
                self.document, page, strokes, color=self.ink_color
            )
        except PDFMasterException as exc:
            self._warn(str(exc))
            return
        self._finish(MSG_ANNOT_ADDED.format(kind="drawing", page=page + 1))

    # ------------------------------------------------------------------
    # Individual tools
    # ------------------------------------------------------------------
    def _markup(self, page: int, rect: RectLike, tool: ToolMode) -> None:
        self._begin_edit()
        count = AnnotationProcessor.add_markup(
            self.document, page, rect, kind=tool.value, color=self.highlight_color
        )
        self._finish(
            MSG_ANNOT_ADDED.format(kind=f"{tool.value} ({count} words)", page=page + 1)
        )

    def _shape(self, page: int, rect: RectLike, _tool: ToolMode) -> None:
        self._begin_edit()
        AnnotationProcessor.add_shape(self.document, page, rect, color=self.ink_color)
        self._finish(MSG_ANNOT_ADDED.format(kind="rectangle", page=page + 1))

    def _add_note(self, page: int, point: Tuple[float, float]) -> None:
        existing = AnnotationProcessor.find_text_annotation_at(
            self.document, page, point
        )
        if existing is not None:
            dialog = StickyNoteDialog(
                self._window,
                text=existing.get("content", ""),
                editing=True,
            )
            if dialog.exec() != StickyNoteDialog.DialogCode.Accepted:
                return
            text = dialog.text()
            if not text.strip():
                return
            self._begin_edit()
            AnnotationProcessor.update_sticky_note(
                self.document, page, int(existing["index"]), text
            )
            self._finish(f"Updated note on page {page + 1}")
            return

        dialog = StickyNoteDialog(self._window)
        if dialog.exec() != StickyNoteDialog.DialogCode.Accepted:
            return
        text = dialog.text()
        if not text.strip():
            return
        self._begin_edit()
        AnnotationProcessor.add_sticky_note(self.document, page, point, text)
        self._finish(MSG_ANNOT_ADDED.format(kind="note", page=page + 1))

    def _delete_annotation(self, page: int, point: Tuple[float, float]) -> None:
        self._begin_edit()
        removed = AnnotationProcessor.delete_annotations_at(self.document, page, point)
        if not removed:
            self._window.statusBar().showMessage("No markup at that spot.")
            return
        self._finish(f"Deleted {removed} markup item(s)")

    def delete_annotation_at_index(self, page: int, index: int) -> None:
        """Delete one annotation chosen from the properties panel list."""
        if not self._require_document():
            return
        try:
            self._begin_edit()
            AnnotationProcessor.delete_annotation(self.document, page, index)
        except PDFMasterException as exc:
            self._warn(str(exc))
            return
        self._finish(f"Deleted markup from page {page + 1}")

    def _add_text(self, page: int, rect: RectLike, _tool: ToolMode) -> None:
        dialog = AddTextDialog(self._window)
        if dialog.exec() != AddTextDialog.DialogCode.Accepted:
            return
        values = dialog.result_values()
        if not values["text"].strip():
            return
        self._begin_edit()
        ContentEditor.add_text(
            self.document,
            page,
            rect,
            values["text"],
            font=values["font"],
            size=values["size"],
            color=values["color"],
        )
        self._finish(f"Added text to page {page + 1}")

    def _add_image(self, page: int, rect: RectLike, _tool: ToolMode) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self._window, "Choose an image", str(Path.home()), IMAGE_IMPORT_FILTER
        )
        if not path:
            return
        self._begin_edit()
        ContentEditor.add_image(self.document, page, rect, path)
        self._finish(f"Added image to page {page + 1}")

    def _edit_text(self, page: int, rect: RectLike, _tool: ToolMode) -> None:
        spans = ContentEditor.find_spans(self.document, page, rect)
        if not spans:
            self._warn(MSG_TEXT_NOT_FOUND)
            return
        original = " ".join(span["text"] for span in spans).strip()
        size = spans[0]["size"]

        dialog = ReplaceTextDialog(original, size=size, parent=self._window)
        if dialog.exec() != ReplaceTextDialog.DialogCode.Accepted:
            return
        values = dialog.result_values()
        if values["text"] == original:
            return

        self._begin_edit()
        report = ContentEditor.replace_text(
            self.document,
            page,
            rect,
            values["text"],
            font=values["font"],
            size=values["size"],
            color=values["color"],
        )
        self._finish(MSG_TEXT_REPLACED.format(page=page + 1))
        self._report_substitution(report)

    def _report_substitution(self, report: Dict[str, Any]) -> None:
        notes = []
        if report.get("substituted"):
            notes.append(
                f"The original font ({report['original_font']}) is not embedded, "
                f"so a standard font was used instead."
            )
        if report.get("shrunk"):
            notes.append(
                f"The text was shrunk from {report['original_size']}pt to "
                f"{report['size']}pt so it would fit."
            )
        if notes:
            QMessageBox.information(self._window, "Text replaced", "\n\n".join(notes))

    def _redact(self, page: int, rect: RectLike, _tool: ToolMode) -> None:
        preview = Redactor.preview_text(self.document, page, [rect])
        detail = f"\n\nThis will permanently remove:\n{preview[0][:200]}" if preview else ""
        confirm = QMessageBox.warning(
            self._window,
            "Redact content",
            "Redaction permanently deletes the content in the selected area. "
            "It cannot be recovered from the saved file." + detail,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._begin_edit()
        count = Redactor.redact_areas(self.document, page, [rect])
        self._finish(MSG_REDACTED.format(count=count, page=page + 1))

    def _erase(self, page: int, rect: RectLike, _tool: ToolMode) -> None:
        self._begin_edit()
        ContentEditor.erase_area(self.document, page, rect)
        self._finish(f"Erased an area on page {page + 1}")

    # ------------------------------------------------------------------
    # Menu-driven actions
    # ------------------------------------------------------------------
    def organize_pages(self) -> None:
        if not self._require_document():
            return
        dialog = PageOrganizerDialog(self.document, self._begin_edit, self._window)
        dialog.document_changed.connect(
            lambda: self._finish("Page structure updated")
        )
        dialog.exec()
        self._window.refresh_after_edit()

    def fill_form(self) -> None:
        if not self._require_document():
            return
        if not FormProcessor.has_form(self.document):
            QMessageBox.information(self._window, APP_NAME, MSG_NO_FORM)
            return
        self._begin_edit()
        dialog = FormDialog(self.document, self._window)
        if dialog.exec() != FormDialog.DialogCode.Accepted:
            return
        self._finish(MSG_FORM_SAVED.format(count=getattr(dialog, "updated_count", 0)))

    def find_and_replace(self) -> None:
        if not self._require_document():
            return
        dialog = FindReplaceDialog(
            self.document.page_count, self._window.viewer.current_page, self._window
        )
        if dialog.exec() != FindReplaceDialog.DialogCode.Accepted:
            return
        values = dialog.result_values()
        if not values["search"]:
            return

        pages = (
            range(self.document.page_count)
            if values["all_pages"]
            else [self._window.viewer.current_page]
        )
        self._begin_edit()
        replaced = 0
        try:
            for page in pages:
                replaced += ContentEditor.replace_matching_text(
                    self.document, page, values["search"], values["replacement"]
                )
        except PDFMasterException as exc:
            self._warn(str(exc))
            return

        if not replaced:
            self._window.statusBar().showMessage(
                f"'{values['search']}' was not found."
            )
            return
        self._finish(f"Replaced {replaced} occurrence(s)")

    def flatten_document(self) -> None:
        if not self._require_document():
            return
        confirm = QMessageBox.question(
            self._window,
            "Flatten document",
            "Flattening bakes annotations and form values into the page. "
            "They will no longer be editable. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._begin_edit()
        try:
            AnnotationProcessor.flatten(self.document)
        except PDFMasterException as exc:
            self._warn(str(exc))
            return
        self._finish("Flattened annotations and form fields")

    def clear_page_markup(self) -> None:
        if not self._require_document():
            return
        page = self._window.viewer.current_page
        self._begin_edit()
        removed = AnnotationProcessor.clear_page(self.document, page)
        self._finish(f"Removed {removed} markup item(s) from page {page + 1}")

    def add_watermark(self) -> None:
        """Open the watermark dialog and apply to selected pages."""
        if not self._require_document():
            return
        dialog = WatermarkDialog(
            self.document.page_count,
            self._window.viewer.current_page if self._window.viewer else 0,
            self._window,
        )
        if dialog.exec() != WatermarkDialog.DialogCode.Accepted:
            return
        values = dialog.result_values()
        if not values["text"]:
            self._warn("Enter watermark text first.")
            return
        pages = values["pages"]
        if pages is not None and not pages:
            self._warn("No valid pages in that range.")
            return
        try:
            self._begin_edit()
            count = WatermarkProcessor.add_text_watermark(
                self.document,
                values["text"],
                pages=pages,
                fontsize=values["fontsize"],
                angle=values["angle"],
                opacity=values["opacity"],
            )
        except PDFMasterException as exc:
            self._warn(str(exc))
            return
        self._finish(f"Watermark added to {count} page(s)")

    def add_stamp(self) -> None:
        """Open the stamp dialog and place a text or image stamp."""
        if not self._require_document():
            return
        dialog = StampDialog(self._window)
        if dialog.exec() != StampDialog.DialogCode.Accepted:
            return
        values = dialog.result_values()
        page = self._window.viewer.current_page if self._window.viewer else 0
        if values["kind"] == "image":
            path = values.get("image_path") or ""
            if not path:
                self._warn("Choose an image file for the stamp.")
                return
        elif not values["text"]:
            self._warn("Enter stamp text first.")
            return
        try:
            self._begin_edit()
            if values["kind"] == "image":
                WatermarkProcessor.add_image_stamp(
                    self.document, page, values["image_path"]
                )
                kind = "image stamp"
            else:
                WatermarkProcessor.add_text_stamp(
                    self.document, page, values["text"]
                )
                kind = "text stamp"
        except PDFMasterException as exc:
            self._warn(str(exc))
            return
        self._finish(f"Added {kind} on page {page + 1}")

    def add_signature_field(self, field_name: str = "Signature") -> None:
        """Place an empty digital-signature field on the current page."""
        if not self._require_document():
            return
        if self._window.viewer is None:
            return
        name = (field_name or "").strip() or "Signature"
        page = self._window.viewer.current_page
        with self.document.transaction(mark_modified=False) as pdf:
            rect = pdf.load_page(page).rect
        width, height = 220.0, 56.0
        cx = (rect.x0 + rect.x1) / 2.0
        cy = (rect.y0 + rect.y1) / 2.0
        area = (
            cx - width / 2,
            cy - height / 2,
            cx + width / 2,
            cy + height / 2,
        )
        try:
            self._begin_edit()
            SignatureService.add_signature_field(
                self.document, page, area, field_name=name
            )
        except PDFMasterException as exc:
            self._warn(str(exc))
            return
        self._finish(f"Added signature field '{name}' on page {page + 1}")

    # ------------------------------------------------------------------
    # Printing and export
    # ------------------------------------------------------------------
    def print_document(self) -> None:
        if not self._require_document():
            return
        try:
            printed = PrintService.print_with_dialog(
                self.document, self._window, self._window.viewer.current_page
            )
        except PDFMasterException as exc:
            self._warn(str(exc))
            return
        if not printed:
            self._window.statusBar().showMessage(MSG_PRINT_CANCELLED)
            return
        self._window.statusBar().showMessage(
            MSG_PRINT_SENT.format(pages=printed, printer=PrintService.default_printer())
        )

    def print_preview(self) -> None:
        if not self._require_document():
            return
        try:
            PrintService.show_preview(
                self.document, self._window, self._window.viewer.current_page
            )
        except PDFMasterException as exc:
            self._warn(str(exc))

    def export_images(self) -> None:
        if not self._require_document():
            return
        dialog = ExportImagesDialog(
            self.document.page_count, self.document.file_path.parent, self._window
        )
        if dialog.exec() != ExportImagesDialog.DialogCode.Accepted:
            return
        values = dialog.result_values()
        try:
            written = PrintService.export_images(
                self.document,
                values["folder"],
                pages=values["pages"],
                dpi=values["dpi"],
                image_format=values["format"],
            )
        except PDFMasterException as exc:
            self._warn(str(exc))
            return
        self._window.statusBar().showMessage(
            MSG_EXPORTED.format(count=len(written), folder=values["folder"])
        )
