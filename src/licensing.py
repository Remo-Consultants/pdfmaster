"""License notices for programs shipped beside PDFMaster.

PDFMaster's own code is MIT. Tesseract and Ghostscript stay under their
own licenses. This module is the text the installer, the About dialog,
and the files next to those programs all share.
"""

from __future__ import annotations

from pathlib import Path

GHOSTSCRIPT_VERSION = "10.08.0"
GHOSTSCRIPT_SOURCE_URL = (
    "https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/"
    "gs10080/ghostpdl-10.08.0.tar.gz"
)
TESSERACT_VERSION = "5.4.0.20240606"
TESSERACT_BUILD_URL = (
    "https://github.com/UB-Mannheim/tesseract/releases/tag/v5.4.0.20240606"
)
TESSDATA_COMMIT = "ced78752cc61322fb554c280d13360b35b8684e4"
TESSDATA_URL = (
    "https://github.com/tesseract-ocr/tessdata/raw/"
    f"{TESSDATA_COMMIT}/{{name}}.traineddata"
)

# Training tools and the Java viewer shipped by the Tesseract installer.
# PDFMaster only runs tesseract.exe.
_TESSERACT_EXCLUDED_FILES = frozenset(
    {
        "ambiguous_words.exe",
        "classifier_tester.exe",
        "cntraining.exe",
        "combine_lang_model.exe",
        "combine_tessdata.exe",
        "dawg2wordlist.exe",
        "lstmeval.exe",
        "lstmtraining.exe",
        "merge_unicharsets.exe",
        "mftraining.exe",
        "set_unicharset_properties.exe",
        "shapeclustering.exe",
        "text2image.exe",
        "unicharset_extractor.exe",
        "wordlist2dawg.exe",
        "tesseract-uninstall.exe.nsis",
        "winpath.exe",
    }
)


def ship_bundled_file(folder_name: str, path: Path) -> bool:
    """False for Tesseract files the Windows package must not redistribute."""
    if folder_name != "tesseract":
        return True
    if "$PLUGINSDIR" in path.parts:
        return False
    if path.suffix.lower() == ".jar":
        return False
    if path.name in _TESSERACT_EXCLUDED_FILES:
        return False
    if path.suffix.lower() == ".html" and path.name != "tesseract.1.html":
        return False
    return True


def ghostscript_source_offer() -> str:
    """Short offer placed next to gswin64c.exe."""
    return "\n".join(
        [
            f"Ghostscript {GHOSTSCRIPT_VERSION}",
            "License: GNU Affero General Public License, version 3 (AGPL-3.0)",
            "Copyright: Artifex Software, Inc.",
            "",
            "This folder contains the unmodified Ghostscript "
            f"{GHOSTSCRIPT_VERSION} Windows binaries.",
            "PDFMaster runs gswin64c.exe as a separate program.",
            "PDFMaster does not load gsdll64.dll.",
            "",
            "The complete AGPL-3.0 text is installed at:",
            "  ..\\doc\\COPYING",
            "",
            "Corresponding source for this exact version:",
            f"  {GHOSTSCRIPT_SOURCE_URL}",
            "",
            "That archive is the source for these binaries and is to be",
            "offered for as long as these binaries are offered.",
            "Ghostscript is not covered by the MIT license of PDFMaster.",
            "",
        ]
    )


# Direct imports and the packager. A new name in requirements.txt must be
# added here. tests/test_licensing.py fails when that step is skipped.
NOTICE_PACKAGES = (
    "PySide6",
    "shiboken6",
    "pymupdf",
    "pypdf",
    "pillow",
    "cryptography",
    "pytesseract",
    "pyinstaller",
)


def distribution_version(dist_name: str) -> str:
    """Installed version, or a stable fallback when the package is absent."""
    try:
        from importlib.metadata import version
    except ImportError:
        return "the version installed with this build"
    try:
        return version(dist_name)
    except Exception:
        return "the version installed with this build"


