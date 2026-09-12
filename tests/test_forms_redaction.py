"""Tests for form filling and redaction."""

from __future__ import annotations

import pytest

from src.core.document import Document
from src.processors.forms import FormProcessor
from src.processors.redaction import Redactor
from src.utils.exceptions import AnnotationError, FormError


# ----------------------------------------------------------------------
# Forms
# ----------------------------------------------------------------------
def test_detects_forms(make_form_pdf, make_pdf) -> None:
    with Document(make_form_pdf()) as doc:
        assert FormProcessor.has_form(doc) is True
    with Document(make_pdf(pages=1)) as plain:
        assert FormProcessor.has_form(plain) is False


def test_list_fields(make_form_pdf) -> None:
    with Document(make_form_pdf()) as doc:
        fields = {f["name"]: f for f in FormProcessor.list_fields(doc)}
        assert set(fields) == {"customer", "agree", "plan"}
        assert fields["customer"]["type_name"] == "Text"
        assert fields["plan"]["options"] == ["basic", "pro", "enterprise"]
        assert all(f["editable"] for f in fields.values())


def test_get_and_set_values(make_form_pdf) -> None:
    with Document(make_form_pdf()) as doc:
        assert FormProcessor.get_values(doc)["customer"] == "initial"
        updated = FormProcessor.set_values(
            doc, {"customer": "Dinesh", "agree": True, "plan": "pro"}
        )
        assert updated == 3
        values = FormProcessor.get_values(doc)
        assert values["customer"] == "Dinesh"
        assert values["plan"] == "pro"
        assert values["agree"] not in ("Off", False)
        assert doc.is_modified


def test_set_values_unknown_field(make_form_pdf) -> None:
    with Document(make_form_pdf()) as doc:
        with pytest.raises(FormError, match="Unknown form field"):
            FormProcessor.set_values(doc, {"not_a_field": "x"})


def test_set_values_invalid_choice(make_form_pdf) -> None:
    with Document(make_form_pdf()) as doc:
        with pytest.raises(FormError, match="not an option"):
            FormProcessor.set_values(doc, {"plan": "platinum"})


def test_set_values_empty_is_noop(make_form_pdf) -> None:
    with Document(make_form_pdf()) as doc:
        assert FormProcessor.set_values(doc, {}) == 0


def test_checkbox_accepts_strings(make_form_pdf) -> None:
    with Document(make_form_pdf()) as doc:
        FormProcessor.set_values(doc, {"agree": "yes"})
        assert FormProcessor.get_values(doc)["agree"] not in ("Off", False)


def test_form_values_persist_after_save(make_form_pdf) -> None:
    source = make_form_pdf()
    with Document(source) as doc:
        FormProcessor.set_values(doc, {"customer": "Persisted Name"})
        doc.save(incremental=False)
    with Document(source) as reopened:
        assert FormProcessor.get_values(reopened)["customer"] == "Persisted Name"


def test_flatten_form(make_form_pdf) -> None:
    with Document(make_form_pdf()) as doc:
        FormProcessor.set_values(doc, {"customer": "Flattened"})
        FormProcessor.flatten(doc)
        assert FormProcessor.list_fields(doc) == []


# ----------------------------------------------------------------------
# Redaction
# ----------------------------------------------------------------------
def test_redact_area_removes_text(make_text_pdf) -> None:
    from src.processors.content import ContentEditor

    with Document(make_text_pdf()) as doc:
        span = next(s for s in ContentEditor.find_spans(doc, 0)
                    if s["text"].startswith("SECRET"))
        assert Redactor.redact_areas(doc, 0, [span["bbox"]]) == 1
        assert "SECRET" not in doc.get_page_text(0)
        assert doc.is_modified


def test_redact_requires_area(make_text_pdf) -> None:
    with Document(make_text_pdf()) as doc:
        with pytest.raises(AnnotationError):
            Redactor.redact_areas(doc, 0, [])
        with pytest.raises(AnnotationError):
            Redactor.redact_areas(doc, 0, [(10, 10, 10, 10)])


def test_redact_text_across_pages(make_pdf) -> None:
    with Document(make_pdf(pages=3)) as doc:
        removed = Redactor.redact_text(doc, "Page 2")
        assert removed == 1
        assert "Page 2" not in doc.get_page_text(1)
        assert "Page 1" in doc.get_page_text(0)


def test_redact_text_requires_input(make_pdf) -> None:
    with Document(make_pdf(pages=1)) as doc:
        with pytest.raises(AnnotationError):
            Redactor.redact_text(doc, "   ")


def test_redact_preview(make_text_pdf) -> None:
    from src.processors.content import ContentEditor

    with Document(make_text_pdf()) as doc:
        span = ContentEditor.find_spans(doc, 0)[0]
        preview = Redactor.preview_text(doc, 0, [span["bbox"]])
        assert preview and "Invoice" in preview[0]
        # Preview must not modify the document.
        assert not doc.is_modified


def test_redaction_is_permanent_after_save(make_text_pdf) -> None:
    from src.processors.content import ContentEditor

    source = make_text_pdf()
    with Document(source) as doc:
        span = next(s for s in ContentEditor.find_spans(doc, 0)
                    if s["text"].startswith("SECRET"))
        Redactor.redact_areas(doc, 0, [span["bbox"]])
        doc.save(incremental=False)
    raw = source.read_bytes()
    with Document(source) as reopened:
        assert "SECRET" not in reopened.get_page_text(0)
    assert b"SECRET reference" not in raw, "redacted text must not survive in the file"
