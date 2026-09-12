"""Tests for the undo/redo history."""

from __future__ import annotations

import pytest

from src.core.document import Document
from src.core.history import DocumentHistory
from src.processors.content import ContentEditor
from src.processors.page_ops import PageOrganizer


def test_new_history_is_empty() -> None:
    history = DocumentHistory()
    assert history.can_undo is False
    assert history.can_redo is False
    assert history.depth == 0


def test_undo_restores_previous_page_count(make_pdf) -> None:
    history = DocumentHistory()
    with Document(make_pdf(pages=3)) as doc:
        history.record(doc)
        PageOrganizer.delete_pages(doc, [0])
        assert doc.page_count == 2

        assert history.undo(doc) is True
        assert doc.page_count == 3
        assert doc.get_page_text(0).strip() == "Page 1"


def test_redo_reapplies_the_edit(make_pdf) -> None:
    history = DocumentHistory()
    with Document(make_pdf(pages=3)) as doc:
        history.record(doc)
        PageOrganizer.delete_pages(doc, [0])
        history.undo(doc)
        assert doc.page_count == 3

        assert history.redo(doc) is True
        assert doc.page_count == 2
        assert history.can_redo is False


def test_undo_and_redo_return_false_when_empty(make_pdf) -> None:
    history = DocumentHistory()
    with Document(make_pdf(pages=1)) as doc:
        assert history.undo(doc) is False
        assert history.redo(doc) is False


def test_new_edit_clears_the_redo_stack(make_pdf) -> None:
    history = DocumentHistory()
    with Document(make_pdf(pages=4)) as doc:
        history.record(doc)
        PageOrganizer.delete_pages(doc, [0])
        history.undo(doc)
        assert history.can_redo is True

        history.record(doc)
        assert history.can_redo is False


def test_multiple_undo_steps(make_pdf) -> None:
    history = DocumentHistory()
    with Document(make_pdf(pages=5)) as doc:
        for _ in range(3):
            history.record(doc)
            PageOrganizer.delete_pages(doc, [0])
        assert doc.page_count == 2
        assert history.depth == 3

        for expected in (3, 4, 5):
            assert history.undo(doc) is True
            assert doc.page_count == expected
        assert history.can_undo is False


def test_history_respects_step_limit(make_pdf) -> None:
    history = DocumentHistory(max_steps=2)
    with Document(make_pdf(pages=8)) as doc:
        for _ in range(5):
            history.record(doc)
            PageOrganizer.delete_pages(doc, [0])
        assert history.depth == 2


def test_history_respects_byte_budget(make_pdf) -> None:
    history = DocumentHistory(max_steps=50, max_bytes=1)
    with Document(make_pdf(pages=4)) as doc:
        history.record(doc)
        history.record(doc)
        # Every snapshot exceeds the budget, so only the newest survives.
        assert history.depth <= 1


def test_clear_drops_everything(make_pdf) -> None:
    history = DocumentHistory()
    with Document(make_pdf(pages=3)) as doc:
        history.record(doc)
        PageOrganizer.delete_pages(doc, [0])
        history.undo(doc)
        history.clear()
        assert history.can_undo is False
        assert history.can_redo is False


def test_undo_restores_content_edits(make_text_pdf) -> None:
    history = DocumentHistory()
    with Document(make_text_pdf()) as doc:
        history.record(doc)
        span = ContentEditor.find_spans(doc, 0)[0]
        ContentEditor.replace_text(doc, 0, span["bbox"], "Completely New Line")
        assert "Completely New Line" in doc.get_page_text(0)

        history.undo(doc)
        text = doc.get_page_text(0)
        assert "Completely New Line" not in text
        assert "Invoice Date" in text


def test_document_remains_usable_after_undo(make_pdf) -> None:
    history = DocumentHistory()
    with Document(make_pdf(pages=3)) as doc:
        history.record(doc)
        PageOrganizer.delete_pages(doc, [0])
        history.undo(doc)
        # The handle was swapped underneath; rendering must still work.
        image = doc.render_page_to_image(0, zoom=1.0)
        assert image.width > 0
        assert doc.is_open
