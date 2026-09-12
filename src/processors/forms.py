"""Form field reading and filling (AcroForm widgets)."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

import pymupdf as fitz

from src.core.document import Document
from src.utils.exceptions import FormError
from src.utils.logger import get_logger

logger = get_logger(__name__)

TEXT = fitz.PDF_WIDGET_TYPE_TEXT
CHECKBOX = fitz.PDF_WIDGET_TYPE_CHECKBOX
RADIO = fitz.PDF_WIDGET_TYPE_RADIOBUTTON
COMBOBOX = fitz.PDF_WIDGET_TYPE_COMBOBOX
LISTBOX = fitz.PDF_WIDGET_TYPE_LISTBOX
SIGNATURE = fitz.PDF_WIDGET_TYPE_SIGNATURE

# Field types PDFMaster can actually edit in the MVP form dialog.
EDITABLE_TYPES = {TEXT, CHECKBOX, RADIO, COMBOBOX, LISTBOX}

_TRUTHY = {"yes", "on", "true", "1", "checked"}


class FormProcessor:
    """Reads and fills AcroForm fields."""

    @staticmethod
    def has_form(document: Document) -> bool:
        """Whether the document declares any form fields."""
        with document.transaction(mark_modified=False) as pdf:
            return bool(pdf.is_form_pdf)

    @staticmethod
    def list_fields(document: Document) -> List[Dict[str, Any]]:
        """Describe every form field across all pages."""
        fields: List[Dict[str, Any]] = []
        with document.transaction(mark_modified=False) as pdf:
            for page_index in range(pdf.page_count):
                page = pdf.load_page(page_index)
                for widget in page.widgets():
                    fields.append(
                        {
                            "page": page_index,
                            "name": widget.field_name or "",
                            "label": widget.field_label or "",
                            "type": widget.field_type,
                            "type_name": widget.field_type_string,
                            "value": widget.field_value,
                            "options": list(widget.choice_values or []),
                            "required": bool(
                                widget.field_flags & 2
                            ),
                            "readonly": bool(widget.field_flags & 1),
                            "rect": tuple(widget.rect),
                            "editable": widget.field_type in EDITABLE_TYPES,
                        }
                    )
        logger.debug("Found %s form field(s)", len(fields))
        return fields

    @staticmethod
    def get_values(document: Document) -> Dict[str, Any]:
        """Return a ``{field_name: value}`` mapping."""
        return {
            field["name"]: field["value"]
            for field in FormProcessor.list_fields(document)
            if field["name"]
        }

    @staticmethod
    def set_values(document: Document, values: Mapping[str, Any]) -> int:
        """Write new values into named fields.

        Unknown names are reported rather than silently ignored, because
        a typo in a field name would otherwise look like a save bug.

        Returns:
            The number of widgets updated.
        """
        if not values:
            return 0

        wanted = dict(values)
        updated = 0
        seen: set = set()

        with document.transaction() as pdf:
            for page_index in range(pdf.page_count):
                page = pdf.load_page(page_index)
                for widget in page.widgets():
                    name = widget.field_name
                    if name not in wanted:
                        continue
                    seen.add(name)
                    if widget.field_flags & 1:  # read-only
                        logger.warning("Skipping read-only field %r", name)
                        continue
                    widget.field_value = FormProcessor._coerce(widget, wanted[name])
                    widget.update()
                    updated += 1

        missing = set(wanted) - seen
        if missing:
            raise FormError(f"Unknown form field(s): {', '.join(sorted(missing))}")

        logger.info("Updated %s form field(s)", updated)
        return updated

    @staticmethod
    def _coerce(widget: fitz.Widget, value: Any) -> Any:
        """Convert a Python value into what the widget type expects."""
        kind = widget.field_type
        if kind == CHECKBOX:
            if isinstance(value, str):
                return value.strip().lower() in _TRUTHY
            return bool(value)
        if kind in (COMBOBOX, LISTBOX):
            options = list(widget.choice_values or [])
            text = "" if value is None else str(value)
            if options and text and text not in options:
                raise FormError(
                    f"{text!r} is not an option for {widget.field_name!r}. "
                    f"Valid options: {', '.join(options)}"
                )
            return text
        if kind == RADIO:
            return value if isinstance(value, str) else bool(value)
        return "" if value is None else str(value)

    @staticmethod
    def flatten(document: Document) -> None:
        """Bake field values into the page so they are no longer editable."""
        with document.transaction() as pdf:
            try:
                pdf.bake()
            except Exception as exc:  # noqa: BLE001
                raise FormError(f"Could not flatten the form: {exc}") from exc
        logger.info("Flattened form fields in %s", document.filename)
