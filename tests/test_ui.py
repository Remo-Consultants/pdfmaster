"""GUI tests driven headlessly through pytest-qt."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.conftest import act_and_wait, open_and_wait

pytest.importorskip("pytestqt")


def test_window_starts_empty(main_window) -> None:
    assert main_window.document is None
    assert not main_window.save_action.isEnabled()
    assert not main_window.delete_action.isEnabled()
    assert main_window._page_count_label.text().strip() == "/ 0"


def test_open_pdf_populates_ui(qtbot, main_window, make_pdf) -> None:
    pdf = make_pdf(pages=5)
    open_and_wait(qtbot, main_window, pdf)

    assert main_window.document.page_count == 5
    assert main_window._page_spin.value() == 1
    assert main_window._page_spin.maximum() == 5
    assert main_window._page_count_label.text().strip() == "/ 5"
    assert pdf.name in main_window.windowTitle()
    assert main_window.save_action.isEnabled()
    assert main_window.viewer.page_pixmap(0) is not None


def test_navigation_updates_spinbox(qtbot, main_window, make_pdf) -> None:
    pdf = make_pdf(pages=4)
    open_and_wait(qtbot, main_window, pdf)

    act_and_wait(qtbot, main_window.viewer, main_window.next_page)
    assert main_window._page_spin.value() == 2

    act_and_wait(qtbot, main_window.viewer, main_window.last_page)
    assert main_window._page_spin.value() == 4

    main_window.next_page()  # already at the end, must not overshoot
    assert main_window.viewer.current_page == 3

    act_and_wait(qtbot, main_window.viewer, main_window.first_page)
    assert main_window._page_spin.value() == 1

    main_window.previous_page()  # already at the start
    assert main_window.viewer.current_page == 0


def test_spinbox_jumps_to_page(qtbot, main_window, make_pdf) -> None:
    pdf = make_pdf(pages=10)
    open_and_wait(qtbot, main_window, pdf)
    act_and_wait(qtbot, main_window.viewer,
                 lambda: main_window._page_spin.setValue(7))
    assert main_window.viewer.current_page == 6


def test_zoom_controls_and_limits(qtbot, main_window, make_pdf) -> None:
    pdf = make_pdf(pages=1)
    open_and_wait(qtbot, main_window, pdf)

    act_and_wait(qtbot, main_window.viewer, main_window.zoom_in)
    assert main_window.viewer.zoom_level == pytest.approx(1.1)
    assert main_window._zoom_label.text() == "110%"
    assert main_window._zoom_slider.value() == 110

    act_and_wait(qtbot, main_window.viewer, main_window.zoom_out)
    assert main_window.viewer.zoom_level == pytest.approx(1.0)

    act_and_wait(qtbot, main_window.viewer,
                 lambda: main_window.viewer.set_zoom(99.0))
    assert main_window.viewer.zoom_level == pytest.approx(4.0)

    act_and_wait(qtbot, main_window.viewer,
                 lambda: main_window.viewer.set_zoom(0.01))
    assert main_window.viewer.zoom_level == pytest.approx(0.25)


def test_slider_drives_zoom(qtbot, main_window, make_pdf) -> None:
    pdf = make_pdf(pages=1)
    open_and_wait(qtbot, main_window, pdf)
    act_and_wait(qtbot, main_window.viewer,
                 lambda: main_window._zoom_slider.setValue(250))
    assert main_window.viewer.zoom_level == pytest.approx(2.5)
    assert main_window._zoom_label.text() == "250%"


def test_fit_to_width_fills_viewport(qtbot, main_window, make_pdf) -> None:
    pdf = make_pdf(pages=1, width=400, height=800)
    open_and_wait(qtbot, main_window, pdf)
    act_and_wait(qtbot, main_window.viewer, main_window.fit_to_width)

    rendered = main_window.viewer.page_pixmap(0).width()
    viewport = main_window.viewer.viewport().width()
    assert rendered <= viewport
    assert rendered >= viewport - 40  # actually fills, not just fits


def test_fit_to_width_after_rotation(qtbot, main_window, make_pdf) -> None:
    """Regression: rotation was double-counted, overflowing the viewport 2x."""
    pdf = make_pdf(pages=1, width=400, height=800)
    open_and_wait(qtbot, main_window, pdf)
    act_and_wait(qtbot, main_window.viewer, main_window.rotate_clockwise)
    act_and_wait(qtbot, main_window.viewer, main_window.fit_to_width)

    rendered = main_window.viewer.page_pixmap(0).width()
    viewport = main_window.viewer.viewport().width()
    assert rendered <= viewport, f"rotated page overflows by {rendered - viewport}px"
    assert rendered >= viewport - 40


def test_fit_to_page_after_rotation(qtbot, main_window, make_pdf) -> None:
    pdf = make_pdf(pages=1, width=400, height=800)
    open_and_wait(qtbot, main_window, pdf)
    act_and_wait(qtbot, main_window.viewer, main_window.rotate_clockwise)
    act_and_wait(qtbot, main_window.viewer, main_window.fit_to_page)

    pixmap = main_window.viewer.page_pixmap(0)
    viewport = main_window.viewer.viewport().size()
    assert pixmap.width() <= viewport.width()
    assert pixmap.height() <= viewport.height()
    # A landscape page in a landscape viewport should be width-limited.
    assert pixmap.width() >= viewport.width() - 40


def test_rotation_cycles_and_marks_modified(qtbot, main_window, make_pdf) -> None:
    pdf = make_pdf(pages=2)
    open_and_wait(qtbot, main_window, pdf)

    act_and_wait(qtbot, main_window.viewer, main_window.rotate_clockwise)
    assert main_window.viewer.rotation == 90
    act_and_wait(qtbot, main_window.viewer, main_window.rotate_clockwise)
    assert main_window.viewer.rotation == 180
    act_and_wait(qtbot, main_window.viewer, main_window.rotate_counterclockwise)
    assert main_window.viewer.rotation == 90
    assert main_window.document.is_modified

    act_and_wait(qtbot, main_window.viewer, main_window.reset_view)
    assert main_window.viewer.rotation == 0
    assert main_window.viewer.zoom_level == pytest.approx(1.0)


def test_rotation_is_per_page(qtbot, main_window, make_pdf) -> None:
    pdf = make_pdf(pages=3)
    open_and_wait(qtbot, main_window, pdf)
    act_and_wait(qtbot, main_window.viewer, main_window.rotate_clockwise)
    act_and_wait(qtbot, main_window.viewer, main_window.next_page)
    assert main_window.viewer.rotation == 0
    act_and_wait(qtbot, main_window.viewer, main_window.previous_page)
    assert main_window.viewer.rotation == 90


def test_delete_page_updates_counters(qtbot, main_window, make_pdf) -> None:
    pdf = make_pdf(pages=3)
    open_and_wait(qtbot, main_window, pdf)
    act_and_wait(qtbot, main_window.viewer, main_window.delete_current_page)

    assert main_window.document.page_count == 2
    assert main_window._page_spin.maximum() == 2
    assert main_window._page_count_label.text().strip() == "/ 2"


def test_delete_last_page_clamps_view(qtbot, main_window, make_pdf) -> None:
    pdf = make_pdf(pages=3)
    open_and_wait(qtbot, main_window, pdf)
    act_and_wait(qtbot, main_window.viewer, main_window.last_page)
    act_and_wait(qtbot, main_window.viewer, main_window.delete_current_page)

    assert main_window.viewer.current_page == 1
    assert main_window._page_spin.value() == 2


def test_cannot_delete_only_page(qtbot, main_window, make_pdf) -> None:
    pdf = make_pdf(pages=1)
    open_and_wait(qtbot, main_window, pdf)
    main_window.delete_current_page()
    assert main_window.document.page_count == 1


def test_save_as_writes_file(qtbot, main_window, make_pdf, tmp_path, monkeypatch) -> None:
    from PySide6.QtWidgets import QFileDialog

    pdf = make_pdf(pages=3)
    open_and_wait(qtbot, main_window, pdf)
    act_and_wait(qtbot, main_window.viewer, main_window.delete_current_page)

    target = tmp_path / "saved_copy"  # deliberately missing the extension
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(target), "")))
    main_window.save_file_as()

    assert (tmp_path / "saved_copy.pdf").exists()
    assert not main_window.document.is_modified


def test_invalid_file_is_rejected(qtbot, main_window, tmp_path) -> None:
    bogus = tmp_path / "fake.pdf"
    bogus.write_bytes(b"this is not a pdf at all")
    main_window._load_path(str(bogus))
    assert main_window.document is None


def test_recent_files_menu_records_opens(qtbot, main_window, make_pdf) -> None:
    pdf = make_pdf(pages=1)
    open_and_wait(qtbot, main_window, pdf)
    labels = [action.text() for action in main_window._recent_menu.actions()]
    assert any(pdf.name in label for label in labels)


def test_render_cache_respects_memory_budget(qtbot, main_window, make_pdf) -> None:
    from src.constants import MAX_RENDER_CACHE_MB

    pdf = make_pdf(pages=1)
    open_and_wait(qtbot, main_window, pdf)
    # Each distinct zoom caches a full-page pixmap; 400% of A4 alone is ~30 MB.
    for percent in (150, 200, 250, 300, 350, 400):
        act_and_wait(qtbot, main_window.viewer,
                     lambda p=percent: main_window.viewer.set_zoom(p / 100))

    budget = MAX_RENDER_CACHE_MB * 1024 * 1024
    assert main_window.viewer._cache_bytes <= budget
    assert len(main_window.viewer._cache) >= 1


def test_closing_drains_renders(qtbot, main_window, make_pdf) -> None:
    pdf = make_pdf(pages=3)
    open_and_wait(qtbot, main_window, pdf)
    viewer = main_window.viewer  # grab reference before close
    viewer.set_zoom(3.5)  # kick off a render, then close immediately
    main_window.document._modified = False
    main_window.close()
    # After close, all tabs are gone and viewer property returns None.
    # The viewer object itself should have drained its renders.
    assert viewer.wait_for_render(5_000)
    assert viewer.document is None
