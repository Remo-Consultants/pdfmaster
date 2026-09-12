"""Shared pytest fixtures and path bootstrap for the PDFMaster suite."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Qt must run headless in CI and during local test runs.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pymupdf as fitz  # noqa: E402


@pytest.fixture
def make_pdf(tmp_path: Path):
    """Return a factory that writes a simple multi-page PDF to tmp_path."""

    def _make(name: str = "sample.pdf", pages: int = 3, width: int = 612,
              height: int = 792) -> Path:
        path = tmp_path / name
        doc = fitz.open()
        for index in range(pages):
            page = doc.new_page(width=width, height=height)
            page.insert_text((72, 72), f"Page {index + 1}")
        doc.save(path)
        doc.close()
        return path

    return _make


@pytest.fixture
def make_text_pdf(tmp_path: Path):
    """Return a factory for a PDF with known, searchable text lines."""

    def _make(name: str = "text.pdf", lines=None, fontsize: int = 12) -> Path:
        lines = lines or ["Invoice Date: 2024-01-01", "Customer: ACME Corp",
                          "Total: 100.00", "SECRET reference 42"]
        path = tmp_path / name
        doc = fitz.open()
        page = doc.new_page(width=612, height=792)
        y = 100
        for line in lines:
            page.insert_text((72, y), line, fontname="helv", fontsize=fontsize)
            y += fontsize * 2.5
        doc.save(path)
        doc.close()
        return path

    return _make


@pytest.fixture
def make_form_pdf(tmp_path: Path):
    """Return a factory for a PDF containing AcroForm fields."""

    def _make(name: str = "form.pdf") -> Path:
        path = tmp_path / name
        doc = fitz.open()
        page = doc.new_page(width=612, height=792)

        text = fitz.Widget()
        text.field_name = "customer"
        text.field_type = fitz.PDF_WIDGET_TYPE_TEXT
        text.rect = fitz.Rect(100, 100, 350, 130)
        text.field_value = "initial"
        page.add_widget(text)

        check = fitz.Widget()
        check.field_name = "agree"
        check.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
        check.rect = fitz.Rect(100, 150, 120, 170)
        check.field_value = False
        page.add_widget(check)

        combo = fitz.Widget()
        combo.field_name = "plan"
        combo.field_type = fitz.PDF_WIDGET_TYPE_COMBOBOX
        combo.rect = fitz.Rect(100, 200, 300, 230)
        combo.choice_values = ["basic", "pro", "enterprise"]
        combo.field_value = "basic"
        page.add_widget(combo)

        doc.save(path)
        doc.close()
        return path

    return _make


@pytest.fixture
def make_image(tmp_path: Path):
    """Return a factory that writes a small PNG for insertion tests."""

    def _make(name: str = "stamp.png", size=(160, 60)) -> Path:
        from PIL import Image

        path = tmp_path / name
        Image.new("RGB", size, (10, 90, 200)).save(path)
        return path

    return _make


@pytest.fixture
def isolated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point recent-file storage at tmp_path instead of the real home dir."""
    config = tmp_path / "config"
    config.mkdir(exist_ok=True)
    monkeypatch.setattr("src.ui.main_window.CONFIG_DIR", config, raising=False)
    return config


@pytest.fixture
def silent_dialogs(monkeypatch: pytest.MonkeyPatch):
    """Auto-accept QMessageBox prompts so tests never block on modals."""
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "about", staticmethod(lambda *a, **k: None))

    # Any editing dialog reached without an explicit patch behaves as if the
    # user pressed Cancel. Without this, a modal exec() blocks forever under
    # the offscreen platform and the whole run hangs.
    from PySide6.QtWidgets import QDialog

    from src.ui import dialogs

    for name in dialogs.__all__:
        candidate = getattr(dialogs, name)
        if isinstance(candidate, type) and issubclass(candidate, QDialog):
            monkeypatch.setattr(
                candidate, "exec",
                lambda self: QDialog.DialogCode.Rejected,
                raising=False,
            )


@pytest.fixture
def main_window(qtbot, isolated_config, silent_dialogs):
    """A shown MainWindow wired to qtbot, closed cleanly on teardown."""
    from src.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.resize(1000, 700)
    window.show()
    qtbot.waitExposed(window)
    yield window
    # Mark all documents as unmodified so close_all won't prompt.
    for tab in window._tabs._tabs:
        tab.document._modified = False
    # Thumbnail workers share the document handle, so stop them before it
    # is closed.
    window.thumbnails.set_document(None)
    window.thumbnails.wait_for_render()
    # Close all tabs without prompting.
    window._tabs.close_all(force=True)


def open_and_wait(qtbot, window, path: Path) -> None:
    """Open a PDF in the window and wait for the first async render."""
    from PySide6.QtWidgets import QApplication

    window._load_path(str(path))
    # The viewer now exists after loading. Wait for render to complete.
    viewer = window.viewer
    if viewer is not None:
        # wait_for_render waits for in-flight jobs, then process events
        # to let the pixmap land in the cache.
        viewer.wait_for_render()
        for _ in range(50):
            QApplication.processEvents()
            if viewer.page_pixmap(0) is not None:
                break


def act_and_wait(qtbot, viewer, action) -> None:
    """Run an action that triggers a render and wait for it to land."""
    from PySide6.QtWidgets import QApplication

    with qtbot.waitSignal(viewer.render_finished, timeout=15_000):
        action()
    # Process events to let the pixmap land in the cache.
    viewer.wait_for_render()
    for _ in range(50):
        QApplication.processEvents()
        if viewer.page_pixmap(0) is not None:
            break
