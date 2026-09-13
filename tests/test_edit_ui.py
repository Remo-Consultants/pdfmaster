"""Tests for the interactive editing UI: tools, coordinate mapping, controller."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QDialog, QMessageBox

from src.processors.annotations import AnnotationProcessor
from src.processors.content import ContentEditor
from src.ui.dialogs.export_dialog import parse_page_range
from src.ui.tools import CLICK_TOOLS, DRAG_TOOLS, TOOL_HINTS, TOOL_LABELS, ToolMode
from tests.conftest import act_and_wait, open_and_wait


# ----------------------------------------------------------------------
# Tool metadata
# ----------------------------------------------------------------------
def test_every_tool_has_a_label_and_hint() -> None:
    for mode in ToolMode:
        assert TOOL_LABELS[mode]
        assert TOOL_HINTS[mode]


def test_tool_sets_do_not_overlap() -> None:
    assert DRAG_TOOLS.isdisjoint(CLICK_TOOLS)
    assert ToolMode.PAN not in DRAG_TOOLS
    assert ToolMode.PAN not in CLICK_TOOLS


# ----------------------------------------------------------------------
# Page range parsing
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "text,expected",
    [
        ("", [0, 1, 2, 3, 4]),
        ("1", [0]),
        ("1,3", [0, 2]),
        ("2-4", [1, 2, 3]),
        ("1, 3-5", [0, 2, 3, 4]),
        ("3-3", [2]),
        ("99", []),
        ("abc", []),
        ("1-99", [0, 1, 2, 3, 4]),
        ("2,2,2", [1]),
    ],
)
def test_parse_page_range(text: str, expected: list) -> None:
    assert parse_page_range(text, 5) == expected


# ----------------------------------------------------------------------
# Coordinate mapping
# ----------------------------------------------------------------------
def test_widget_to_pdf_maps_through_zoom(qtbot, main_window, make_text_pdf) -> None:
    open_and_wait(qtbot, main_window, make_text_pdf())
    viewer = main_window.viewer
    origin = viewer.page_origin(viewer.current_page)

    point = viewer.widget_to_pdf(QPointF(origin.x() + 100, origin.y() + 200))
    assert point is not None
    assert point[0] == pytest.approx(100 / viewer.zoom_level, abs=0.01)
    assert point[1] == pytest.approx(200 / viewer.zoom_level, abs=0.01)


def test_widget_to_pdf_rejects_points_outside_the_page(
    qtbot, main_window, make_text_pdf
) -> None:
    open_and_wait(qtbot, main_window, make_text_pdf())
    viewer = main_window.viewer
    assert viewer.widget_to_pdf(QPointF(-50, -50)) is None
    assert viewer.widget_to_pdf(QPointF(99_999, 99_999)) is None


def test_widget_to_pdf_without_document(main_window) -> None:
    # With tabs, there's no viewer when no document is open.
    assert main_window.viewer is None


def test_click_lands_on_the_same_word_after_rotation(
    qtbot, main_window, make_text_pdf
) -> None:
    """The whole point of the derotation matrix: clicks must still hit the text."""
    open_and_wait(qtbot, main_window, make_text_pdf())
    viewer = main_window.viewer
    document = main_window.document

    span = ContentEditor.find_spans(document, 0)[0]
    centre_x = (span["bbox"][0] + span["bbox"][2]) / 2
    centre_y = (span["bbox"][1] + span["bbox"][3]) / 2

    for angle in (90, 90, 90, 90):
        act_and_wait(qtbot, viewer, lambda: viewer.rotate_page(angle))
        origin = viewer.page_origin(viewer.current_page)
        rotation = document.get_page_rotation(0)

        # Where that PDF point currently appears on screen.
        import pymupdf as fitz

        with document.transaction(mark_modified=False) as pdf:
            matrix = pdf.load_page(0).rotation_matrix
        screen = fitz.Point(centre_x, centre_y) * matrix
        widget_point = QPointF(
            origin.x() + screen.x * viewer.zoom_level,
            origin.y() + screen.y * viewer.zoom_level,
        )

        mapped = viewer.widget_to_pdf(widget_point)
        assert mapped is not None, f"mapping failed at rotation {rotation}"
        assert mapped[0] == pytest.approx(centre_x, abs=1.0)
        assert mapped[1] == pytest.approx(centre_y, abs=1.0)


# ----------------------------------------------------------------------
# Drag handling
# ----------------------------------------------------------------------
def _drag(viewer, start: QPointF, end: QPointF) -> None:
    viewer.handle_press(start)
    viewer.handle_move(end)
    viewer.handle_release(end)


def test_pan_tool_ignores_drags(qtbot, main_window, make_text_pdf) -> None:
    open_and_wait(qtbot, main_window, make_text_pdf())
    viewer = main_window.viewer
    main_window.set_tool(ToolMode.PAN)
    assert viewer.handle_press(QPointF(50, 50)) is False


def test_drag_emits_area_selected_in_pdf_coordinates(
    qtbot, main_window, make_text_pdf
) -> None:
    open_and_wait(qtbot, main_window, make_text_pdf())
    viewer = main_window.viewer
    main_window.set_tool(ToolMode.HIGHLIGHT)
    origin = viewer.page_origin(viewer.current_page)

    with qtbot.waitSignal(viewer.area_selected, timeout=2000) as caught:
        _drag(
            viewer,
            QPointF(origin.x() + 60, origin.y() + 85),
            QPointF(origin.x() + 300, origin.y() + 110),
        )

    tool, page, rect = caught.args
    assert tool is ToolMode.HIGHLIGHT
    assert page == 0
    assert rect[0] < rect[2] and rect[1] < rect[3]
    assert rect[0] == pytest.approx(60 / viewer.zoom_level, abs=0.5)


def test_tiny_drag_is_ignored(qtbot, main_window, make_text_pdf) -> None:
    open_and_wait(qtbot, main_window, make_text_pdf())
    viewer = main_window.viewer
    main_window.set_tool(ToolMode.HIGHLIGHT)
    origin = viewer.page_origin(viewer.current_page)

    received = []
    viewer.area_selected.connect(lambda *a: received.append(a))
    _drag(viewer, QPointF(origin.x() + 60, origin.y() + 85),
          QPointF(origin.x() + 61, origin.y() + 86))
    assert received == []


def test_click_tool_emits_point(qtbot, main_window, make_text_pdf) -> None:
    open_and_wait(qtbot, main_window, make_text_pdf())
    viewer = main_window.viewer
    main_window.set_tool(ToolMode.NOTE)
    origin = viewer.page_origin(viewer.current_page)

    with qtbot.waitSignal(viewer.point_selected, timeout=2000) as caught:
        viewer.handle_press(QPointF(origin.x() + 120, origin.y() + 140))

    tool, page, point = caught.args
    assert tool is ToolMode.NOTE
    assert page == 0
    assert point[0] == pytest.approx(120 / viewer.zoom_level, abs=0.5)


def test_pen_tool_emits_ink_strokes(qtbot, main_window, make_text_pdf) -> None:
    open_and_wait(qtbot, main_window, make_text_pdf())
    viewer = main_window.viewer
    main_window.set_tool(ToolMode.PEN)
    origin = viewer.page_origin(viewer.current_page)

    with qtbot.waitSignal(viewer.ink_drawn, timeout=2000) as caught:
        viewer.handle_press(QPointF(origin.x() + 50, origin.y() + 50))
        for offset in range(10, 60, 10):
            viewer.handle_move(QPointF(origin.x() + 50 + offset, origin.y() + 50 + offset))
        viewer.handle_release(QPointF(origin.x() + 110, origin.y() + 110))

    page, strokes = caught.args
    assert page == 0
    assert len(strokes) == 1
    assert len(strokes[0]) >= 2


def test_switching_tools_cancels_an_active_drag(qtbot, main_window, make_text_pdf) -> None:
    open_and_wait(qtbot, main_window, make_text_pdf())
    viewer = main_window.viewer
    main_window.set_tool(ToolMode.HIGHLIGHT)
    origin = viewer.page_origin(viewer.current_page)
    viewer.handle_press(QPointF(origin.x() + 100, origin.y() + 100))
    assert viewer._dragging is True

    main_window.set_tool(ToolMode.PAN)
    assert viewer._dragging is False


# ----------------------------------------------------------------------
# Controller: applying edits
# ----------------------------------------------------------------------
def test_highlight_tool_adds_an_annotation(qtbot, main_window, make_text_pdf) -> None:
    open_and_wait(qtbot, main_window, make_text_pdf())
    viewer = main_window.viewer
    main_window.set_tool(ToolMode.HIGHLIGHT)
    origin = viewer.page_origin(viewer.current_page)

    act_and_wait(qtbot, viewer, lambda: _drag(
        viewer,
        QPointF(origin.x() + 60, origin.y() + 85),
        QPointF(origin.x() + 300, origin.y() + 110),
    ))

    annots = AnnotationProcessor.list_annotations(main_window.document, 0)
    assert len(annots) == 1
    assert annots[0]["type"] == "Highlight"
    assert main_window.document.is_modified


def test_highlight_over_blank_space_warns(qtbot, main_window, make_text_pdf, monkeypatch) -> None:
    open_and_wait(qtbot, main_window, make_text_pdf())
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: warnings.append(a)))

    viewer = main_window.viewer
    main_window.set_tool(ToolMode.HIGHLIGHT)
    origin = viewer.page_origin(viewer.current_page)
    _drag(viewer,
          QPointF(origin.x() + 400, origin.y() + 600),
          QPointF(origin.x() + 500, origin.y() + 650))

    assert warnings, "expected a warning when no text is selected"
    assert AnnotationProcessor.list_annotations(main_window.document, 0) == []


def test_sticky_note_uses_the_dialog(qtbot, main_window, make_text_pdf, monkeypatch) -> None:
    open_and_wait(qtbot, main_window, make_text_pdf())
    from src.ui import edit_controller

    monkeypatch.setattr(
        edit_controller.StickyNoteDialog, "exec",
        lambda self: QDialog.DialogCode.Accepted,
    )
    monkeypatch.setattr(
        edit_controller.StickyNoteDialog, "text", lambda self: "review this"
    )

    viewer = main_window.viewer
    main_window.set_tool(ToolMode.NOTE)
    origin = viewer.page_origin(viewer.current_page)
    act_and_wait(qtbot, viewer,
                 lambda: viewer.handle_press(QPointF(origin.x() + 200, origin.y() + 200)))

    annots = AnnotationProcessor.list_annotations(main_window.document, 0)
    assert len(annots) == 1
    assert annots[0]["content"] == "review this"


def test_sticky_note_reopens_existing(qtbot, main_window, make_text_pdf, monkeypatch) -> None:
    open_and_wait(qtbot, main_window, make_text_pdf())
    from src.ui import edit_controller

    AnnotationProcessor.add_sticky_note(main_window.document, 0, (72, 72), "keep me")
    main_window.refresh_after_edit()

    seen: list[str] = []

    def fake_init(self, parent=None, *, text: str = "", editing: bool = False) -> None:
        QDialog.__init__(self, parent)
        self._text = text
        self._editing = editing
        seen.append(text)

    monkeypatch.setattr(edit_controller.StickyNoteDialog, "__init__", fake_init)
    monkeypatch.setattr(
        edit_controller.StickyNoteDialog, "exec",
        lambda self: QDialog.DialogCode.Accepted,
    )
    monkeypatch.setattr(
        edit_controller.StickyNoteDialog, "text", lambda self: "keep me — updated"
    )

    viewer = main_window.viewer
    main_window.set_tool(ToolMode.NOTE)
    # PDF (72,72) mapped roughly — use page_origin + zoomed offset
    origin = viewer.page_origin(viewer.current_page)
    zoom = viewer.zoom_level
    act_and_wait(
        qtbot,
        viewer,
        lambda: viewer.handle_press(
            QPointF(origin.x() + 72 * zoom, origin.y() + 72 * zoom)
        ),
    )

    assert seen and seen[0] == "keep me"
    annots = AnnotationProcessor.list_annotations(main_window.document, 0)
    assert annots[0]["content"] == "keep me — updated"


def test_pen_tool_stores_ink(qtbot, main_window, make_text_pdf) -> None:
    open_and_wait(qtbot, main_window, make_text_pdf())
    viewer = main_window.viewer
    main_window.set_tool(ToolMode.PEN)
    origin = viewer.page_origin(viewer.current_page)

    def draw() -> None:
        viewer.handle_press(QPointF(origin.x() + 50, origin.y() + 400))
        for offset in (10, 20, 30, 40):
            viewer.handle_move(QPointF(origin.x() + 50 + offset, origin.y() + 400 + offset))
        viewer.handle_release(QPointF(origin.x() + 100, origin.y() + 450))

    act_and_wait(qtbot, viewer, draw)
    annots = AnnotationProcessor.list_annotations(main_window.document, 0)
    assert annots and annots[0]["type"] == "Ink"


def test_delete_markup_tool(qtbot, main_window, make_text_pdf) -> None:
    open_and_wait(qtbot, main_window, make_text_pdf())
    document = main_window.document
    AnnotationProcessor.add_shape(document, 0, (100, 400, 300, 500))

    viewer = main_window.viewer
    main_window.set_tool(ToolMode.DELETE_ANNOT)
    origin = viewer.page_origin(viewer.current_page)
    zoom = viewer.zoom_level
    act_and_wait(qtbot, viewer, lambda: viewer.handle_press(
        QPointF(origin.x() + 200 * zoom, origin.y() + 450 * zoom)
    ))

    assert AnnotationProcessor.list_annotations(document, 0) == []


def test_edit_text_tool_replaces_text(qtbot, main_window, make_text_pdf, monkeypatch) -> None:
    open_and_wait(qtbot, main_window, make_text_pdf())
    from src.ui import edit_controller

    monkeypatch.setattr(
        edit_controller.ReplaceTextDialog, "exec",
        lambda self: QDialog.DialogCode.Accepted,
    )
    monkeypatch.setattr(
        edit_controller.ReplaceTextDialog, "result_values",
        lambda self: {"text": "Invoice Date: 2030-05-05", "font": None,
                      "size": None, "color": None},
    )
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))

    document = main_window.document
    span = ContentEditor.find_spans(document, 0)[0]
    viewer = main_window.viewer
    main_window.set_tool(ToolMode.EDIT_TEXT)
    origin = viewer.page_origin(viewer.current_page)
    zoom = viewer.zoom_level
    x0, y0, x1, y1 = span["bbox"]

    act_and_wait(qtbot, viewer, lambda: _drag(
        viewer,
        QPointF(origin.x() + x0 * zoom, origin.y() + y0 * zoom),
        QPointF(origin.x() + x1 * zoom, origin.y() + y1 * zoom),
    ))

    text = document.get_page_text(0)
    assert "2030-05-05" in text
    assert "2024-01-01" not in text


def test_redact_tool_asks_for_confirmation(
    qtbot, main_window, make_text_pdf, monkeypatch
) -> None:
    open_and_wait(qtbot, main_window, make_text_pdf())
    monkeypatch.setattr(
        QMessageBox, "warning",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Cancel),
    )

    document = main_window.document
    span = next(s for s in ContentEditor.find_spans(document, 0)
                if s["text"].startswith("SECRET"))
    viewer = main_window.viewer
    main_window.set_tool(ToolMode.REDACT)
    origin = viewer.page_origin(viewer.current_page)
    zoom = viewer.zoom_level
    x0, y0, x1, y1 = span["bbox"]
    _drag(viewer,
          QPointF(origin.x() + x0 * zoom, origin.y() + y0 * zoom),
          QPointF(origin.x() + x1 * zoom, origin.y() + y1 * zoom))

    assert "SECRET" in document.get_page_text(0), "cancelling must not redact"


def test_redact_tool_removes_content_when_confirmed(
    qtbot, main_window, make_text_pdf, monkeypatch
) -> None:
    open_and_wait(qtbot, main_window, make_text_pdf())
    monkeypatch.setattr(
        QMessageBox, "warning",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
    )

    document = main_window.document
    span = next(s for s in ContentEditor.find_spans(document, 0)
                if s["text"].startswith("SECRET"))
    viewer = main_window.viewer
    main_window.set_tool(ToolMode.REDACT)
    origin = viewer.page_origin(viewer.current_page)
    zoom = viewer.zoom_level
    x0, y0, x1, y1 = span["bbox"]

    act_and_wait(qtbot, viewer, lambda: _drag(
        viewer,
        QPointF(origin.x() + x0 * zoom, origin.y() + y0 * zoom),
        QPointF(origin.x() + x1 * zoom, origin.y() + y1 * zoom),
    ))

    assert "SECRET" not in document.get_page_text(0)


# ----------------------------------------------------------------------
# Undo / redo through the window
# ----------------------------------------------------------------------
def test_undo_actions_start_disabled(main_window) -> None:
    assert main_window.undo_action.isEnabled() is False
    assert main_window.redo_action.isEnabled() is False


def test_undo_reverses_a_highlight(qtbot, main_window, make_text_pdf) -> None:
    open_and_wait(qtbot, main_window, make_text_pdf())
    viewer = main_window.viewer
    main_window.set_tool(ToolMode.HIGHLIGHT)
    origin = viewer.page_origin(viewer.current_page)

    act_and_wait(qtbot, viewer, lambda: _drag(
        viewer,
        QPointF(origin.x() + 60, origin.y() + 85),
        QPointF(origin.x() + 300, origin.y() + 110),
    ))
    assert main_window.undo_action.isEnabled() is True

    act_and_wait(qtbot, viewer, lambda: main_window.editor.undo())
    assert AnnotationProcessor.list_annotations(main_window.document, 0) == []
    assert main_window.redo_action.isEnabled() is True

    act_and_wait(qtbot, viewer, lambda: main_window.editor.redo())
    assert len(AnnotationProcessor.list_annotations(main_window.document, 0)) == 1


def test_undo_history_resets_on_new_document(qtbot, main_window, make_text_pdf) -> None:
    open_and_wait(qtbot, main_window, make_text_pdf("first.pdf"))
    viewer = main_window.viewer
    main_window.set_tool(ToolMode.HIGHLIGHT)
    origin = viewer.page_origin(viewer.current_page)
    act_and_wait(qtbot, viewer, lambda: _drag(
        viewer,
        QPointF(origin.x() + 60, origin.y() + 85),
        QPointF(origin.x() + 300, origin.y() + 110),
    ))
    assert main_window.editor.history.can_undo is True

    main_window.document._modified = False
    open_and_wait(qtbot, main_window, make_text_pdf("second.pdf"))
    assert main_window.editor.history.can_undo is False
    assert main_window.undo_action.isEnabled() is False


def test_undo_restores_deleted_pages(qtbot, main_window, make_pdf, monkeypatch) -> None:
    open_and_wait(qtbot, main_window, make_pdf(pages=4))
    from src.processors.page_ops import PageOrganizer

    main_window.editor._begin_edit()
    PageOrganizer.delete_pages(main_window.document, [0, 1])
    act_and_wait(qtbot, main_window.viewer, main_window.refresh_after_edit)
    assert main_window.document.page_count == 2

    act_and_wait(qtbot, main_window.viewer, lambda: main_window.editor.undo())
    assert main_window.document.page_count == 4


def test_refresh_clamps_current_page(qtbot, main_window, make_pdf) -> None:
    open_and_wait(qtbot, main_window, make_pdf(pages=4))
    act_and_wait(qtbot, main_window.viewer, lambda: main_window.viewer.go_to_page(3))

    from src.processors.page_ops import PageOrganizer

    PageOrganizer.delete_pages(main_window.document, [2, 3])
    act_and_wait(qtbot, main_window.viewer, main_window.refresh_after_edit)
    assert main_window.viewer.current_page == 1


# ----------------------------------------------------------------------
# Menu-driven actions
# ----------------------------------------------------------------------
def test_editing_actions_disabled_without_document(main_window) -> None:
    for action in (
        main_window.print_action,
        main_window.print_preview_action,
        main_window.export_images_action,
        main_window.organize_action,
        main_window.form_action,
        main_window.find_replace_action,
        main_window.flatten_action,
    ):
        assert action.isEnabled() is False


def test_editing_actions_enabled_after_open(qtbot, main_window, make_text_pdf) -> None:
    open_and_wait(qtbot, main_window, make_text_pdf())
    for action in (
        main_window.print_action,
        main_window.export_images_action,
        main_window.organize_action,
        main_window.form_action,
    ):
        assert action.isEnabled() is True


def test_fill_form_on_plain_pdf_informs_user(
    qtbot, main_window, make_pdf, monkeypatch
) -> None:
    open_and_wait(qtbot, main_window, make_pdf(pages=1))
    messages = []
    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda *a, **k: messages.append(a)))
    main_window.editor.fill_form()
    assert messages, "expected an explanation that there is no form"


def test_fill_form_saves_values(qtbot, main_window, make_form_pdf, monkeypatch) -> None:
    open_and_wait(qtbot, main_window, make_form_pdf())
    from src.processors.forms import FormProcessor
    from src.ui import edit_controller

    monkeypatch.setattr(
        edit_controller.FormDialog, "exec",
        lambda self: (
            setattr(self, "updated_count",
                    FormProcessor.set_values(self._document, {"customer": "Dinesh"})),
            QDialog.DialogCode.Accepted,
        )[1],
    )
    act_and_wait(qtbot, main_window.viewer, lambda: main_window.editor.fill_form())
    assert FormProcessor.get_values(main_window.document)["customer"] == "Dinesh"


def test_find_and_replace(qtbot, main_window, make_text_pdf, monkeypatch) -> None:
    pdf = make_text_pdf(lines=["alpha one", "alpha two"])
    open_and_wait(qtbot, main_window, pdf)
    from src.ui import edit_controller

    monkeypatch.setattr(
        edit_controller.FindReplaceDialog, "exec",
        lambda self: QDialog.DialogCode.Accepted,
    )
    monkeypatch.setattr(
        edit_controller.FindReplaceDialog, "result_values",
        lambda self: {"search": "alpha", "replacement": "OMEGA", "all_pages": True},
    )

    act_and_wait(qtbot, main_window.viewer,
                 lambda: main_window.editor.find_and_replace())
    text = main_window.document.get_page_text(0)
    assert "alpha" not in text
    assert text.count("OMEGA") == 2


def test_export_images_from_controller(
    qtbot, main_window, make_pdf, tmp_path, monkeypatch
) -> None:
    open_and_wait(qtbot, main_window, make_pdf(pages=2))
    from src.ui import edit_controller

    target = tmp_path / "shots"
    monkeypatch.setattr(
        edit_controller.ExportImagesDialog, "exec",
        lambda self: QDialog.DialogCode.Accepted,
    )
    monkeypatch.setattr(
        edit_controller.ExportImagesDialog, "result_values",
        lambda self: {"folder": target, "format": "PNG", "dpi": 72, "pages": [0, 1]},
    )

    main_window.editor.export_images()
    assert len(list(target.glob("*.png"))) == 2


def test_clear_page_markup(qtbot, main_window, make_text_pdf) -> None:
    open_and_wait(qtbot, main_window, make_text_pdf())
    document = main_window.document
    AnnotationProcessor.add_sticky_note(document, 0, (100, 100), "one")
    AnnotationProcessor.add_sticky_note(document, 0, (200, 200), "two")

    act_and_wait(qtbot, main_window.viewer,
                 lambda: main_window.editor.clear_page_markup())
    assert AnnotationProcessor.list_annotations(document, 0) == []


def test_flatten_document(qtbot, main_window, make_text_pdf, monkeypatch) -> None:
    open_and_wait(qtbot, main_window, make_text_pdf())
    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
    )
    document = main_window.document
    AnnotationProcessor.add_markup(document, 0, (60, 85, 400, 105))

    act_and_wait(qtbot, main_window.viewer,
                 lambda: main_window.editor.flatten_document())
    assert AnnotationProcessor.list_annotations(document, 0) == []


def test_print_without_printer_warns(qtbot, main_window, make_pdf, monkeypatch) -> None:
    open_and_wait(qtbot, main_window, make_pdf(pages=1))
    from src.services.print_service import PrintService

    monkeypatch.setattr(PrintService, "has_printer", staticmethod(lambda: False))
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: warnings.append(a)))

    main_window.editor.print_document()
    assert warnings, "expected a warning when no printer exists"


# ----------------------------------------------------------------------
# Page organiser dialog
# ----------------------------------------------------------------------
def _organizer(qtbot, main_window):
    from src.ui.dialogs.page_organizer import PageOrganizerDialog

    dialog = PageOrganizerDialog(
        main_window.document, main_window.editor._begin_edit, main_window
    )
    qtbot.addWidget(dialog)
    return dialog


def test_organizer_lists_every_page(qtbot, main_window, make_pdf) -> None:
    open_and_wait(qtbot, main_window, make_pdf(pages=4))
    dialog = _organizer(qtbot, main_window)
    assert dialog._list.count() == 4
    assert "Page 1" in dialog._list.item(0).text()


def test_organizer_move_down_reorders(qtbot, main_window, make_pdf) -> None:
    open_and_wait(qtbot, main_window, make_pdf(pages=3))
    dialog = _organizer(qtbot, main_window)
    dialog._list.setCurrentRow(0)
    dialog.move_down()

    document = main_window.document
    assert document.get_page_text(0).strip() == "Page 2"
    assert document.get_page_text(1).strip() == "Page 1"
    assert dialog._list.currentRow() == 1


def test_organizer_move_down_onto_the_last_page(qtbot, main_window, make_pdf) -> None:
    """Move Down from the second-to-last row lands on the final slot."""
    open_and_wait(qtbot, main_window, make_pdf(pages=3))
    dialog = _organizer(qtbot, main_window)
    dialog._list.setCurrentRow(1)
    dialog.move_down()

    document = main_window.document
    labels = [document.get_page_text(i).strip() for i in range(3)]
    assert labels == ["Page 1", "Page 3", "Page 2"]


def test_organizer_move_down_at_bottom_is_a_noop(qtbot, main_window, make_pdf) -> None:
    open_and_wait(qtbot, main_window, make_pdf(pages=3))
    dialog = _organizer(qtbot, main_window)
    dialog._list.setCurrentRow(2)
    dialog.move_down()
    assert main_window.document.get_page_text(2).strip() == "Page 3"


def test_organizer_duplicate_last_page(qtbot, main_window, make_pdf) -> None:
    open_and_wait(qtbot, main_window, make_pdf(pages=2))
    dialog = _organizer(qtbot, main_window)
    dialog._list.setCurrentRow(1)
    dialog.duplicate()

    document = main_window.document
    assert document.page_count == 3
    assert document.get_page_text(2).strip() == "Page 2"


def test_organizer_walk_a_page_to_the_bottom(qtbot, main_window, make_pdf) -> None:
    """Repeated Move Down must work all the way to the end."""
    open_and_wait(qtbot, main_window, make_pdf(pages=4))
    dialog = _organizer(qtbot, main_window)
    dialog._list.setCurrentRow(0)
    for _ in range(3):
        dialog.move_down()

    document = main_window.document
    labels = [document.get_page_text(i).strip() for i in range(4)]
    assert labels == ["Page 2", "Page 3", "Page 4", "Page 1"]


def test_organizer_move_up_at_top_is_a_noop(qtbot, main_window, make_pdf) -> None:
    open_and_wait(qtbot, main_window, make_pdf(pages=3))
    dialog = _organizer(qtbot, main_window)
    dialog._list.setCurrentRow(0)
    dialog.move_up()
    assert main_window.document.get_page_text(0).strip() == "Page 1"


def test_organizer_duplicate_and_insert(qtbot, main_window, make_pdf) -> None:
    open_and_wait(qtbot, main_window, make_pdf(pages=2))
    dialog = _organizer(qtbot, main_window)
    dialog._list.setCurrentRow(0)

    dialog.duplicate()
    assert main_window.document.page_count == 3
    assert dialog._list.count() == 3

    dialog.insert_blank()
    assert main_window.document.page_count == 4


def test_organizer_rotate(qtbot, main_window, make_pdf) -> None:
    open_and_wait(qtbot, main_window, make_pdf(pages=2))
    dialog = _organizer(qtbot, main_window)
    dialog._list.setCurrentRow(1)
    dialog.rotate(90)
    assert main_window.document.get_page_rotation(1) == 90
    assert "90deg" in dialog._list.item(1).text()


def test_organizer_delete_respects_confirmation(
    qtbot, main_window, make_pdf, monkeypatch
) -> None:
    open_and_wait(qtbot, main_window, make_pdf(pages=3))
    dialog = _organizer(qtbot, main_window)
    dialog._list.setCurrentRow(0)

    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No))
    dialog.delete_selected()
    assert main_window.document.page_count == 3

    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    dialog.delete_selected()
    assert main_window.document.page_count == 2


def test_organizer_refuses_to_delete_the_last_page(
    qtbot, main_window, make_pdf, monkeypatch
) -> None:
    open_and_wait(qtbot, main_window, make_pdf(pages=1))
    dialog = _organizer(qtbot, main_window)
    dialog._list.setCurrentRow(0)
    messages = []
    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda *a, **k: messages.append(a)))
    dialog.delete_selected()
    assert main_window.document.page_count == 1
    assert messages


def test_organizer_import_pages(qtbot, main_window, make_pdf, monkeypatch) -> None:
    open_and_wait(qtbot, main_window, make_pdf(name="base.pdf", pages=2))
    extra = make_pdf(name="extra.pdf", pages=3)
    dialog = _organizer(qtbot, main_window)
    dialog._list.setCurrentRow(0)

    from PySide6.QtWidgets import QFileDialog

    monkeypatch.setattr(QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: (str(extra), "")))
    dialog.import_pdf()
    assert main_window.document.page_count == 5


def test_organizer_changes_are_undoable(qtbot, main_window, make_pdf) -> None:
    open_and_wait(qtbot, main_window, make_pdf(pages=3))
    dialog = _organizer(qtbot, main_window)
    dialog._list.setCurrentRow(0)
    dialog.duplicate()
    assert main_window.document.page_count == 4

    act_and_wait(qtbot, main_window.viewer, lambda: main_window.editor.undo())
    assert main_window.document.page_count == 3


def test_edits_are_ignored_without_a_document(main_window) -> None:
    """Tool signals must be harmless before anything is open."""
    main_window.editor.handle_area(ToolMode.HIGHLIGHT, 0, (0, 0, 10, 10))
    main_window.editor.handle_point(ToolMode.NOTE, 0, (5, 5))
    main_window.editor.handle_ink(0, [[(0, 0), (5, 5)]])
    main_window.editor.undo()
    main_window.editor.redo()