def runtime_requirement_names(root: Path) -> list[str]:
    """Runtime packages in requirements.txt. Test tools are not shipped."""
    text = (Path(root) / "requirements.txt").read_text(encoding="utf-8")
    names = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        name = stripped.split(">=")[0].split("==")[0].split("[")[0].strip()
        if name.lower().startswith("pytest"):
            continue
        names.append(name)
    return names


def python_libraries_notice() -> str:
    """Notices for libraries linked into the Windows build, with live versions."""
    pyside = distribution_version("PySide6")
    shiboken = distribution_version("shiboken6")
    pymupdf = distribution_version("pymupdf")
    pypdf_version = distribution_version("pypdf")
    pillow = distribution_version("pillow")
    crypto = distribution_version("cryptography")
    pytesseract_version = distribution_version("pytesseract")
    pyinstaller = distribution_version("pyinstaller")
    pymupdf_source = "https://github.com/pymupdf/PyMuPDF"
    if pymupdf != "the version installed with this build":
        pymupdf_source = f"https://github.com/pymupdf/PyMuPDF/releases/tag/{pymupdf}"
    return f"""Python libraries linked into the Windows build

Versions below are read from the environment that generated this notice.
Regenerate it with write_distribution_notices() after changing requirements.txt.
Every runtime package in requirements.txt has an entry. Test-only packages do not.

PyMuPDF {pymupdf}
  Distribution name: pymupdf
  License: GNU AGPL-3.0, or an Artifex commercial license.
  PDFMaster imports this library for open, save, edit, and redaction.
  The AGPL-3.0 text is the GNU AGPL text included with this build
  (vendor/ghostscript/doc/COPYING and the installer license page).
  Corresponding source for this version: {pymupdf_source}
  Corresponding source for PDFMaster: https://github.com/Remo-Consultants/pdfmaster
  Keep producer identification that this library writes into a PDF.
  A commercial license from Artifex is the alternative to the AGPL duties.

PySide6 {pyside} and shiboken6 {shiboken}
  License chosen for this build: LGPL-3.0.
  Copyright The Qt Company Ltd. and the Qt contributors, and the shiboken authors.
  The full LGPL-3.0 text is installed at licenses/LGPL-3.0.txt.
  The Qt and shiboken libraries are separate DLLs in this build.
  You may replace those DLLs under the LGPL-3.0.

pypdf {pypdf_version}
  License: BSD-3-Clause.
  Copyright (c) 2006-2008, Mathieu Fenniak.
  Some contributions copyright (c) 2007, Ashish Kulkarni.
  Some contributions copyright (c) 2014, Steve Witham.
  The license conditions and disclaimer are installed at
  licenses/upstream/pypdf-LICENSE.txt.

Pillow {pillow}
  License: MIT-CMU.
  The Python Imaging Library (PIL):
    Copyright (c) 1997-2011 by Secret Labs AB
    Copyright (c) 1995-2011 by Fredrik Lundh and contributors
  Pillow is the friendly PIL fork:
    Copyright (c) 2010 by Jeffrey 'Alex' Clark and contributors
  Permission to use, copy, modify, and distribute this software and its
  documentation for any purpose and without fee is granted, provided that
  the above copyright notice appears in all copies, and that both that
  copyright notice and this permission notice appear in supporting
  documentation, and that the name of Secret Labs AB or the author not be
  used in advertising or publicity pertaining to distribution of the
  software without specific, written prior permission.
  SECRET LABS AB AND THE AUTHOR DISCLAIM ALL WARRANTIES WITH REGARD TO
  THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
  FITNESS. IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR BE LIABLE FOR
  ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER
  RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF
  CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
  CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
  Notices for image codecs bundled with Pillow are installed at
  licenses/upstream/pillow-LICENSE.txt.

cryptography {crypto}
  License: Apache-2.0 or BSD-3-Clause.
  This Windows build includes OpenSSL inside the cryptography package.
  Copyright The OpenSSL Project.
  The license texts are installed at
  licenses/upstream/cryptography-LICENSE.txt,
  licenses/upstream/cryptography-LICENSE.APACHE, and
  licenses/upstream/cryptography-LICENSE.BSD.

pytesseract {pytesseract_version}
  License: Apache-2.0.
  This is the Python wrapper that starts tesseract.exe. It is not Tesseract.

PyInstaller {pyinstaller}
  The bootloader embedded in PDFMaster.exe is GPL-2.0 or later with this
  exception from the PyInstaller Development Team, Copyright (c) 2010-2023,
  and earlier authors:
  In addition to the permissions in the GNU General Public License, the
  authors give you unlimited permission to link or embed compiled bootloader
  and related files into combinations with other programs, and to distribute
  those combinations without any restriction coming from the use of those
  files. The General Public License restrictions do apply in other respects;
  for example, they cover modification of the files, and distribution when
  not linked into a combined executable.
  The text is installed at licenses/upstream/PyInstaller-COPYING.txt.
"""


