# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for PDFMaster.

Build with: pyinstaller pdfmaster.spec

This creates a single-folder distribution with all dependencies.
For a single executable, set onefile=True (larger startup time).
"""

import sys
from pathlib import Path

block_cipher = None

# Project root
ROOT = Path(SPECPATH)
sys.path.insert(0, str(ROOT))
from src.licensing import ship_bundled_file, write_distribution_notices

write_distribution_notices(ROOT)

datas = []
if (ROOT / 'resources' / 'icons').is_dir():
    datas.append((str(ROOT / 'resources' / 'icons'), 'resources/icons'))


def _add_tree(source: Path, dest: str, folder_name: str) -> None:
    """Add a vendor tree, leaving out Tesseract files we do not ship."""
    for path in source.rglob('*'):
        if not path.is_file():
            continue
        if not ship_bundled_file(folder_name, path):
            continue
        relative = path.relative_to(source).parent.as_posix()
        target = dest if relative in ('.', '') else f'{dest}/{relative}'
        datas.append((str(path), target))


for bundled in ('tesseract', 'ghostscript'):
    folder = ROOT / 'vendor' / bundled
    if folder.is_dir():
        _add_tree(folder, f'vendor/{bundled}', bundled)
for extra in (
    (ROOT / 'TERMS_OF_USE.txt', '.'),
    (ROOT / 'PRIVACY.txt', '.'),
    (ROOT / 'THIRD_PARTY_NOTICES.txt', '.'),
    (ROOT / 'LICENSE', '.'),
    (ROOT / 'installer' / 'BUNDLE_LICENSE.txt', '.'),
    (ROOT / 'vendor' / 'NOTICE.md', 'vendor'),
):
    if extra[0].is_file():
        datas.append((str(extra[0]), extra[1]))
license_root = ROOT / 'licenses'
if license_root.is_dir():
    _add_tree(license_root, 'licenses', 'licenses')

# Collect all source files
a = Analysis(
    [str(ROOT / 'src' / 'main.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtPrintSupport',
        'pymupdf',
        'pypdf',
        'PIL',
        'PIL.Image',
        'pytesseract',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PySide6.QtNetwork',
        'PySide6.QtQml',
        'PySide6.QtQuick',
        'PySide6.QtWebEngine',
        'PySide6.QtMultimedia',
        'tkinter',
        'matplotlib',
        'numpy.tests',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PDFMaster',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / 'resources' / 'icons' / 'pdfmaster.ico') if (ROOT / 'resources' / 'icons' / 'pdfmaster.ico').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PDFMaster',
)
