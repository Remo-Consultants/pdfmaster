"""Tests for document compare and PDF/A inspection."""

from __future__ import annotations

from pathlib import Path

import pymupdf as fitz
import pytest

from src.core.document import Document
from src.services.compare_service import CompareService
from src.services.pdfa_service import PdfaService
from src.utils.exceptions import ValidationError


def _write_pdf(path: Path, lines: list[str]) -> None:
    doc = fitz.open()
    for text in lines:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def test_compare_identical(tmp_path: Path) -> None:
    a = tmp_path / "a.pdf"
    b = tmp_path / "b.pdf"
    _write_pdf(a, ["Same page"])
    _write_pdf(b, ["Same page"])
    report = CompareService.compare_files(a, b)
    assert report.identical
    assert report.changed_count == 0
    assert report.pages[0].status == "equal"


def test_compare_changed_and_extra_page(tmp_path: Path) -> None:
    a = tmp_path / "a.pdf"
    b = tmp_path / "b.pdf"
    _write_pdf(a, ["Alpha", "Shared"])
    _write_pdf(b, ["Beta", "Shared", "Extra"])
    report = CompareService.compare_files(a, b)
    assert not report.identical
    assert report.pages[0].status == "changed"
    assert report.pages[1].status == "equal"
    assert report.pages[2].status == "only_right"
    assert report.changed_count == 2


def test_compare_rejects_same_path(tmp_path: Path) -> None:
    a = tmp_path / "a.pdf"
    _write_pdf(a, ["x"])
    with pytest.raises(ValidationError):
        CompareService.compare_files(a, a)


def test_pdfa_undeclared(make_pdf) -> None:
    with Document(make_pdf()) as doc:
        report = PdfaService.inspect(doc)
        assert report.declares_pdfa is False
        assert "Not declared" in report.label


def test_pdfa_declared_via_metadata(tmp_path: Path) -> None:
    path = tmp_path / "pdfa.pdf"
    raw = fitz.open()
    raw.new_page().insert_text((72, 72), "Archival")
    # Minimal XMP identification block.
    xmp = """<?xpacket begin='' id='W5M0MpCehiHzreSzNTczkc9d'?>
<x:xmpmeta xmlns:x='adobe:ns:meta/'>
 <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
  <rdf:Description rdf:about=''
    xmlns:pdfaid='http://www.aiim.org/pdfa/ns/id/'>
   <pdfaid:part>1</pdfaid:part>
   <pdfaid:conformance>B</pdfaid:conformance>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end='w'?>"""
    raw.set_xml_metadata(xmp)
    raw.save(path)
    raw.close()

    with Document(path) as doc:
        report = PdfaService.inspect(doc)
        assert report.declares_pdfa is True
        assert report.part == "1"
        assert (report.conformance or "").lower() == "b"
        assert "PDF/A-1" in report.label
