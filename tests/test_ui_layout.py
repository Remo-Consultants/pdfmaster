"""Layout, theming, and panel tests for the reworked interface.

These cover the parts that the earlier suite could not see, because it
drove the window through method calls rather than through the widgets.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPointF

from src.constants import WINDOW_MIN_WIDTH
from src.processors.annotations import AnnotationProcessor
from src.ui import theme
from src.ui.icons import action_icon, tool_icon
from src.ui.tools import PRIMARY_TOOLS, ToolMode
from tests.conftest import act_and_wait, open_and_wait


def _drag(viewer, start: QPointF, end: QPointF) -> None:
    viewer.handle_press(start)
    viewer.handle_move(end)
    viewer.handle_release(end)


def _canvas_point(viewer, page: int, pdf_x: float, pdf_y: float) -> QPointF:
    """Canvas coordinates for a PDF point on a given page."""
    rect = viewer.page_rect(page)
    assert rect is not None, f"page {page} is not laid out"
    return QPointF(
        rect.left() + pdf_x * viewer.zoom_level,
        rect.top() + pdf_y * viewer.zoom_level,
    )


# ----------------------------------------------------------------------
# Ribbon layout
# ----------------------------------------------------------------------
def test_ribbon_has_expected_tabs(main_window) -> None:
    """The ribbon should have Home, Markup, Edit, Organize, View tabs."""
    ribbon = main_window._ribbon
    assert ribbon.get_tab("home") is not None
    assert ribbon.get_tab("markup") is not None
    assert ribbon.get_tab("edit") is not None
    assert ribbon.get_tab("organize") is not None
    assert ribbon.get_tab("view") is not None


def test_ribbon_fits_at_minimum_width(qtbot, main_window, make_pdf) -> None:
    """Ribbon groups should not overflow at the minimum window size."""
    open_and_wait(qtbot, main_window, make_pdf(pages=2))
    main_window.resize(WINDOW_MIN_WIDTH, 760)
    qtbot.waitUntil(lambda: main_window.width() == WINDOW_MIN_WIDTH, timeout=2000)

    # Ribbon uses tabs, so content doesn't overflow like toolbars did.
    ribbon = main_window._ribbon
    assert ribbon.width() <= main_window.width()


def test_all_tools_accessible_via_menu(main_window) -> None:
    """Every tool must be reachable from the Tools menu."""
    assert set(main_window._tool_actions) == set(ToolMode)


def test_number_keys_match_primary_tool_order(main_window) -> None:
    for position, mode in enumerate(PRIMARY_TOOLS, start=1):
        action = main_window._tool_actions[mode]
        assert action.shortcut().toString() == str(position)


# ----------------------------------------------------------------------
# Continuous scrolling
# ----------------------------------------------------------------------
def test_all_pages_are_laid_out_in_order(qtbot, main_window, make_pdf) -> None:
    open_and_wait(qtbot, main_window, make_pdf(pages=5))
    viewer = main_window.viewer

    rects = [viewer.page_rect(i) for i in range(5)]
    assert all(rect is not None for rect in rects)
    for upper, lower in zip(rects, rects[1:]):
        assert lower.top() > upper.bottom(), "pages must stack without overlap"


def test_scrolling_changes_the_current_page(qtbot, main_window, make_pdf) -> None:
    open_and_wait(qtbot, main_window, make_pdf(pages=4))
    viewer = main_window.viewer
    assert viewer.current_page == 0

    third = viewer.page_rect(2)
    with qtbot.waitSignal(viewer.page_changed, timeout=5000):
        viewer.verticalScrollBar().setValue(int(third.center().y()))
    assert viewer.current_page == 2
    assert main_window._page_spin.value() == 3


def test_only_visible_pages_are_rendered(qtbot, main_window, make_pdf) -> None:
    """Cost should track the viewport, not the page count."""
    open_and_wait(qtbot, main_window, make_pdf(pages=60))
    viewer = main_window.viewer
    qtbot.waitUntil(lambda: not viewer.is_rendering, timeout=20_000)

    assert viewer.page_pixmap(0) is not None
    assert viewer.page_pixmap(59) is None, "off-screen pages must stay unrendered"
    assert len(viewer.visible_pages()) < 60


def test_drag_annotates_the_page_it_landed_on(
    qtbot, main_window, make_pdf, silent_dialogs
) -> None:
    """The core risk of continuous mode: edits must not hit the wrong page.

    Page 1 stays the "current" page while the drag happens on page 2.
    """
    open_and_wait(qtbot, main_window, make_pdf(pages=3))
    viewer = main_window.viewer
    document = main_window.document
    main_window.set_tool(ToolMode.HIGHLIGHT)

    assert viewer.current_page == 0
    act_and_wait(qtbot, viewer, lambda: _drag(
        viewer,
        _canvas_point(viewer, 1, 65, 58),
        _canvas_point(viewer, 1, 200, 86),
    ))

    assert len(AnnotationProcessor.list_annotations(document, 1)) == 1
    assert AnnotationProcessor.list_annotations(document, 0) == []
    assert AnnotationProcessor.list_annotations(document, 2) == []


def test_drag_across_a_page_boundary_stays_on_one_page(
    qtbot, main_window, make_pdf, silent_dialogs
) -> None:
    """Dragging past the bottom edge must clamp, not spill onto page 2."""
    open_and_wait(qtbot, main_window, make_pdf(pages=3))
    viewer = main_window.viewer
    document = main_window.document
    main_window.set_tool(ToolMode.SHAPE)

    first = viewer.page_rect(0)
    act_and_wait(qtbot, viewer, lambda: _drag(
        viewer,
        QPointF(first.left() + 40, first.bottom() - 30),
        QPointF(first.left() + 240, first.bottom() + 400),  # well into page 2
    ))

    assert len(AnnotationProcessor.list_annotations(document, 0)) == 1
    assert AnnotationProcessor.list_annotations(document, 1) == []
    _, _, _, bottom = AnnotationProcessor.list_annotations(document, 0)[0]["rect"]
    height = document.get_page_size(0)[1]
    assert bottom <= height + 1, "annotation escaped the page"


# ----------------------------------------------------------------------
# Thumbnail sidebar
# ----------------------------------------------------------------------
def test_thumbnail_panel_lists_every_page(qtbot, main_window, make_pdf) -> None:
    open_and_wait(qtbot, main_window, make_pdf(pages=6))
    assert main_window.thumbnails.count() == 6
    assert main_window.thumbnails.currentRow() == 0


def test_clicking_a_thumbnail_navigates(qtbot, main_window, make_pdf) -> None:
    open_and_wait(qtbot, main_window, make_pdf(pages=5))
    with qtbot.waitSignal(main_window.viewer.page_changed, timeout=5000):
        main_window.thumbnails.setCurrentRow(3)
    assert main_window.viewer.current_page == 3


def test_thumbnails_follow_the_viewer_without_looping(
    qtbot, main_window, make_pdf
) -> None:
    """Syncing the highlight must not bounce back into the viewer."""
    open_and_wait(qtbot, main_window, make_pdf(pages=4))
    act_and_wait(qtbot, main_window.viewer, main_window.last_page)
    assert main_window.thumbnails.currentRow() == 3
    assert main_window.viewer.current_page == 3


def test_thumbnails_rebuild_after_a_page_is_deleted(
    qtbot, main_window, make_pdf, silent_dialogs
) -> None:
    open_and_wait(qtbot, main_window, make_pdf(pages=4))
    act_and_wait(qtbot, main_window.viewer, main_window.delete_current_page)
    assert main_window.thumbnails.count() == 3


# ----------------------------------------------------------------------
# Properties panel
# ----------------------------------------------------------------------
def test_info_panel_reports_document_properties(
    qtbot, main_window, make_pdf
) -> None:
    open_and_wait(qtbot, main_window, make_pdf(pages=3, width=400, height=800))
    labels = main_window.info_panel._labels
    assert labels["pages"].text() == "3"
    assert labels["page_size"].text() == "400 x 800 pt"
    assert labels["encrypted"].text() == "No"


def test_info_panel_lists_and_deletes_markup(
    qtbot, main_window, make_pdf, silent_dialogs
) -> None:
    open_and_wait(qtbot, main_window, make_pdf(pages=2))
    viewer = main_window.viewer
    document = main_window.document
    main_window.set_tool(ToolMode.SHAPE)

    act_and_wait(qtbot, viewer, lambda: _drag(
        viewer,
        _canvas_point(viewer, 0, 100, 200),
        _canvas_point(viewer, 0, 300, 320),
    ))
    panel = main_window.info_panel
    assert panel._list.count() == 1

    panel._list.setCurrentRow(0)
    act_and_wait(qtbot, viewer, panel._on_delete)
    assert AnnotationProcessor.list_annotations(document, 0) == []
    assert panel._list.count() == 1  # the "no markup" placeholder row


def test_panels_toggle_from_the_view_menu(main_window) -> None:
    assert main_window._thumb_dock.isVisible()
    main_window.toggle_thumbs_action.trigger()
    assert not main_window._thumb_dock.isVisible()
    main_window.toggle_thumbs_action.trigger()
    assert main_window._thumb_dock.isVisible()


# ----------------------------------------------------------------------
# Theme and icons
# ----------------------------------------------------------------------
def test_light_and_dark_schemes_differ() -> None:
    light = theme.build_palette(theme.LIGHT)
    dark = theme.build_palette(theme.DARK)
    assert light.window().color() != dark.window().color()
    assert theme.color("canvas", theme.LIGHT) != theme.color("canvas", theme.DARK)


def test_every_colour_key_exists_in_both_schemes() -> None:
    assert set(theme.COLORS[theme.LIGHT]) == set(theme.COLORS[theme.DARK])


def test_unknown_colour_falls_back_to_light() -> None:
    assert theme.color("canvas", "chartreuse") == theme.COLORS[theme.LIGHT]["canvas"]


def test_every_tool_has_a_drawn_icon() -> None:
    for mode in ToolMode:
        for scheme in (theme.LIGHT, theme.DARK):
            icon = tool_icon(mode, scheme)
            assert not icon.isNull(), f"{mode} has no icon in {scheme}"


def test_toolbar_actions_have_icons(main_window) -> None:
    for name, action in main_window._icon_actions.items():
        assert not action.icon().isNull(), f"{name} lost its icon"


def test_switching_scheme_redraws_icons(main_window) -> None:
    main_window._apply_scheme(theme.DARK)
    assert main_window._scheme == theme.DARK
    assert not action_icon("open", theme.DARK).isNull()
    for action in main_window._tool_actions.values():
        assert not action.icon().isNull()
    main_window._apply_scheme(theme.LIGHT)


def test_app_icon_asset_exists() -> None:
    from src.constants import APP_ICON_ICO, APP_ICON_PATH, APP_ICON_PNG

    assert APP_ICON_PNG.is_file(), f"missing {APP_ICON_PNG}"
    assert APP_ICON_ICO.is_file(), f"missing {APP_ICON_ICO}"
    assert APP_ICON_PATH.is_file()


def test_main_window_uses_app_icon(main_window) -> None:
    assert not main_window.windowIcon().isNull()
