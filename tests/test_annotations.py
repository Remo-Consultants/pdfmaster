"""Tests for the annotation processor."""

from __future__ import annotations

import pytest

from src.core.document import Document
from src.processors.annotations import AnnotationProcessor, resolve_color
from src.utils.exceptions import AnnotationError


def test_resolve_color_names_and_tuples() -> None:
    assert resolve_color("yellow", "red") == pytest.approx((1.0, 0.92, 0.23))
    assert resolve_color(None, "black") == (0.0, 0.0, 0.0)
    assert resolve_color((0.1, 0.2, 0.3), "black") == (0.1, 0.2, 0.3)
    with pytest.raises(AnnotationError):
        resolve_color("chartreuse", "black")
    with pytest.raises(AnnotationError):
        resolve_color((2.0, 0.0, 0.0), "black")


def test_words_in_rect_selects_overlapping_words(make_text_pdf) -> None:
    with Document(make_text_pdf()) as doc:
        # A generous band across the first line.
        hits = AnnotationProcessor.words_in_rect(doc, 0, (60, 85, 400, 105))
        assert hits, "expected to select words on the first line"
        empty = AnnotationProcessor.words_in_rect(doc, 0, (400, 700, 500, 720))
        assert empty == []


@pytest.mark.parametrize("kind", ["highlight", "underline", "strikeout", "squiggly"])
def test_markup_types(make_text_pdf, kind: str) -> None:
    with Document(make_text_pdf()) as doc:
        count = AnnotationProcessor.add_markup(doc, 0, (60, 85, 400, 105), kind=kind)
        assert count > 0
        annots = AnnotationProcessor.list_annotations(doc, 0)
        assert len(annots) == 1
        assert doc.is_modified


def test_markup_without_text_raises(make_text_pdf) -> None:
    with Document(make_text_pdf()) as doc:
        with pytest.raises(AnnotationError):
            AnnotationProcessor.add_markup(doc, 0, (400, 700, 500, 720))


def test_unknown_markup_kind(make_text_pdf) -> None:
    with Document(make_text_pdf()) as doc:
        with pytest.raises(AnnotationError):
            AnnotationProcessor.add_markup(doc, 0, (60, 85, 400, 105), kind="glitter")


def test_sticky_note(make_text_pdf) -> None:
    with Document(make_text_pdf()) as doc:
        AnnotationProcessor.add_sticky_note(doc, 0, (300, 300), "check this figure")
        annots = AnnotationProcessor.list_annotations(doc, 0)
        assert annots[0]["type"] == "Text"
        assert annots[0]["content"] == "check this figure"
        with pytest.raises(AnnotationError):
            AnnotationProcessor.add_sticky_note(doc, 0, (10, 10), "   ")


def test_ink_annotation(make_text_pdf) -> None:
    with Document(make_text_pdf()) as doc:
        AnnotationProcessor.add_ink(doc, 0, [[(50, 50), (60, 70), (80, 90)]])
        assert AnnotationProcessor.list_annotations(doc, 0)[0]["type"] == "Ink"
        with pytest.raises(AnnotationError):
            AnnotationProcessor.add_ink(doc, 0, [[(1, 1)]])


@pytest.mark.parametrize("shape", ["rect", "ellipse"])
def test_shapes(make_text_pdf, shape: str) -> None:
    with Document(make_text_pdf()) as doc:
        AnnotationProcessor.add_shape(doc, 0, (100, 400, 300, 500), shape=shape)
        assert len(AnnotationProcessor.list_annotations(doc, 0)) == 1


def test_delete_and_clear(make_text_pdf) -> None:
    with Document(make_text_pdf()) as doc:
        AnnotationProcessor.add_sticky_note(doc, 0, (100, 100), "one")
        AnnotationProcessor.add_sticky_note(doc, 0, (200, 200), "two")
        assert len(AnnotationProcessor.list_annotations(doc, 0)) == 2

        AnnotationProcessor.delete_annotation(doc, 0, 0)
        remaining = AnnotationProcessor.list_annotations(doc, 0)
        assert len(remaining) == 1
        assert remaining[0]["content"] == "two"

        with pytest.raises(AnnotationError):
            AnnotationProcessor.delete_annotation(doc, 0, 9)

        assert AnnotationProcessor.clear_page(doc, 0) == 1
        assert AnnotationProcessor.list_annotations(doc, 0) == []


def test_delete_annotations_at_point(make_text_pdf) -> None:
    with Document(make_text_pdf()) as doc:
        AnnotationProcessor.add_shape(doc, 0, (100, 400, 300, 500))
        assert AnnotationProcessor.delete_annotations_at(doc, 0, (500, 600)) == 0
        assert AnnotationProcessor.delete_annotations_at(doc, 0, (200, 450)) == 1


def test_annotations_survive_save(make_text_pdf, tmp_path) -> None:
    source = make_text_pdf()
    with Document(source) as doc:
        AnnotationProcessor.add_markup(doc, 0, (60, 85, 400, 105))
        doc.save(incremental=False)
    with Document(source) as reopened:
        assert len(AnnotationProcessor.list_annotations(reopened, 0)) == 1


def test_flatten_bakes_annotations(make_text_pdf) -> None:
    with Document(make_text_pdf()) as doc:
        AnnotationProcessor.add_markup(doc, 0, (60, 85, 400, 105))
        AnnotationProcessor.flatten(doc)
        assert AnnotationProcessor.list_annotations(doc, 0) == []


def test_annotation_on_rotated_page(make_text_pdf) -> None:
    """Markup must still land on the words after the page is rotated."""
    with Document(make_text_pdf()) as doc:
        doc.rotate_page(0, 90)
        count = AnnotationProcessor.add_markup(doc, 0, (60, 85, 400, 105))
        assert count > 0