def mobile_notice_text() -> str:
    """Notices for the Flutter reader. It does not ship Ghostscript or PyMuPDF."""
    return """Third-party notices for the PDFMaster mobile reader

PDFMaster's own code for the reader is offered with the Windows project's MIT License.
These libraries are included when the reader is built.

pdfrx
  License: MIT. Copyright (c) 2018 Takashi Kawasaki.

PDFium, bundled by pdfium_flutter and pdfium_dart
  License: BSD-3-Clause and Apache-2.0, plus the notices shipped inside PDFium.
  Copyright the PDFium Authors and contributors. Do not use Google's name to
  endorse a product without permission.

Flutter and the Flutter engine
  License: BSD-3-Clause. Copyright the Flutter Authors and Google.

cupertino_icons
  License: MIT.

Material icons, from the Material design icon font included by Flutter
  License: Apache-2.0.

file_picker, share_plus, and shared_preferences, including their platform
implementations
  License: BSD-3-Clause. Copyright the Flutter Authors and the plugin authors.

The share sheet sends a file only to an app the user chooses. The reader does
not upload documents.
"""


def third_party_notice_text() -> str:
    """Attribution required to redistribute the Windows build."""
    bundled = f"""Third-party notices for the PDFMaster Windows build

PDFMaster's own code is under the MIT License (see LICENSE).
The programs below are separate. Their licenses are not MIT.

Ghostscript {GHOSTSCRIPT_VERSION}
  License: GNU AGPL-3.0
  What it does: PDFMaster runs gswin64c.exe to write a PDF/A-2 file.
  PDFMaster does not load gsdll64.dll and does not modify Ghostscript.
  License text: vendor/ghostscript/doc/COPYING
  Source offer next to the binary: vendor/ghostscript/bin/SOURCE.txt
  Corresponding source for this exact version:
    {GHOSTSCRIPT_SOURCE_URL}

Tesseract OCR {TESSERACT_VERSION}
  License: Apache-2.0
  What it does: PDFMaster runs tesseract.exe for OCR, orientation, and deskew.
  Windows build: {TESSERACT_BUILD_URL}
  License text and copyright: vendor/tesseract/doc/LICENSE and vendor/tesseract/doc/AUTHORS
  This build was not modified.

Tesseract language data
  License: Apache-2.0
  Source: https://github.com/tesseract-ocr/tessdata
  Pinned revision: {TESSDATA_COMMIT}
  Files: osd, eng, deu, fra, spa, ita, por, chi_sim, jpn, and pdf.ttf

Libraries in the Tesseract Windows build
  These are unmodified files from the UB-Mannheim installer above.
  Versions are those reported by tesseract.exe {TESSERACT_VERSION}.

  Leptonica 1.84.1 (libleptonica-6.dll) — BSD-2-Clause
    Copyright (C) 2001 Leptonica. All rights reserved.
    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions
    are met:
    1. Redistributions of source code must retain the above copyright
       notice, this list of conditions and the following disclaimer.
    2. Redistributions in binary form must reproduce the above copyright
       notice, this list of conditions and the following disclaimer in
       the documentation and/or other materials provided with the
       distribution.
    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
    "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
    LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
    A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL ANY
    CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
    EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
    PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
    PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
    OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
    OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

  OpenSSL 3 (libcrypto-3-x64.dll) — Apache-2.0
    Copyright The OpenSSL Project. The Apache-2.0 text in
    vendor/tesseract/doc/LICENSE covers these terms.

  Image and compression libraries linked by this Tesseract build:
    giflib 5.2.1 — MIT
    libjpeg-turbo 3.0.1 — IJG License, BSD-3-Clause, and zlib components
    libpng 1.6.43 — PNG Reference Library License version 2
    libtiff 4.6.0 — libtiff License
    zlib 1.3 — zlib License. Copyright (C) 1995-2023 Jean-loup Gailly and Mark Adler.
    libwebp 1.4.0 — BSD-3-Clause
    OpenJPEG 2.5.2 — BSD-2-Clause
    libarchive 3.7.4 — BSD-2-Clause
    liblzma 5.6.1 — BSD Zero Clause License
    bzip2 1.0.8 — bzip2 License
    LZ4 1.9.4 — BSD-2-Clause
    Zstandard 1.5.6 — BSD-3-Clause

  Other libraries installed beside tesseract.exe:
    FreeType (libfreetype-6.dll) — FreeType Project License (FTL)
    HarfBuzz (libharfbuzz-0.dll) — MIT
    ICU (libicu*.dll) — Unicode License
    libgcc_s_seh-1.dll, libstdc++-6.dll, libwinpthread-1.dll —
      GPL-3.0 with the GCC Runtime Library Exception, which allows
      combining those runtime libraries with this program.

  LGPL libraries, shipped as separate DLLs next to tesseract.exe:
    GLib (libglib-2.0-0.dll, libgobject-2.0-0.dll, libgio-2.0-0.dll,
      libgmodule-2.0-0.dll) — LGPL-2.1-or-later
    Cairo (libcairo-2.dll) — LGPL-2.1-only or MPL-1.1.
      This distribution follows the LGPL-2.1 terms.
    Pango (libpango-1.0-0.dll, libpangocairo-1.0-0.dll,
      libpangoft2-1.0-0.dll, libpangowin32-1.0-0.dll) — LGPL-2.1-or-later

  You may replace those GLib, Cairo, and Pango DLLs with compatible
  modified versions. PDFMaster does not link them into PDFMaster.exe.
  tesseract.exe, a separate program, loads them.
  PDFMaster did not modify GLib, Cairo, or Pango. Their source is the
  source of the versions in the UB-Mannheim build:
    {TESSERACT_BUILD_URL}
  The LGPL-2.1 text is installed at licenses/LGPL-2.1.txt.

pytesseract, the Python wrapper that starts tesseract.exe, is Apache-2.0.
"""
    return bundled + "\n" + python_libraries_notice()


