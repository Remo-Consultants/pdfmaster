"""PDF/A-2 export using Ghostscript.

Searchable text, deskew, and rotation stay inside PDFMaster. A real PDF/A
file still needs Ghostscript's PDF writer, so this module calls ``gswin64c``
or ``gs`` directly. It does not call OCRmyPDF.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional


class PdfaExportError(Exception):
    """PDF/A export could not run or Ghostscript reported a failure."""


def ghostscript_executable() -> Optional[str]:
    """Return a Ghostscript console executable on PATH, if one is installed."""
    for name in ("gswin64c", "gswin32c", "gs"):
        found = shutil.which(name)
        if found:
            return found
    return None


def find_srgb_icc(gs_executable: str) -> Optional[Path]:
    """Locate an sRGB ICC profile next to a Ghostscript install."""
    exe = Path(gs_executable).resolve()
    names = ("srgb.icc", "default_rgb.icc", "sRGB_v4_ICC_preference.icc")
    roots = [
        exe.parent,
        exe.parent / "iccprofiles",
        exe.parent / "lib",
        exe.parent.parent / "iccprofiles",
        exe.parent.parent / "lib" / "iccprofiles",
        exe.parent.parent / "Resource" / "ColorSpace",
    ]
    for root in roots:
        for name in names:
            candidate = root / name
            if candidate.is_file():
                return candidate
    return None


def pdfa_prefix(icc_path: Path) -> str:
    """PostScript prefix that attaches an sRGB output intent for PDF/A-2."""
    icc = str(icc_path).replace("\\", "/")
    return f"""%!PS
/ICCProfile ({icc}) def
[/_objdef {{icc_PDFA}} /type /stream /OBJ pdfmark
[{{icc_PDFA}} << /N 3 >> /PUT pdfmark
[{{icc_PDFA}} ICCProfile (r) file /PUT pdfmark
[/_objdef {{OutputIntent_PDFA}} /type /dict /OBJ pdfmark
[{{OutputIntent_PDFA}} <<
  /Type /OutputIntent
  /S /GTS_PDFA1
  /DestOutputProfile {{icc_PDFA}}
  /OutputConditionIdentifier (sRGB)
>> /PUT pdfmark
[{{Catalog}} <</OutputIntents [ {{OutputIntent_PDFA}} ]>> /PUT pdfmark
"""


def build_pdfa_command(gs_executable: str, prefix_path: Path, source: Path, destination: Path) -> List[str]:
    """Ghostscript command that writes a PDF/A-2 file."""
    return [
        gs_executable,
        "-dPDFA=2",
        "-dBATCH",
        "-dNOPAUSE",
        "-dQUIET",
        "-sColorConversionStrategy=RGB",
        "-sDEVICE=pdfwrite",
        "-dPDFACompatibilityPolicy=1",
        f"-sOutputFile={destination}",
        str(prefix_path),
        str(source),
    ]


def export_pdfa(source: Path, destination: Path) -> Path:
    """Convert ``source`` to PDF/A-2 at ``destination``."""
    gs = ghostscript_executable()
    if not gs:
        raise PdfaExportError(
            "PDF/A export needs Ghostscript (gswin64c or gs) installed and on PATH."
        )
    icc = find_srgb_icc(gs)
    if icc is None:
        raise PdfaExportError(
            "Ghostscript is installed, but no sRGB ICC profile was found beside it."
        )
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    prefix_path = destination.with_suffix(".pdfa.ps")
    prefix_path.write_text(pdfa_prefix(icc), encoding="ascii", errors="replace")
    command = build_pdfa_command(gs, prefix_path, Path(source), destination)
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        prefix_path.unlink(missing_ok=True)
    if completed.returncode != 0 or not destination.is_file():
        detail = (completed.stderr or completed.stdout or "").strip()
        tail = detail[-800:] if detail else f"Ghostscript exited with code {completed.returncode}."
        raise PdfaExportError(tail)
    return destination
