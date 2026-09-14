#!/usr/bin/env python3
"""Capture product-page screenshots from the live MainWindow.

Run from the repo root (with the project venv activated)::

    python scripts/capture_product_screens.py

Writes PNGs under ``docs/assets/screenshots/``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import fitz
from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "docs" / "assets" / "screenshots"
MAX_WIDTH = 1280


def _wait(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def _save(widget, name: str) -> Path:
    pix = widget.grab()
    if pix.width() > MAX_WIDTH:
        pix = pix.scaledToWidth(MAX_WIDTH, Qt.TransformationMode.SmoothTransformation)
    path = OUT / name
    pix.save(str(path), "PNG")
    print(f"Wrote {path} ({pix.width()}x{pix.height()})")
    return path


def _sample_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 72), "PDFMaster", fontsize=28)
    page.insert_text((72, 110), "The desk, not the cloud.", fontsize=14)
    page.insert_text(
        (72, 150),
        "Offline-first PDF viewer and editor for Windows.",
        fontsize=11,
    )
    page.insert_text((72, 190), "Review · Compare · PDF/A · Search · Batch", fontsize=11)
    page2 = doc.new_page(width=612, height=792)
    page2.insert_text((72, 72), "Page 2", fontsize=18)
    page2.insert_text((72, 110), "Multi-document tabs keep zoom and undo per file.", fontsize=11)
    doc.save(path)
    doc.close()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    # Prefer a visible light scheme for marketing shots.
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication.instance() or QApplication(sys.argv)

    from src.ui.main_window import MainWindow

    win = MainWindow()
    win.resize(1280, 820)
    win.show()
    win.raise_()
    app.processEvents()
    _wait(400)

    _save(win, "welcome.png")

    sample = OUT / "_sample.pdf"
    _sample_pdf(sample)

    win.open_file(str(sample))
    app.processEvents()
    _wait(900)

    review_idx = win._ribbon._tab_indices.get("review")
    if review_idx is not None:
        win._ribbon._tab_widget.setCurrentIndex(review_idx)
    app.processEvents()
    _wait(250)
    _save(win, "workspace-review.png")

    markup_idx = win._ribbon._tab_indices.get("markup")
    if markup_idx is not None:
        win._ribbon._tab_widget.setCurrentIndex(markup_idx)
    app.processEvents()
    _wait(250)
    _save(win, "workspace-markup.png")

    # Close tabs so the sample PDF handle is released before exit.
    win._tabs.close_all(force=True)
    app.processEvents()
    win.close()
    if sample.exists():
        sample.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
