"""Tests for content editing: text replacement, new text, and images."""

from __future__ import annotations

import pytest

from src.core.document import Document
from src.processors.content import ContentEditor, color_int_to_rgb, map_to_base14
from src.utils.exceptions import ContentEditError


def test_color_int_to_rgb() -> None:
    assert color_int_to_rgb(0x000000) == (0.0, 0.0, 0.0)
    assert color_int_to_rgb(0xFFFFFF) == (1.0, 1.0, 1.0)
    r, g, b = color_int_to_rgb(0xFF0000)
    assert (r, g, b) == (1.0, 0.0, 0.0)


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Helvetica", "helv"),
        ("ABCDEF+Arial-BoldMT", "hebo"),
        ("Times-Roman", "tiro"),
        ("Georgia-Italic", "tiit"),
        ("CourierNewPSMT", "cour"),
        ("SomeUnknownFace", "helv"),
    ],
)
def test_map_to_base14(name: str, expected: str) -> None:
    code, _ = map_to_base14(name)
    assert code == expected


def test_map_to_base14_flags_substitution() -> None:
    _, substituted = map_to_base14("Helvetica")
    assert substituted is False
    _, substituted = map_to_base14("ABCDEF+Wingdings")
    assert substituted is True


def test_find_spans_whole_page(make_text_pdf) -> None:
    with Document(make_text_pdf()) as doc:
        spans = ContentEditor.find_spans(doc, 0)
        texts = [s["text"] for s in spans]
        assert "Invoice Date: 2024-01-01" in texts
        assert spans[0]["size"] == 12.0
        assert spans[0]["font"]


def test_find_spans_limited_to_rect(make_text_pdf) -> None:
    with Document(make_text_pdf()) as doc:
        all_spans = ContentEditor.find_spans(doc, 0)
        first = all_spans[0]
        near = ContentEditor.find_spans(doc, 0, first["bbox"])
        assert len(near) == 1
        assert near[0]["text"] == first["text"]


def test_text_in_rect(make_text_pdf) -> None:
    with Document(make_text_pdf()) as doc:
        span = ContentEditor.find_spans(doc, 0)[0]
        assert "Invoice" in ContentEditor.text_in_rect(doc, 0, span["bbox"])


def test_replace_text_same_length(make_text_pdf) -> None:
    with Document(make_text_pdf()) as doc:
        span = ContentEditor.find_spans(doc, 0)[0]
        report = ContentEditor.replace_text(
            doc, 0, span["bbox"], "Invoice Date: 2026-09-11"
        )
        assert report["shrunk"] is False
        page_text = doc.get_page_text(0)
        assert "2026-09-11" in page_text
        assert "2024-01-01" not in page_text


def test_replace_text_longer_shrinks_to_fit(make_text_pdf) -> None:
    with Document(make_text_pdf()) as doc:
        span = next(s for s in ContentEditor.find_spans(doc, 0)
                    if s["text"].startswith("Total"))
        report = ContentEditor.replace_text(
            doc, 0, span["bbox"], "Total: 1,000,000.00 including tax"
        )
        assert "1,000,000.00" in doc.get_page_text(0)
        assert report["size"] <= report["original_size"]


def test_replace_text_rejects_impossible_fit(make_text_pdf) -> None:
    with Document(make_text_pdf()) as doc:
        span = ContentEditor.find_spans(doc, 0)[0]
        with pytest.raises(ContentEditError):
            ContentEditor.replace_text(doc, 0, span["bbox"], "word " * 400)


def test_replace_text_reports_font_substitution(make_text_pdf) -> None:
    with Document(make_text_pdf()) as doc:
        span = ContentEditor.find_spans(doc, 0)[0]
        report = ContentEditor.replace_text(doc, 0, span["bbox"], "New value")
        assert report["font"] in ("helv", "hebo", "heit")
        assert "substituted" in report


def test_replace_text_empty_rect(make_text_pdf) -> None:
    with Document(make_text_pdf()) as doc:
        with pytest.raises(ContentEditError):
            ContentEditor.replace_text(doc, 0, (10, 10, 10, 10), "hello")


def test_replace_matching_text(make_text_pdf) -> None:
    pdf = make_text_pdf(lines=["alpha beta", "gamma alpha", "alpha delta"])
    with Document(pdf) as doc:
        replaced = ContentEditor.replace_matching_text(doc, 0, "alpha", "OMEGA")
        assert replaced == 3
        text = doc.get_page_text(0)
        assert "alpha" not in text
        assert text.count("OMEGA") == 3


def test_replace_matching_text_no_hits(make_text_pdf) -> None:
    with Document(make_text_pdf()) as doc:
        assert ContentEditor.replace_matching_text(doc, 0, "nonexistent", "x") == 0
        with pytest.raises(ContentEditError):
            ContentEditor.replace_matching_text(doc, 0, "", "x")


def test_add_text_box(make_pdf) -> None:
    with Document(make_pdf(pages=1)) as doc:
        used = ContentEditor.add_text(
            doc, 0, (100, 300, 400, 360), "Approved by Dinesh", size=14
        )
        assert used <= 14
        assert "Approved by Dinesh" in doc.get_page_text(0)
        assert doc.is_modified


def test_add_text_validation(make_pdf) -> None:
    with Document(make_pdf(pages=1)) as doc:
        with pytest.raises(ContentEditError):
            ContentEditor.add_text(doc, 0, (10, 10, 200, 40), "   ")
        with pytest.raises(ContentEditError):
            ContentEditor.add_text(doc, 0, (10, 10, 10, 10), "hi")
        with pytest.raises(ContentEditError):
            ContentEditor.add_text(doc, 0, (10, 10, 40, 20), "far too much text " * 50)


def test_add_image(make_pdf, make_image) -> None:
    image = make_image()
    with Document(make_pdf(pages=1)) as doc:
        ContentEditor.add_image(doc, 0, (100, 100, 300, 180), image)
        with doc.transaction(mark_modified=False) as pdf:
            assert len(pdf.load_page(0).get_images()) == 1


def test_add_image_missing_file(make_pdf, tmp_path) -> None:
    with Document(make_pdf(pages=1)) as doc:
        with pytest.raises(ContentEditError):
            ContentEditor.add_image(doc, 0, (10, 10, 100, 100), tmp_path / "nope.png")


def test_erase_area(make_text_pdf) -> None:
    with Document(make_text_pdf()) as doc:
        span = ContentEditor.find_spans(doc, 0)[0]
        ContentEditor.erase_area(doc, 0, span["bbox"])
        assert "Invoice Date" not in doc.get_page_text(0)


def test_edits_persist_after_save(make_text_pdf) -> None:
    source = make_text_pdf()
    with Document(source) as doc:
        span = ContentEditor.find_spans(doc, 0)[0]
        ContentEditor.replace_text(doc, 0, span["bbox"], "Invoice Date: 2030-12-25")
        doc.save(incremental=False)
    with Document(source) as reopened:
        assert "2030-12-25" in reopened.get_page_text(0)