def terms_file(root: Path | None = None) -> Path:
    """Terms of use for a source tree, or for a frozen Windows build."""
    import sys

    if root is not None:
        return Path(root) / "TERMS_OF_USE.txt"
    if getattr(sys, "frozen", False):
        bundled = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidate = bundled / "TERMS_OF_USE.txt"
        if candidate.is_file():
            return candidate
        return Path(sys.executable).parent / "TERMS_OF_USE.txt"
    return Path(__file__).resolve().parent.parent / "TERMS_OF_USE.txt"


def read_terms(root: Path | None = None) -> str:
    """Return the terms of use shipped with this copy."""
    path = terms_file(root)
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return "Terms of use were not found in this copy of PDFMaster."


def privacy_file(root: Path | None = None) -> Path:
    """Privacy notice for a source tree, or for a frozen Windows build."""
    import sys

    if root is not None:
        return Path(root) / "PRIVACY.txt"
    if getattr(sys, "frozen", False):
        bundled = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidate = bundled / "PRIVACY.txt"
        if candidate.is_file():
            return candidate
        return Path(sys.executable).parent / "PRIVACY.txt"
    return Path(__file__).resolve().parent.parent / "PRIVACY.txt"


def read_privacy(root: Path | None = None) -> str:
    """Return the privacy notice shipped with this copy."""
    path = privacy_file(root)
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return "The privacy notice was not found in this copy of PDFMaster."


