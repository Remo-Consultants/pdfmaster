"""Tests for page organisation operations."""

from __future__ import annotations

import pytest

from src.core.document import Document
from src.processors.page_ops import PageOrganizer
from src.utils.exceptions import PageOperationError, ValidationError


def _labels(document: Document):
    return [document.get_page_text(i).strip() for i in range(document.page_count)]


def test_move_page_forward_and_back(make_pdf) -> None:
    with Document(make_pdf(pages=4)) as doc:
        PageOrganizer.move_page(doc, 0, 2)
        assert _labels(doc) == ["Page 2", "Page 3", "Page 1", "Page 4"]
        PageOrganizer.move_page(doc, 2, 0)
        assert _labels(doc) == ["Page 1", "Page 2", "Page 3", "Page 4"]


def test_move_page_to_last_position(make_pdf) -> None:
    """Landing on the final slot has no 'insert before' index."""
    with Document(make_pdf(pages=3)) as doc:
        PageOrganizer.move_page(doc, 0, 2)
        assert _labels(doc) == ["Page 2", "Page 3", "Page 1"]


def test_move_page_to_first_position(make_pdf) -> None:
    with Document(make_pdf(pages=3)) as doc:
        PageOrganizer.move_page(doc, 2, 0)
        assert _labels(doc) == ["Page 3", "Page 1", "Page 2"]


def test_move_page_one_step_down_lands_adjacent(make_pdf) -> None:
    with Document(make_pdf(pages=4)) as doc:
        PageOrganizer.move_page(doc, 1, 2)
        assert _labels(doc) == ["Page 1", "Page 3", "Page 2", "Page 4"]


def test_move_every_page_to_every_position(make_pdf) -> None:
    """Exhaustive sweep, since the off-by-one only shows at the edges."""
    for source in range(4):
        for destination in range(4):
            with Document(make_pdf(name=f"m{source}{destination}.pdf", pages=4)) as doc:
                PageOrganizer.move_page(doc, source, destination)
                labels = _labels(doc)
                expected = ["Page 1", "Page 2", "Page 3", "Page 4"]
                moved = expected.pop(source)
                expected.insert(destination, moved)
                assert labels == expected, (
                    f"moving {source} -> {destination} gave {labels}"
                )


def test_move_page_noop_and_bounds(make_pdf) -> None:
    with Document(make_pdf(pages=3)) as doc:
        PageOrganizer.move_page(doc, 1, 1)
        assert _labels(doc) == ["Page 1", "Page 2", "Page 3"]
        with pytest.raises(PageOperationError):
            PageOrganizer.move_page(doc, 5, 0)
        with pytest.raises(PageOperationError):
            PageOrganizer.move_page(doc, 0, 9)


def test_reorder(make_pdf) -> None:
    with Document(make_pdf(pages=4)) as doc:
        PageOrganizer.reorder(doc, [3, 2, 1, 0])
        assert _labels(doc) == ["Page 4", "Page 3", "Page 2", "Page 1"]


def test_reorder_rejects_incomplete_permutation(make_pdf) -> None:
    with Document(make_pdf(pages=4)) as doc:
        with pytest.raises(PageOperationError):
            PageOrganizer.reorder(doc, [0, 1])
        with pytest.raises(PageOperationError):
            PageOrganizer.reorder(doc, [0, 1, 2, 2])


def test_insert_blank_page_matches_neighbour_size(make_pdf) -> None:
    with Document(make_pdf(pages=2, width=400, height=900)) as doc:
        PageOrganizer.insert_blank_page(doc, 1)
        assert doc.page_count == 3
        assert doc.get_page_size(1) == (400.0, 900.0)
        assert doc.get_page_text(1).strip() == ""


def test_insert_blank_page_at_end_and_bounds(make_pdf) -> None:
    with Document(make_pdf(pages=2)) as doc:
        PageOrganizer.insert_blank_page(doc, 2)
        assert doc.page_count == 3
        with pytest.raises(PageOperationError):
            PageOrganizer.insert_blank_page(doc, 99)


def test_duplicate_page(make_pdf) -> None:
    with Document(make_pdf(pages=3)) as doc:
        PageOrganizer.duplicate_page(doc, 1)
        assert doc.page_count == 4
        assert _labels(doc) == ["Page 1", "Page 2", "Page 2", "Page 3"]


def test_duplicate_first_and_last_page(make_pdf) -> None:
    """The last page has no following index to insert before."""
    with Document(make_pdf(name="dup_last.pdf", pages=3)) as doc:
        PageOrganizer.duplicate_page(doc, 2)
        assert _labels(doc) == ["Page 1", "Page 2", "Page 3", "Page 3"]

    with Document(make_pdf(name="dup_first.pdf", pages=3)) as doc:
        PageOrganizer.duplicate_page(doc, 0)
        assert _labels(doc) == ["Page 1", "Page 1", "Page 2", "Page 3"]


def test_duplicate_single_page_document(make_pdf) -> None:
    with Document(make_pdf(pages=1)) as doc:
        PageOrganizer.duplicate_page(doc, 0)
        assert _labels(doc) == ["Page 1", "Page 1"]


def test_delete_pages(make_pdf) -> None:
    with Document(make_pdf(pages=5)) as doc:
        assert PageOrganizer.delete_pages(doc, [0, 2]) == 2
        assert _labels(doc) == ["Page 2", "Page 4", "Page 5"]


def test_delete_pages_guards(make_pdf) -> None:
    with Document(make_pdf(pages=2)) as doc:
        with pytest.raises(ValidationError):
            PageOrganizer.delete_pages(doc, [])
        with pytest.raises(PageOperationError):
            PageOrganizer.delete_pages(doc, [0, 1])


def test_rotate_pages(make_pdf) -> None:
    with Document(make_pdf(pages=3)) as doc:
        assert PageOrganizer.rotate_pages(doc, [0, 2], 90) == 2
        assert doc.get_page_rotation(0) == 90
        assert doc.get_page_rotation(1) == 0
        assert doc.get_page_rotation(2) == 90


def test_import_pages_appends(make_pdf) -> None:
    target = make_pdf(name="target.pdf", pages=2)
    source = make_pdf(name="source.pdf", pages=3)
    with Document(target) as doc:
        added = PageOrganizer.import_pages(doc, source)
        assert added == 3
        assert doc.page_count == 5
        assert _labels(doc)[-1] == "Page 3"


def test_import_pages_at_position_and_range(make_pdf) -> None:
    target = make_pdf(name="t.pdf", pages=2)
    source = make_pdf(name="s.pdf", pages=4)
    with Document(target) as doc:
        added = PageOrganizer.import_pages(doc, source, at_index=1,
                                           from_page=1, to_page=2)
        assert added == 2
        assert doc.page_count == 4
        assert _labels(doc) == ["Page 1", "Page 2", "Page 3", "Page 2"]


def test_import_pages_bad_range(make_pdf) -> None:
    target = make_pdf(name="t2.pdf", pages=1)
    source = make_pdf(name="s2.pdf", pages=2)
    with Document(target) as doc:
        with pytest.raises(PageOperationError):
            PageOrganizer.import_pages(doc, source, from_page=0, to_page=9)


def test_page_summaries(make_pdf) -> None:
    with Document(make_pdf(pages=2, width=800, height=400)) as doc:
        summaries = PageOrganizer.page_summaries(doc)
        assert len(summaries) == 2
        assert summaries[0]["number"] == 1
        assert summaries[0]["orientation"] == "landscape"
        assert summaries[0]["rotation"] == 0
