#!/usr/bin/env python3
"""Build script for PDFMaster Windows distribution.

1. Builds the app with PyInstaller (folder distribution preferred)
2. Creates a ZIP portable package
3. Optionally builds an NSIS Setup.exe when ``makensis`` is on PATH

Usage:
    python installer/build_installer.py [--onefile] [--nsis] [--clean]
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Keep in sync with src.constants.APP_VERSION
sys.path.insert(0, str(ROOT))
try:
    from src.constants import APP_NAME, APP_VERSION as VERSION
except Exception:  # noqa: BLE001
    APP_NAME = "PDFMaster"
    VERSION = "0.5.0"


def run_command(cmd: list[str], cwd: Path = ROOT) -> bool:
    """Run a command and return success status."""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=cwd, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as exc:
        print(f"Command failed with code {exc.returncode}")
        return False
    except FileNotFoundError:
        print(f"Command not found: {cmd[0]}")
        return False


def clean_build() -> None:
    """Clean previous build artifacts (keeps pdfmaster.spec)."""
    for path in ["build", "dist"]:
        full_path = ROOT / path
        if full_path.exists():
            shutil.rmtree(full_path)
            print(f"Cleaned: {path}")
    generated = ROOT / f"{APP_NAME}.spec"
    if generated.exists() and generated.resolve() != (ROOT / "pdfmaster.spec").resolve():
        generated.unlink()
        print(f"Cleaned: {generated.name}")


def build_pyinstaller(onefile: bool = False) -> bool:
    """Build with PyInstaller using the checked-in spec when possible."""
    spec = ROOT / "pdfmaster.spec"
    icon_path = ROOT / "resources" / "icons" / "pdfmaster.ico"
    icons_dir = ROOT / "resources" / "icons"

    if not onefile and spec.exists():
        return run_command(
            [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", str(spec)]
        )

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        APP_NAME,
        "--windowed",
        "--noconfirm",
        "--clean",
        "--paths",
        str(ROOT),
    ]

    if icon_path.exists():
        cmd.extend(["--icon", str(icon_path)])

    if icons_dir.is_dir():
        cmd.extend(
            [
                "--add-data",
                f"{icons_dir}{os.pathsep}resources/icons",
            ]
        )

    for module in (
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtPrintSupport",
        "pymupdf",
        "pypdf",
        "PIL",
        "PIL.Image",
    ):
        cmd.extend(["--hidden-import", module])

    if onefile:
        cmd.append("--onefile")

    cmd.append(str(ROOT / "src" / "main.py"))
    return run_command(cmd)


def create_zip_distribution() -> Path | None:
    """Create a ZIP file of the folder distribution."""
    dist_dir = ROOT / "dist" / APP_NAME
    if not dist_dir.exists():
        # onefile layout
        exe = ROOT / "dist" / f"{APP_NAME}.exe"
        if exe.exists():
            zip_name = f"{APP_NAME}-{VERSION}-win64-onefile"
            archive_base = ROOT / "dist" / zip_name
            staging = ROOT / "dist" / "_onefile_stage"
            if staging.exists():
                shutil.rmtree(staging)
            staging.mkdir(parents=True)
            shutil.copy2(exe, staging / f"{APP_NAME}.exe")
            shutil.make_archive(str(archive_base), "zip", staging)
            shutil.rmtree(staging)
            zip_file = Path(str(archive_base) + ".zip")
            print(f"Created: {zip_file}")
            return zip_file
        print(f"Distribution not found at {dist_dir}")
        return None

    zip_name = f"{APP_NAME}-{VERSION}-win64"
    archive_base = ROOT / "dist" / zip_name
    shutil.make_archive(str(archive_base), "zip", ROOT / "dist", APP_NAME)
    zip_file = Path(str(archive_base) + ".zip")
    print(f"Created: {zip_file}")
    return zip_file


def create_nsis_installer() -> bool:
    """Create Windows installer with NSIS."""
    nsis_script = ROOT / "installer" / "pdfmaster.nsi"
    if not nsis_script.exists():
        print("NSIS script not found, skipping installer creation")
        return False

    makensis = shutil.which("makensis")
    if not makensis:
        # Common winget / Program Files locations
        candidates = [
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
            / "NSIS"
            / "makensis.exe",
            Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
            / "NSIS"
            / "makensis.exe",
        ]
        for candidate in candidates:
            if candidate.is_file():
                makensis = str(candidate)
                break

    if not makensis:
        print("NSIS (makensis) not found, skipping installer creation")
        print("Install from https://nsis.sourceforge.io/ or: winget install NSIS.NSIS")
        return False

    return run_command([makensis, str(nsis_script)])


def main() -> int:
    parser = argparse.ArgumentParser(description="Build PDFMaster installer")
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Build as single executable (slower startup)",
    )
    parser.add_argument("--nsis", action="store_true", help="Create NSIS Setup.exe")
    parser.add_argument("--clean", action="store_true", help="Clean build artifacts first")
    args = parser.parse_args()

    if args.clean:
        clean_build()

    print(f"Building {APP_NAME} v{VERSION}...")

    if not build_pyinstaller(args.onefile):
        print("PyInstaller build failed")
        return 1

    zip_path = create_zip_distribution()
    if zip_path:
        print(f"ZIP distribution: {zip_path}")

    if args.nsis:
        if create_nsis_installer():
            print("NSIS installer created successfully")
        else:
            print("NSIS installer creation skipped or failed")

    print("\nBuild complete!")
    print(f"Folder dist: {ROOT / 'dist' / APP_NAME}")
    if zip_path:
        print(f"Portable ZIP: {zip_path}")
    setup = ROOT / "dist" / f"{APP_NAME}-{VERSION}-Setup.exe"
    if setup.exists():
        print(f"Setup.exe: {setup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