def notices_file(root: Path | None = None) -> Path:
    """Notices file for a source tree, or for a frozen Windows build."""
    import sys

    if root is not None:
        return Path(root) / "THIRD_PARTY_NOTICES.txt"
    if getattr(sys, "frozen", False):
        bundled = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidate = bundled / "THIRD_PARTY_NOTICES.txt"
        if candidate.is_file():
            return candidate
        return Path(sys.executable).parent / "THIRD_PARTY_NOTICES.txt"
    return Path(__file__).resolve().parent.parent / "THIRD_PARTY_NOTICES.txt"


def read_notices(root: Path | None = None) -> str:
    """Return the installed notice, or the generated text if it is not on disk yet."""
    path = notices_file(root)
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return third_party_notice_text()


def _read_if_present(path: Path) -> str:
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return (
        f"The full text is installed at {path.name} once the bundled "
        "programs have been fetched. Run scripts/fetch_bundled_tools.py.\n"
    )


def bundle_license_text(root: Path) -> str:
    """Installer page: terms of use, then the MIT and third-party license texts."""
    root = Path(root)
    mit = (root / "LICENSE").read_text(encoding="utf-8").strip()
    lgpl_path = root / "licenses" / "LGPL-2.1.txt"
    if not lgpl_path.is_file():
        raise FileNotFoundError(f"Missing {lgpl_path}")
    lgpl = lgpl_path.read_text(encoding="utf-8").strip()
    agpl = _read_if_present(root / "vendor" / "ghostscript" / "doc" / "COPYING").strip()
    apache = _read_if_present(root / "vendor" / "tesseract" / "doc" / "LICENSE").strip()
    terms = read_terms(root).strip()
    privacy = read_privacy(root).strip()
    lgpl3_path = root / "licenses" / "LGPL-3.0.txt"
    if not lgpl3_path.is_file():
        raise FileNotFoundError(f"Missing {lgpl3_path}")
    lgpl3 = lgpl3_path.read_text(encoding="utf-8").strip()
    return (
        f"{terms}\n"
        "\n"
        "===== Privacy notice =====\n"
        "\n"
        f"{privacy}\n"
        "\n"
        "===== Open-source licenses included in this installer =====\n"
        "\n"
        "This installer contains more than one program.\n"
        "\n"
        "  PDFMaster's own code is under the MIT License.\n"
        "  PyMuPDF is under the GNU AGPL-3.0, or an Artifex commercial license.\n"
        f"  Ghostscript {GHOSTSCRIPT_VERSION} is under the GNU AGPL-3.0.\n"
        "    It is a separate program. The MIT License does not replace the AGPL.\n"
        "  PySide6 and shiboken6 are under the LGPL-3.0 for this build.\n"
        f"  Tesseract OCR {TESSERACT_VERSION} is under the Apache-2.0,\n"
        "    together with the libraries named in the notice below.\n"
        "\n"
        "The complete texts follow.\n"
        "\n"
        "===== PDFMaster MIT License =====\n"
        "\n"
        f"{mit}\n"
        "\n"
        "===== Third-party notice =====\n"
        "\n"
        f"{third_party_notice_text().strip()}\n"
        "\n"
        "===== Ghostscript and PyMuPDF GNU AGPL-3.0 =====\n"
        "\n"
        f"{agpl}\n"
        "\n"
        "===== Tesseract Apache-2.0 =====\n"
        "\n"
        f"{apache}\n"
        "\n"
        "===== GNU LGPL-2.1 (GLib, Cairo, and Pango) =====\n"
        "\n"
        f"{lgpl}\n"
        "\n"
        "===== GNU LGPL-3.0 (Qt and shiboken) =====\n"
        "\n"
        f"{lgpl3}\n"
    )


