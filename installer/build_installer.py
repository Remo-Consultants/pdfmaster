#!/usr/bin/env python3
"""Build script for PDFMaster installer.

This script:
1. Builds the application with PyInstaller
2. Creates a Windows installer with NSIS (if available)
3. Creates a ZIP distribution

Usage:
    python installer/build_installer.py [--onefile] [--nsis]
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

VERSION = "0.5.0"
APP_NAME = "PDFMaster"


def run_command(cmd: list, cwd: Path = ROOT) -> bool:
    """Run a command and return success status."""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=cwd, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Command failed with code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"Command not found: {cmd[0]}")
        return False


def clean_build() -> None:
    """Clean previous build artifacts."""
    for path in ["build", "dist", f"{APP_NAME}.spec"]:
        full_path = ROOT / path
        if full_path.exists():
            if full_path.is_dir():
                shutil.rmtree(full_path)
            else:
                full_path.unlink()
            print(f"Cleaned: {path}")


def build_pyinstaller(onefile: bool = False) -> bool:
    """Build with PyInstaller."""
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--windowed",
        "--noconfirm",
        "--clean",
    ]

    icon_path = ROOT / "resources" / "icons" / "pdfmaster.ico"
    if icon_path.exists():
        cmd.extend(["--icon", str(icon_path)])

    cmd.extend([
        "--add-data", f"{ROOT / 'resources' / 'icons'}{os.pathsep}resources/icons",
    ])

    hidden_imports = [
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtPrintSupport",
        "pymupdf",
        "pypdf",
        "PIL",
        "PIL.Image",
    ]

    for module in hidden_imports:
        cmd.extend(["--hidden-import", module])

    if onefile:
        cmd.append("--onefile")

    cmd.append(str(ROOT / "src" / "main.py"))

    return run_command(cmd)


def create_zip_distribution() -> Path:
    """Create a ZIP file of the distribution."""
    dist_dir = ROOT / "dist" / APP_NAME
    if not dist_dir.exists():
        print(f"Distribution not found at {dist_dir}")
        return None

    zip_name = f"{APP_NAME}-{VERSION}-win64"
    zip_path = ROOT / "dist" / zip_name

    shutil.make_archive(str(zip_path), "zip", ROOT / "dist", APP_NAME)
    print(f"Created: {zip_path}.zip")
    return zip_path.with_suffix(".zip")


def create_nsis_installer() -> bool:
    """Create Windows installer with NSIS."""
    nsis_script = ROOT / "installer" / "pdfmaster.nsi"
    if not nsis_script.exists():
        print("NSIS script not found, skipping installer creation")
        return False

    if not shutil.which("makensis"):
        print("NSIS (makensis) not found, skipping installer creation")
        return False

    return run_command(["makensis", str(nsis_script)])


def main() -> int:
    parser = argparse.ArgumentParser(description="Build PDFMaster installer")
    parser.add_argument("--onefile", action="store_true",
                        help="Build as single executable")
    parser.add_argument("--nsis", action="store_true",
                        help="Create NSIS installer")
    parser.add_argument("--clean", action="store_true",
                        help="Clean build artifacts first")
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
            print("NSIS installer creation failed")

    print("\nBuild complete!")
    print(f"Distribution: {ROOT / 'dist' / APP_NAME}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
