"""Saved-signature creation and placement."""

from __future__ import annotations

from PySide6.QtGui import QImage

from src.core.document import Document
from src.processors.content import ContentEditor
from src.services import esign


def test_typed_signature_has_ink(monkeypatch, tmp_path, qapp) -> None:
    monkeypatch.setattr(esign, "CONFIG_DIR", tmp_path)
    image = esign.render_typed_signature("Elena Rostova")
    assert _opaque_pixels(image) > 20
    saved = esign.save_signature(image, "Elena Rostova")
    assert saved.is_file()
    assert esign.signature_path() == saved
    assert esign.signature_name() == "Elena Rostova"
    cropped = QImage(str(saved))
    assert cropped.height() < image.height()


def test_each_style_draws_the_name(qapp) -> None:
    for style_id, *_rest in esign.SIGNATURE_STYLES:
        image = esign.render_typed_signature("Elena Rostova", style=style_id)
        assert _opaque_pixels(image) > 10


def test_signature_can_be_placed_on_a_page(monkeypatch, tmp_path, make_pdf, qapp) -> None:
    monkeypatch.setattr(esign, "CONFIG_DIR", tmp_path)
    image = esign.render_typed_signature("A Signer")
    esign.save_signature(image, "A Signer")
    with Document(make_pdf(pages=1)) as document:
        ContentEditor.add_image(document, 0, (72, 500, 280, 560), esign.signature_path())
        with document.transaction(mark_modified=False) as pdf:
            assert pdf[0].get_images()


def _opaque_pixels(image: QImage) -> int:
    count = 0
    step = 2
    for y in range(0, image.height(), step):
        for x in range(0, image.width(), step):
            if image.pixelColor(x, y).alpha() > 12:
                count += 1
    return count
