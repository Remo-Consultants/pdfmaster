"""In-app searchable OCR: text layer, deskew estimate, PDF/A command."""

from PIL import Image, ImageDraw

from src.core.document import Document
from src.services import pdfa_export
from src.services.ocr_service import (
    OCRResult,
    OCRService,
    estimate_skew_degrees,
    orientation_correction,
    page_has_extractable_text,
)


def test_page_with_text_is_detected(make_pdf):
    with Document(make_pdf(pages=1)) as doc:
        assert page_has_extractable_text(doc, 0)


def test_blank_page_is_not_detected(tmp_path):
    import pymupdf as fitz

    path = tmp_path / "blank.pdf"
    pdf = fitz.open()
    pdf.new_page()
    pdf.save(path)
    pdf.close()
    with Document(path) as doc:
        assert not page_has_extractable_text(doc, 0)


def test_skip_text_leaves_existing_words(make_pdf, monkeypatch):
    service = OCRService()
    monkeypatch.setattr(service, "_ocr_image", lambda image: (_ for _ in ()).throw(AssertionError("OCR ran")))
    with Document(make_pdf(pages=1)) as doc:
        report = service.make_pages_searchable(doc, [0], dpi=72, skip_text=True)
        assert report.pages_skipped == 1
        assert "Page 1" in doc.get_page_text(0)


def test_invisible_layer_is_extractable(make_pdf, monkeypatch):
    service = OCRService()

    def fake_ocr(image):
        return OCRResult(
            page=0,
            text="HelloScan",
            confidence=90.0,
            boxes=[(10, 10, 120, 40, "HelloScan")],
        )

    monkeypatch.setattr(service, "_ocr_image", fake_ocr)
    with Document(make_pdf(pages=1)) as doc:
        report = service.make_pages_searchable(
            doc, [0], dpi=72, skip_text=False, deskew=False, rotate_pages=False
        )
        assert report.pages_skipped == 0
        assert "HelloScan" in doc.get_page_text(0)


def test_deskew_replaces_page_and_keeps_ocr_text(make_pdf, monkeypatch):
    import src.services.ocr_service as ocr_mod

    service = OCRService()
    monkeypatch.setattr(ocr_mod, "estimate_skew_degrees", lambda image: 2.0)
    monkeypatch.setattr(
        service,
        "_ocr_image",
        lambda image: OCRResult(page=0, text="Tilted", confidence=80.0, boxes=[(8, 8, 80, 28, "Tilted")]),
    )
    with Document(make_pdf(pages=1)) as doc:
        report = service.make_pages_searchable(doc, [0], dpi=72, skip_text=False, deskew=True)
        assert report.pages_deskewed == 1
        assert "Tilted" in doc.get_page_text(0)
    image = Image.new("RGB", (400, 200), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 90, 380, 110), fill="black")
    assert abs(estimate_skew_degrees(image)) < 1.0


def test_tilted_bar_reports_a_correction():
    image = Image.new("RGB", (400, 200), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 90, 380, 110), fill="black")
    tilted = image.rotate(-3, expand=True, fillcolor="white")
    angle = estimate_skew_degrees(tilted)
    assert 1.5 <= angle <= 4.5


def test_orientation_parser_reads_rotate(monkeypatch):
    import sys
    import types

    image = Image.new("RGB", (20, 20), "white")
    fake = types.ModuleType("pytesseract")
    fake.image_to_osd = lambda _image: "Orientation in degrees: 270\nRotate: 90\n"
    monkeypatch.setitem(sys.modules, "pytesseract", fake)
    assert orientation_correction(image) == 90


def test_bundled_tesseract_is_preferred(tmp_path, monkeypatch):
    from src.services import bundled_tools

    install = tmp_path / "vendor" / "tesseract"
    data = install / "tessdata"
    data.mkdir(parents=True)
    exe = install / "tesseract.exe"
    exe.write_bytes(b"")
    (data / "eng.traineddata").write_bytes(b"trained")
    monkeypatch.setattr(bundled_tools, "vendor_root", lambda: tmp_path / "vendor")
    found = bundled_tools.tesseract_executable()
    assert found == exe
    assert bundled_tools.tessdata_dir(found) == data


def test_pdfa_command_is_ghostscript_not_ocrmypdf(tmp_path):
    prefix = tmp_path / "def.ps"
    source = tmp_path / "in.pdf"
    dest = tmp_path / "out.pdf"
    command = pdfa_export.build_pdfa_command("gswin64c", prefix, source, dest)
    assert command[0] == "gswin64c"
    assert "-dPDFA=2" in command
    assert "ocrmypdf" not in " ".join(command).lower()


def test_pdfa_prefix_points_at_icc(tmp_path):
    icc = tmp_path / "srgb.icc"
    icc.write_bytes(b"icc")
    text = pdfa_export.pdfa_prefix(icc)
    assert "srgb.icc" in text.replace("\\", "/")
    assert "/GTS_PDFA1" in text
