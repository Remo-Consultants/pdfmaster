"""Download Tesseract and Ghostscript into vendor/ for PDFMaster.

Run from the project root:

    .\\venv\\Scripts\\python scripts\\fetch_bundled_tools.py

The Windows installers are unpacked into vendor/ only. Nothing is
installed system-wide, and PATH is left unchanged.
"""

from __future__ import annotations

import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.licensing import TESSDATA_COMMIT, write_distribution_notices

VENDOR = ROOT / "vendor"
CACHE = VENDOR / "_cache"

TESSERACT_URL = (
    "https://github.com/UB-Mannheim/tesseract/releases/download/"
    "v5.4.0.20240606/tesseract-ocr-w64-setup-5.4.0.20240606.exe"
)
GHOSTSCRIPT_URL = (
    "https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/"
    "gs10080/gs10080w64.exe"
)
TESSDATA = (
    "https://github.com/tesseract-ocr/tessdata/raw/"
    f"{TESSDATA_COMMIT}/{{name}}.traineddata"
)
LANGUAGES = ("osd", "eng", "deu", "fra", "spa", "ita", "por", "chi_sim", "jpn")


def _download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and destination.stat().st_size > 0:
        print(f"cached {destination.name}")
        return
    print(f"downloading {url}")
    urllib.request.urlretrieve(url, destination)


def _install(archive: Path, folder: Path, marker: str) -> None:
    """Silent-install into vendor/. The installer does not touch PATH."""
    folder.mkdir(parents=True, exist_ok=True)
    if any(folder.rglob(marker)):
        print(f"already installed {marker}")
        return
    print(f"installing {archive.name} into {folder}")
    completed = subprocess.run(
        [str(archive), "/S", f"/D={folder}"],
        check=False,
    )
    if completed.returncode != 0 or not any(folder.rglob(marker)):
        raise SystemExit(f"Could not install {archive.name} into {folder}")


def _tessdata_dir() -> Path:
    matches = list((VENDOR / "tesseract").rglob("eng.traineddata"))
    if not matches:
        raise SystemExit("Tesseract unpacked, but eng.traineddata was not found.")
    return matches[0].parent


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    tesseract_setup = CACHE / "tesseract-setup.exe"
    ghostscript_setup = CACHE / "ghostscript-setup.exe"
    _download(TESSERACT_URL, tesseract_setup)
    _download(GHOSTSCRIPT_URL, ghostscript_setup)
    print("installing Tesseract into vendor/")
    _install(tesseract_setup, VENDOR / "tesseract", "tesseract.exe")
    print("installing Ghostscript into vendor/")
    _install(ghostscript_setup, VENDOR / "ghostscript", "gswin64c.exe")
    data = _tessdata_dir()
    for name in LANGUAGES:
        target = data / f"{name}.traineddata"
        if target.is_file() and target.stat().st_size > 1000:
            print(f"have {name}")
            continue
        _download(TESSDATA.format(name=name), target)
    write_distribution_notices(ROOT)
    print(f"ready under {VENDOR}")


if __name__ == "__main__":
    main()