def write_distribution_notices(root: Path) -> None:
    """Write the notice files the package, the installer, and the mobile app ship."""
    root = Path(root)
    notice = third_party_notice_text()
    (root / "THIRD_PARTY_NOTICES.txt").write_text(notice, encoding="utf-8", newline="\n")
    _copy_upstream_license_files(root)
    bundle = bundle_license_text(root)
    installer = root / "installer"
    installer.mkdir(parents=True, exist_ok=True)
    # NSIS displays the license page correctly when the file uses CRLF.
    (installer / "BUNDLE_LICENSE.txt").write_text(bundle, encoding="utf-8", newline="\r\n")
    vendor = root / "vendor"
    if vendor.is_dir():
        (vendor / "NOTICE.md").write_text(notice, encoding="utf-8", newline="\n")
    gs_bin = vendor / "ghostscript" / "bin"
    if gs_bin.is_dir():
        (gs_bin / "SOURCE.txt").write_text(
            ghostscript_source_offer(),
            encoding="utf-8",
            newline="\r\n",
        )
    _write_mobile_legal_assets(root)


def _copy_upstream_license_files(root: Path) -> None:
    """Copy license files out of installed wheels so the build can ship them."""
    try:
        from importlib.metadata import distribution
    except ImportError:
        return
    wanted = {
        "pypdf": ("pypdf-LICENSE.txt", ("licenses/LICENSE",)),
        "pillow": ("pillow-LICENSE.txt", ("licenses/LICENSE",)),
        "cryptography": ("cryptography-LICENSE.txt", ("licenses/LICENSE",)),
        "PyInstaller": ("PyInstaller-COPYING.txt", ("licenses/COPYING.txt",)),
    }
    extra = {
        "cryptography": (
            ("cryptography-LICENSE.APACHE", "licenses/LICENSE.APACHE"),
            ("cryptography-LICENSE.BSD", "licenses/LICENSE.BSD"),
        )
    }
    destination = root / "licenses" / "upstream"
    destination.mkdir(parents=True, exist_ok=True)
    for dist_name, (output_name, suffixes) in wanted.items():
        copied = _copy_dist_file(distribution, dist_name, suffixes, destination / output_name)
        if not copied:
            continue
    for dist_name, pairs in extra.items():
        for output_name, suffix in pairs:
            _copy_dist_file(distribution, dist_name, (suffix,), destination / output_name)


def _copy_dist_file(distribution, dist_name: str, suffixes: tuple[str, ...], destination: Path) -> bool:
    try:
        dist = distribution(dist_name)
    except Exception:
        return False
    files = dist.files or []
    for item in files:
        text = str(item).replace("\\", "/")
        if any(text.endswith(suffix) for suffix in suffixes):
            source = Path(str(item.locate()))
            if source.is_file():
                destination.write_bytes(source.read_bytes())
                return True
    return False


def _write_mobile_legal_assets(root: Path) -> None:
    """Keep the Flutter reader's legal assets in step with the desktop texts."""
    mobile = root.parent / "pdfmaster_mobile" / "assets" / "legal"
    if not (root.parent / "pdfmaster_mobile").is_dir():
        return
    mobile.mkdir(parents=True, exist_ok=True)
    (mobile / "THIRD_PARTY_NOTICES.txt").write_text(
        mobile_notice_text(),
        encoding="utf-8",
        newline="\n",
    )
    for name in ("TERMS_OF_USE.txt", "PRIVACY.txt"):
        source = root / name
        if source.is_file():
            (mobile / name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
