"""Notices for the bundled Tesseract and Ghostscript copies."""

from pathlib import Path

from src.licensing import (
    GHOSTSCRIPT_SOURCE_URL,
    NOTICE_PACKAGES,
    TESSDATA_COMMIT,
    bundle_license_text,
    ghostscript_source_offer,
    runtime_requirement_names,
    ship_bundled_file,
    third_party_notice_text,
)


def test_notice_names_versions_source_and_replacement():
    text = third_party_notice_text()
    assert "Ghostscript 10.08.0" in text
    assert "AGPL-3.0" in text
    assert GHOSTSCRIPT_SOURCE_URL in text
    assert "ghostpdl-10.08.0.tar.gz" in text
    assert TESSDATA_COMMIT in text
    assert "raw/main" not in text
    assert "Tesseract OCR 5.4.0.20240606" in text
    assert "Apache-2.0" in text
    assert "You may replace those GLib, Cairo, and Pango DLLs" in text
    assert "does not load gsdll64.dll" in text


def test_source_offer_sits_with_the_exact_archive():
    offer = ghostscript_source_offer()
    assert "gswin64c.exe" in offer
    assert "gsdll64.dll" in offer
    assert GHOSTSCRIPT_SOURCE_URL in offer


def test_training_tools_and_jars_are_not_packaged():
    assert ship_bundled_file("tesseract", Path("lstmtraining.exe")) is False
    assert ship_bundled_file("tesseract", Path("tessdata/jaxb-api-2.3.1.jar")) is False
    assert ship_bundled_file("tesseract", Path("tessdata/ScrollView.jar")) is False
    assert ship_bundled_file("tesseract", Path("$PLUGINSDIR/modern-wizard.exe")) is False
    assert ship_bundled_file("tesseract", Path("ambiguous_words.1.html")) is False
    assert ship_bundled_file("tesseract", Path("tesseract.exe")) is True
    assert ship_bundled_file("tesseract", Path("tesseract.1.html")) is True
    assert ship_bundled_file("tesseract", Path("doc/LICENSE")) is True
    assert ship_bundled_file("tesseract", Path("tessdata/eng.traineddata")) is True
    assert ship_bundled_file("ghostscript", Path("doc/COPYING")) is True
    assert ship_bundled_file("ghostscript", Path("bin/gswin64c.exe")) is True


def test_bundle_license_includes_terms_privacy_and_copyleft():
    root = Path(__file__).resolve().parents[1]
    text = bundle_license_text(root)
    assert text.startswith("Terms of use")
    assert "do not narrow that license" in text
    assert "PyMuPDF" in text
    assert "===== Privacy notice =====" in text
    assert "recent_files.txt" in text
    assert "MIT License" in text
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in text
    assert "Apache License" in text
    assert "GNU LESSER GENERAL PUBLIC LICENSE" in text
    assert "Version 3, 29 June 2007" in text
    assert "PDFMaster's own code is under the MIT License." in text
    assert "The MIT License does not replace the AGPL." in text


def test_runtime_requirements_stay_in_the_notice_catalog():
    root = Path(__file__).resolve().parents[1]
    catalog = {name.lower() for name in NOTICE_PACKAGES}
    for name in runtime_requirement_names(root):
        assert name.lower() in catalog, name
    text = third_party_notice_text().lower()
    for name in catalog:
        assert name in text
    assert "openssl" in text
    assert "lgpl-3.0" in text
    assert "bootloader" in text
