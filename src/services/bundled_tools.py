"""Locate OCR and PDF/A programs that ship inside PDFMaster.

Tesseract and Ghostscript are stored under ``vendor/`` next to the app.
A copy already on PATH is used only when the bundled one is missing.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Optional


def app_root() -> Path:
    """Project root in a source checkout, or the frozen bundle root."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[2]


def vendor_root() -> Path:
    return app_root() / "vendor"


def _shallowest(root: Path, name: str) -> Optional[Path]:
    if not root.is_dir():
        return None
    matches = [path for path in root.rglob(name) if path.is_file()]
    if not matches:
        return None
    matches.sort(key=lambda path: (len(path.parts), str(path)))
    return matches[0]


def tesseract_executable() -> Optional[Path]:
    """Bundled ``tesseract.exe``, or one already on PATH."""
    bundled = _shallowest(vendor_root() / "tesseract", "tesseract.exe")
    if bundled is not None:
        return bundled
    found = shutil.which("tesseract")
    return Path(found) if found else None


def tessdata_dir(executable: Path) -> Optional[Path]:
    """Directory that contains ``eng.traineddata``."""
    for candidate in (
        executable.parent / "tessdata",
        executable.parent.parent / "tessdata",
    ):
        if (candidate / "eng.traineddata").is_file():
            return candidate
    found = _shallowest(executable.parent, "eng.traineddata")
    return found.parent if found is not None else None


def configure_tesseract() -> Optional[str]:
    """Point pytesseract at the bundled engine and language data."""
    executable = tesseract_executable()
    if executable is None:
        return None
    data = tessdata_dir(executable)
    if data is not None:
        # This Windows build reads traineddata directly from TESSDATA_PREFIX.
        os.environ["TESSDATA_PREFIX"] = str(data) + os.sep
    try:
        import pytesseract
    except ImportError:
        return str(executable)
    runner = getattr(pytesseract, "pytesseract", None)
    if runner is not None and hasattr(runner, "tesseract_cmd"):
        runner.tesseract_cmd = str(executable)
    return str(executable)


def ghostscript_executable() -> Optional[Path]:
    """Bundled Ghostscript console binary, or one already on PATH."""
    root = vendor_root() / "ghostscript"
    for name in ("gswin64c.exe", "gswin32c.exe", "gs"):
        bundled = _shallowest(root, name)
        if bundled is not None:
            return bundled
    for name in ("gswin64c", "gswin32c", "gs"):
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


def ghostscript_env(executable: Path) -> dict:
    """Environment that lets a bundled Ghostscript find its lib files."""
    env = os.environ.copy()
    lib_dirs = []
    for candidate in (
        executable.parent / "lib",
        executable.parent.parent / "lib",
    ):
        if candidate.is_dir():
            lib_dirs.append(str(candidate))
    if lib_dirs:
        existing = env.get("GS_LIB", "")
        env["GS_LIB"] = os.pathsep.join(lib_dirs + ([existing] if existing else []))
    return env
