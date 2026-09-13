"""PDF/A detection and lightweight validation helpers.

This is not a substitute for veraPDF. It reports whether the file
declares a PDF/A identity and whether common structural markers are
present, so users get a fast desktop check without external tools.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import pymupdf as fitz

from src.core.document import Document
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PdfaIssue:
    """One finding from PDF/A inspection."""

    severity: str  # info | warning | error
    message: str


@dataclass
class PdfaReport:
    """Summary of PDF/A-related signals in a document."""

    declares_pdfa: bool = False
    part: Optional[str] = None
    conformance: Optional[str] = None
    has_output_intent: bool = False
    pdf_version: str = ""
    issues: List[PdfaIssue] = field(default_factory=list)

    @property
    def label(self) -> str:
        if not self.declares_pdfa:
            return "Not declared as PDF/A"
        part = self.part or "?"
        conf = self.conformance or "?"
        return f"PDF/A-{part}{conf}"

    @property
    def ok_for_basic_use(self) -> bool:
        """True when the file claims PDF/A and has no error-level issues."""
        return self.declares_pdfa and not any(i.severity == "error" for i in self.issues)


class PdfaService:
    """Inspect PDF/A declarations and basic structure."""

    @staticmethod
    def inspect(document: Document) -> PdfaReport:
        """Analyse the open document for PDF/A markers."""
        report = PdfaReport()
        with document.transaction(mark_modified=False) as pdf:
            report.pdf_version = ""
            try:
                meta = pdf.metadata or {}
                report.pdf_version = str(meta.get("format") or "")
            except Exception:  # noqa: BLE001
                report.pdf_version = ""
            if not report.pdf_version:
                try:
                    # Trailer / catalog hint on some builds.
                    report.pdf_version = str(getattr(pdf, "version", "") or "")
                except Exception:  # noqa: BLE001
                    pass

            part, conf = _read_pdfa_identification(pdf)
            if part:
                report.declares_pdfa = True
                report.part = part
                report.conformance = conf
            else:
                report.issues.append(
                    PdfaIssue(
                        "info",
                        "No pdfaid identification metadata was found.",
                    )
                )

            report.has_output_intent = _has_output_intent(pdf)
            if report.declares_pdfa and not report.has_output_intent:
                report.issues.append(
                    PdfaIssue(
                        "warning",
                        "PDF/A is declared but no OutputIntent was found "
                        "(colour profile may be missing).",
                    )
                )

            if pdf.is_encrypted:
                report.issues.append(
                    PdfaIssue(
                        "error",
                        "Document is encrypted; PDF/A files must not require a password.",
                    )
                )

            if pdf.page_count < 1:
                report.issues.append(
                    PdfaIssue("error", "Document has no pages.")
                )

            # Embedded fonts help PDF/A; warn if pages look image-only without text.
            text_pages = 0
            sample = min(pdf.page_count, 5)
            for i in range(sample):
                if (pdf.load_page(i).get_text("text") or "").strip():
                    text_pages += 1
            if report.declares_pdfa and sample and text_pages == 0:
                report.issues.append(
                    PdfaIssue(
                        "info",
                        "Sampled pages have no extractable text "
                        "(scanned PDF/A is valid if properly tagged).",
                    )
                )

        logger.info(
            "PDF/A inspect %s: %s (%s issue(s))",
            document.filename,
            report.label,
            len(report.issues),
        )
        return report


def _read_pdfa_identification(pdf: fitz.Document) -> Tuple[Optional[str], Optional[str]]:
    """Return (part, conformance) from xhtml metadata if present."""
    try:
        xml = pdf.get_xml_metadata() or ""
    except Exception:  # noqa: BLE001
        xml = ""
    if not xml:
        # Some producers only put a hint in the info dict.
        meta = pdf.metadata or {}
        blob = " ".join(str(v) for v in meta.values() if v)
        if "PDF/A" in blob.upper() or "PDFA" in blob.upper():
            return "1", "b"
        return None, None

    part = _xml_tag_value(xml, "pdfaid:part") or _xml_tag_value(xml, "part")
    conf = _xml_tag_value(xml, "pdfaid:conformance") or _xml_tag_value(
        xml, "conformance"
    )
    if part:
        return part.strip(), (conf or "").strip().lower() or None

    lower = xml.lower()
    if "pdfaid" in lower or "pdf/a" in lower:
        return "1", "b"
    return None, None


def _xml_tag_value(xml: str, tag: str) -> Optional[str]:
    """Read a simple XML element or pdfaid attribute value."""
    open_tag = f"<{tag}"
    start = xml.find(open_tag)
    if start >= 0:
        gt = xml.find(">", start)
        close = f"</{tag}>"
        end = xml.find(close, gt)
        if gt >= 0 and end > gt:
            return xml[gt + 1 : end].strip()

    # Attribute form: pdfaid:part="1"
    for attr in (f'{tag}="', f"{tag}='"):
        pos = xml.find(attr)
        if pos >= 0:
            pos += len(attr)
            quote = attr[-1]
            end = xml.find(quote, pos)
            if end > pos:
                return xml[pos:end].strip()
    return None


def _has_output_intent(pdf: fitz.Document) -> bool:
    try:
        catalog = pdf.pdf_catalog()
        intents = pdf.xref_get_key(catalog, "OutputIntents")
        if intents and intents[0] != "null":
            return True
    except Exception:  # noqa: BLE001
        pass
    try:
        xml = (pdf.get_xml_metadata() or "").lower()
        if "outputintent" in xml or "pdfaid" in xml:
            # Weak signal only when OutputIntents dictionary missing.
            return "outputcondition" in xml
    except Exception:  # noqa: BLE001
        pass
    return False
