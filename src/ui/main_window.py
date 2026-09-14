"""Main application window: menus, toolbar, shortcuts, and viewer."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QCloseEvent,
    QGuiApplication,
    QIcon,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDockWidget,
    QFileDialog,
    QLabel,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from src.constants import (
    APP_AUTHOR,
    APP_DESCRIPTION,
    APP_ICON_PATH,
    APP_LICENSE,
    APP_NAME,
    APP_VERSION,
    CONFIG_DIR,
    MAX_RECENT_FILES,
    MSG_ENCRYPTED_PDF,
    MSG_FILE_NOT_FOUND,
    MSG_INVALID_PDF,
    MSG_LAST_PAGE,
    MSG_LOAD_ERROR,
    MSG_NO_DOCUMENT,
    MSG_OPEN_SUCCESS,
    MSG_PAGE_DELETED,
    MSG_PAGE_ROTATED,
    MSG_REPAIRED_PDF,
    MSG_SAVE_ERROR,
    MSG_SAVE_SUCCESS,
    PDF_FILTER,
    SHORTCUTS,
    WINDOW_HEIGHT,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_WIDTH,
    ZOOM_DEFAULT,
    ZOOM_MAX,
    ZOOM_MIN,
    ZOOM_STEP,
)
from src.constants import ANNOT_COLORS
from src.core.document import Document
from src.core.history import DocumentHistory
from src.core.pdf_handler import PDFHandler
from src.ui.edit_controller import EditController
from src.ui.dialogs.batch_dialog import BatchDialog
from src.ui.dialogs.compare_dialog import CompareDialog, PdfaDialog
from src.ui.dialogs.ocr_dialog import OCRDialog
from src.ui.dialogs.search_dialog import SearchDialog
from src.ui.dialogs.security_dialog import (
    PasswordPromptDialog,
    SecurityInfoDialog,
    SetPasswordDialog,
)
from src.ui.icons import action_icon, clear_cache, swatch_icon, tool_icon
from src.ui.theme import apply_theme, detect_scheme
from src.ui.tools import PRIMARY_TOOLS, TOOL_HINTS, TOOL_LABELS, ToolMode
from src.ui.widgets.bookmarks_panel import BookmarksPanel
from src.ui.widgets.document_tabs import DocumentTab, DocumentTabs
from src.ui.widgets.document_viewer import DocumentViewer
from src.ui.widgets.info_panel import InfoPanel
from src.ui.widgets.ribbon import Ribbon
from src.ui.widgets.text_extract_panel import TextExtractPanel
from src.ui.widgets.thumbnail_panel import ThumbnailPanel
from src.ui.widgets.welcome_home import WelcomeHome
from src.services.security_service import SecurityService
from src.utils.exceptions import (
    FileOperationError,
    PageOperationError,
    PDFLoadError,
    PDFMasterException,
    ValidationError,
)
from src.utils.file_handler import FileHandler
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """Top-level window that hosts the document viewer and all controls."""

    def __init__(self) -> None:
        super().__init__()
        self._updating_ui = False

        self.setWindowTitle(self._format_window_title())
        if APP_ICON_PATH.is_file():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.setDockOptions(
            QMainWindow.DockOption.AnimatedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
        )

        self._scheme = detect_scheme()

        # Central widget: ribbon + (welcome | document tabs).
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        self._ribbon = Ribbon(self)
        central_layout.addWidget(self._ribbon)

        self._workspace = QStackedWidget(self)
        self._welcome = WelcomeHome(self._scheme, self)
        self._welcome.open_requested.connect(self.open_file)
        self._welcome.path_requested.connect(self.open_file)
        self._tabs = DocumentTabs(self._scheme, self)
        self._tabs.setObjectName("documentTabs")
        self._workspace.addWidget(self._welcome)
        self._workspace.addWidget(self._tabs)
        self._workspace.setCurrentWidget(self._welcome)
        central_layout.addWidget(self._workspace, 1)
        self.setCentralWidget(central)

        self._tabs.active_tab_changed.connect(self._on_tab_changed)
        self._tabs.tab_count_changed.connect(self._on_tab_count_changed)
        self._docks_auto_shown = False

        self.editor = EditController(self)

        self._page_spin: Optional[QSpinBox] = None
        self._page_count_label: Optional[QLabel] = None
        self._zoom_slider: Optional[QSlider] = None
        self._zoom_label: Optional[QLabel] = None
        self._recent_menu = None
        self._tool_actions: dict = {}
        # Action name -> QAction, so icons can be redrawn when the theme flips.
        self._icon_actions: dict = {}

        self.create_menu_bar()
        self.create_ribbon()
        self.create_docks()
        self.create_status_bar()
        self._apply_scheme(self._scheme)
        self._watch_system_theme()
        self._set_document_actions_enabled(False)
        self._reload_recent_menu()
        self.update_history_actions()
        self._ribbon.set_compact(True)
        self._sync_empty_workspace()
        self.statusBar().showMessage(
            f"Use the Review tab for Compare, PDF/A, Search, and Batch — {APP_NAME} {APP_VERSION}",
            12000,
        )
        logger.info("Main window created")

    def _format_window_title(self, document_name: str = "") -> str:
        """Window title always includes the app version so builds are easy to verify."""
        base = f"{APP_NAME} {APP_VERSION}"
        return f"{document_name} — {base}" if document_name else base

    def _assign_action_icon(self, icon_name: str, action: QAction) -> None:
        action.setIcon(action_icon(icon_name, self._scheme))
        self._icon_actions[icon_name] = action

    # ------------------------------------------------------------------
    # Theming
    # ------------------------------------------------------------------
    def _watch_system_theme(self) -> None:
        """Follow Windows when the user flips between light and dark."""
        hints = QGuiApplication.styleHints()
        signal = getattr(hints, "colorSchemeChanged", None)
        if signal is None:  # Qt older than 6.5
            return
        try:
            signal.connect(lambda _scheme=None: self._apply_scheme(detect_scheme()))
        except Exception as exc:  # noqa: BLE001 - theming must not break startup
            logger.debug("Could not subscribe to colour scheme changes: %s", exc)

    def _apply_scheme(self, scheme: str) -> None:
        """Repaint the whole window for a light or dark colour scheme."""
        self._scheme = scheme
        app = QGuiApplication.instance()
        if app is not None:
            apply_theme(app, scheme)
        clear_cache()
        self._tabs.apply_scheme(scheme)
        self._ribbon.apply_scheme(scheme)
        self._welcome.apply_scheme(scheme)
        self._retheme_icons()

    def _retheme_icons(self) -> None:
        """Redraw every icon in the new scheme's ink colour."""
        for name, action in self._icon_actions.items():
            action.setIcon(action_icon(name, self._scheme))
        for mode, action in self._tool_actions.items():
            action.setIcon(tool_icon(mode, self._scheme))

    @property
    def document(self) -> Optional[Document]:
        """The current tab's document, or None. Used by the edit controller."""
        return self._tabs.current_document

    @property
    def viewer(self) -> Optional[DocumentViewer]:
        """The current tab's viewer, or None."""
        return self._tabs.current_viewer

    @property
    def history(self) -> Optional[DocumentHistory]:
        """The current tab's history, or None."""
        return self._tabs.current_history

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def create_menu_bar(self) -> None:
        """Build File, Edit, View, and Help menus."""
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        self.open_action = QAction("&Open...", self)
        self.open_action.setShortcut(QKeySequence(SHORTCUTS["open"]))
        self.open_action.setStatusTip("Open a PDF file")
        self.open_action.triggered.connect(self.open_file)
        file_menu.addAction(self.open_action)

        self.save_action = QAction("&Save", self)
        self.save_action.setShortcut(QKeySequence(SHORTCUTS["save"]))
        self.save_action.setStatusTip("Save the current PDF")
        self.save_action.triggered.connect(self.save_file)
        file_menu.addAction(self.save_action)

        self.save_as_action = QAction("Save &As...", self)
        self.save_as_action.setStatusTip("Save the PDF to a new file")
        self.save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(self.save_as_action)

        file_menu.addSeparator()
        self.print_action = QAction("&Print...", self)
        self.print_action.setShortcut(QKeySequence(SHORTCUTS["print"]))
        self.print_action.setStatusTip("Print the document")
        self.print_action.triggered.connect(lambda: self.editor.print_document())
        file_menu.addAction(self.print_action)

        self.print_preview_action = QAction("Print Pre&view...", self)
        self.print_preview_action.setShortcut(QKeySequence(SHORTCUTS["print_preview"]))
        self.print_preview_action.setStatusTip("Preview the document before printing")
        self.print_preview_action.triggered.connect(lambda: self.editor.print_preview())
        file_menu.addAction(self.print_preview_action)

        self.export_images_action = QAction("&Export Pages as Images...", self)
        self.export_images_action.setShortcut(QKeySequence(SHORTCUTS["export_images"]))
        self.export_images_action.setStatusTip("Save pages as PNG or JPEG files")
        self.export_images_action.triggered.connect(lambda: self.editor.export_images())
        file_menu.addAction(self.export_images_action)

        file_menu.addSeparator()
        self._recent_menu = file_menu.addMenu("Open &Recent")
        file_menu.addSeparator()

        self.exit_action = QAction("E&xit", self)
        self.exit_action.setShortcut(QKeySequence(SHORTCUTS["exit"]))
        self.exit_action.setStatusTip("Exit PDFMaster")
        self.exit_action.triggered.connect(self.close)
        file_menu.addAction(self.exit_action)

        edit_menu = menu_bar.addMenu("&Edit")
        self.undo_action = QAction("&Undo", self)
        self.undo_action.setShortcut(QKeySequence(SHORTCUTS["undo"]))
        self.undo_action.setStatusTip("Undo the last edit")
        self.undo_action.triggered.connect(lambda: self.editor.undo())
        edit_menu.addAction(self.undo_action)

        self.redo_action = QAction("&Redo", self)
        self.redo_action.setShortcut(QKeySequence(SHORTCUTS["redo"]))
        self.redo_action.setStatusTip("Redo the last undone edit")
        self.redo_action.triggered.connect(lambda: self.editor.redo())
        edit_menu.addAction(self.redo_action)

        edit_menu.addSeparator()
        self.find_replace_action = QAction("&Find and Replace...", self)
        self.find_replace_action.setShortcut(QKeySequence("Ctrl+H"))
        self.find_replace_action.setStatusTip("Replace text throughout the document")
        self.find_replace_action.triggered.connect(lambda: self.editor.find_and_replace())
        edit_menu.addAction(self.find_replace_action)

        self.organize_action = QAction("&Organize Pages...", self)
        self.organize_action.setShortcut(QKeySequence(SHORTCUTS["organize_pages"]))
        self.organize_action.setStatusTip("Reorder, insert, duplicate, or import pages")
        self.organize_action.triggered.connect(lambda: self.editor.organize_pages())
        edit_menu.addAction(self.organize_action)

        self.form_action = QAction("Fill &Form...", self)
        self.form_action.setShortcut(QKeySequence(SHORTCUTS["fill_forms"]))
        self.form_action.setStatusTip("Fill in this document's form fields")
        self.form_action.triggered.connect(lambda: self.editor.fill_form())
        edit_menu.addAction(self.form_action)

        edit_menu.addSeparator()
        self.delete_action = QAction("&Delete Page", self)
        self.delete_action.setShortcut(QKeySequence(SHORTCUTS["delete_page"]))
        self.delete_action.setStatusTip("Delete the current page")
        self.delete_action.triggered.connect(self.delete_current_page)
        edit_menu.addAction(self.delete_action)

        self.clear_markup_action = QAction("Clear Markup on This &Page", self)
        self.clear_markup_action.setStatusTip("Remove all annotations from this page")
        self.clear_markup_action.triggered.connect(
            lambda: self.editor.clear_page_markup()
        )
        edit_menu.addAction(self.clear_markup_action)

        self.flatten_action = QAction("Fla&tten Document", self)
        self.flatten_action.setStatusTip(
            "Bake annotations and form values into the page"
        )
        self.flatten_action.triggered.connect(lambda: self.editor.flatten_document())
        edit_menu.addAction(self.flatten_action)

        self._create_tools_menu(menu_bar)

        view_menu = menu_bar.addMenu("&View")
        self.toggle_thumbs_action = QAction("Page &Thumbnails", self)
        self.toggle_thumbs_action.setCheckable(True)
        self.toggle_thumbs_action.setShortcut(QKeySequence("F9"))
        self.toggle_thumbs_action.setStatusTip("Show or hide the page sidebar")
        self.toggle_thumbs_action.triggered.connect(
            lambda checked: self._thumb_dock.setVisible(checked)
        )
        view_menu.addAction(self.toggle_thumbs_action)

        self.toggle_info_action = QAction("&Properties Panel", self)
        self.toggle_info_action.setCheckable(True)
        self.toggle_info_action.setShortcut(QKeySequence("F10"))
        self.toggle_info_action.setStatusTip(
            "Show or hide document properties and page markup"
        )
        self.toggle_info_action.triggered.connect(
            lambda checked: self._info_dock.setVisible(checked)
        )
        view_menu.addAction(self.toggle_info_action)
        view_menu.addSeparator()

        self.fit_width_action = QAction("Fit &Width", self)
        self.fit_width_action.setShortcut(QKeySequence(SHORTCUTS["fit_width"]))
        self.fit_width_action.triggered.connect(self.fit_to_width)
        view_menu.addAction(self.fit_width_action)

        self.fit_page_action = QAction("Fit &Page", self)
        self.fit_page_action.setShortcut(QKeySequence(SHORTCUTS["fit_page"]))
        self.fit_page_action.triggered.connect(self.fit_to_page)
        view_menu.addAction(self.fit_page_action)

        view_menu.addSeparator()
        self.zoom_in_action = QAction("Zoom &In", self)
        self.zoom_in_action.setShortcuts(
            [QKeySequence(SHORTCUTS["zoom_in"]), QKeySequence("Ctrl+=")]
        )
        self.zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(self.zoom_in_action)

        self.zoom_out_action = QAction("Zoom &Out", self)
        self.zoom_out_action.setShortcut(QKeySequence(SHORTCUTS["zoom_out"]))
        self.zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(self.zoom_out_action)

        self.reset_zoom_action = QAction("&Reset Zoom", self)
        self.reset_zoom_action.setShortcut(QKeySequence(SHORTCUTS["reset_zoom"]))
        self.reset_zoom_action.triggered.connect(self.reset_view)
        view_menu.addAction(self.reset_zoom_action)

        view_menu.addSeparator()
        self.rotate_cw_action = QAction("Rotate &Clockwise", self)
        self.rotate_cw_action.setShortcut(QKeySequence(SHORTCUTS["rotate_cw"]))
        self.rotate_cw_action.triggered.connect(self.rotate_clockwise)
        view_menu.addAction(self.rotate_cw_action)

        self.rotate_ccw_action = QAction("Rotate Counterclock&wise", self)
        self.rotate_ccw_action.setShortcut(QKeySequence(SHORTCUTS["rotate_ccw"]))
        self.rotate_ccw_action.triggered.connect(self.rotate_counterclockwise)
        view_menu.addAction(self.rotate_ccw_action)

        nav_menu = view_menu.addMenu("&Navigate")
        self.prev_action = QAction("&Previous Page", self)
        self.prev_action.setShortcut(QKeySequence(SHORTCUTS["previous_page"]))
        self.prev_action.triggered.connect(self.previous_page)
        nav_menu.addAction(self.prev_action)

        self.next_action = QAction("&Next Page", self)
        self.next_action.setShortcut(QKeySequence(SHORTCUTS["next_page"]))
        self.next_action.triggered.connect(self.next_page)
        nav_menu.addAction(self.next_action)

        self.first_action = QAction("&First Page", self)
        self.first_action.setShortcut(QKeySequence(SHORTCUTS["first_page"]))
        self.first_action.triggered.connect(self.first_page)
        nav_menu.addAction(self.first_action)

        self.last_action = QAction("&Last Page", self)
        self.last_action.setShortcut(QKeySequence(SHORTCUTS["last_page"]))
        self.last_action.triggered.connect(self.last_page)
        nav_menu.addAction(self.last_action)

        # --- Tools menu additions ---
        tools_menu = self.menuBar().findChild(QAction, "")
        for action in self.menuBar().actions():
            if action.text() == "&Tools":
                tools_menu = action.menu()
                break

        if tools_menu:
            tools_menu.addSeparator()
            self.search_action = QAction("&Search Document...", self)
            self.search_action.setShortcut(QKeySequence(SHORTCUTS["search"]))
            self.search_action.setStatusTip("Search text across all pages")
            self.search_action.triggered.connect(self.open_search_dialog)
            tools_menu.addAction(self.search_action)

            self.ocr_action = QAction("&OCR Scanned Pages...", self)
            self.ocr_action.setShortcut(QKeySequence(SHORTCUTS["ocr"]))
            self.ocr_action.setStatusTip("Extract text from scanned pages using OCR")
            self.ocr_action.triggered.connect(self.open_ocr_dialog)
            tools_menu.addAction(self.ocr_action)

            self.extract_text_action = QAction("E&xtract Text...", self)
            self.extract_text_action.setShortcut(QKeySequence(SHORTCUTS["extract_text"]))
            self.extract_text_action.setStatusTip("Extract text from pages")
            self.extract_text_action.triggered.connect(self.toggle_text_panel)
            tools_menu.addAction(self.extract_text_action)

            tools_menu.addSeparator()
            self.batch_action = QAction("&Batch Processing...", self)
            self.batch_action.setStatusTip("Process multiple PDF files in a folder")
            self.batch_action.triggered.connect(self.open_batch_dialog)
            tools_menu.addAction(self.batch_action)

            tools_menu.addSeparator()
            self.watermark_action = QAction("&Watermark...", self)
            self.watermark_action.setStatusTip("Add a text watermark across pages")
            self.watermark_action.triggered.connect(lambda: self.editor.add_watermark())
            tools_menu.addAction(self.watermark_action)

            self.stamp_action = QAction("S&tamp...", self)
            self.stamp_action.setStatusTip("Add a text or image stamp on this page")
            self.stamp_action.triggered.connect(lambda: self.editor.add_stamp())
            tools_menu.addAction(self.stamp_action)

            tools_menu.addSeparator()
            self.compare_action = QAction("&Compare Documents...", self)
            self.compare_action.setStatusTip(
                "Compare this PDF with another file (text diff per page)"
            )
            self.compare_action.triggered.connect(self.open_compare_dialog)
            tools_menu.addAction(self.compare_action)

            self.pdfa_action = QAction("PDF/&A Check...", self)
            self.pdfa_action.setStatusTip(
                "Inspect PDF/A declaration and basic structure"
            )
            self.pdfa_action.triggered.connect(self.open_pdfa_dialog)
            tools_menu.addAction(self.pdfa_action)

            tools_menu.addSeparator()
            security_menu = tools_menu.addMenu("&Security")
            self.security_info_action = QAction("Security &Info...", self)
            self.security_info_action.setStatusTip("View document security settings")
            self.security_info_action.triggered.connect(self.show_security_info)
            security_menu.addAction(self.security_info_action)

            self.set_password_action = QAction("Set &Password...", self)
            self.set_password_action.setStatusTip("Add password protection to the document")
            self.set_password_action.triggered.connect(self.set_document_password)
            security_menu.addAction(self.set_password_action)

            self.remove_password_action = QAction("&Remove Password...", self)
            self.remove_password_action.setStatusTip("Remove password protection")
            self.remove_password_action.triggered.connect(self.remove_document_password)
            security_menu.addAction(self.remove_password_action)

            self.add_signature_field_action = QAction("Add &Signature Field...", self)
            self.add_signature_field_action.setStatusTip(
                "Place an empty signature field on the current page"
            )
            self.add_signature_field_action.triggered.connect(self.add_signature_field)
            security_menu.addAction(self.add_signature_field_action)

        help_menu = menu_bar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def _create_tools_menu(self, menu_bar) -> None:
        """Build the Tools menu, one exclusive entry per editing tool.

        Every tool lives here; the toolbar carries only the common ones.
        """
        tools_menu = menu_bar.addMenu("&Tools")
        self._tool_group = QActionGroup(self)
        self._tool_group.setExclusive(True)

        # Number keys 1-9 select the tools shown on the toolbar, so the
        # shortcut order matches the button order.
        shortcut_order = {mode: i + 1 for i, mode in enumerate(PRIMARY_TOOLS)}
        for mode in ToolMode:
            action = QAction(TOOL_LABELS[mode], self)
            action.setCheckable(True)
            action.setStatusTip(TOOL_HINTS[mode])
            action.setData(mode)
            action.setIcon(tool_icon(mode, self._scheme))
            number = shortcut_order.get(mode)
            if number is not None and number <= 9:
                action.setShortcut(QKeySequence(str(number)))
                action.setToolTip(
                    f"{TOOL_LABELS[mode]} ({number}) - {TOOL_HINTS[mode]}"
                )
            else:
                action.setToolTip(f"{TOOL_LABELS[mode]} - {TOOL_HINTS[mode]}")
            action.triggered.connect(
                lambda _checked=False, m=mode: self.set_tool(m)
            )
            self._tool_group.addAction(action)
            tools_menu.addAction(action)
            self._tool_actions[mode] = action
            if mode is ToolMode.PAN:
                action.setChecked(True)
                tools_menu.addSeparator()

    def _on_color_changed(self) -> None:
        name = self._color_box.currentData()
        self.editor.highlight_color = name
        self.editor.ink_color = name
        self.statusBar().showMessage(f"Markup colour set to {name}")

    def set_tool(self, mode: ToolMode) -> None:
        """Activate an editing tool and tell the user what it does."""
        self.viewer.set_tool(mode)
        action = self._tool_actions.get(mode)
        if action is not None and not action.isChecked():
            action.setChecked(True)
        self.statusBar().showMessage(f"{TOOL_LABELS[mode]}: {TOOL_HINTS[mode]}")

    def create_ribbon(self) -> None:
        """Build the ribbon with Home, Markup, Edit, and View tabs."""
        ribbon = self._ribbon

        # Set up action icons.
        self.open_action.setIcon(action_icon("open", self._scheme))
        self.save_action.setIcon(action_icon("save", self._scheme))
        self.print_action.setIcon(action_icon("print", self._scheme))
        self.undo_action.setIcon(action_icon("undo", self._scheme))
        self.redo_action.setIcon(action_icon("redo", self._scheme))
        self.organize_action.setIcon(action_icon("organize", self._scheme))
        for name, action in (
            ("open", self.open_action),
            ("save", self.save_action),
            ("print", self.print_action),
            ("undo", self.undo_action),
            ("redo", self.redo_action),
            ("organize", self.organize_action),
        ):
            self._icon_actions[name] = action

        # Short captions under large ribbon icons (menus keep longer text).
        _RIBBON_TOOL_LABELS = {
            ToolMode.PAN: "Select",
            ToolMode.HIGHLIGHT: "Highlight",
            ToolMode.UNDERLINE: "Underline",
            ToolMode.STRIKEOUT: "Strikeout",
            ToolMode.NOTE: "Note",
            ToolMode.PEN: "Pen",
            ToolMode.SHAPE: "Shape",
            ToolMode.TEXT: "Text",
            ToolMode.IMAGE: "Image",
            ToolMode.EDIT_TEXT: "Edit",
            ToolMode.REDACT: "Redact",
            ToolMode.ERASE: "Erase",
            ToolMode.DELETE_ANNOT: "Delete",
        }
        for mode, caption in _RIBBON_TOOL_LABELS.items():
            self._tool_actions[mode].setIconText(caption)

        # --- HOME TAB ---
        home = ribbon.add_tab("home", "Home")

        # File group.
        file_grp = home.add_group("File")
        file_grp.add_action(self.open_action, large=True, label="Open")
        file_grp.add_action(self.save_action, large=True, label="Save")
        file_grp.add_action(self.print_action, large=True, label="Print")

        # Edit group.
        edit_grp = home.add_group("Edit")
        edit_grp.add_action(self.undo_action, large=True, label="Undo")
        edit_grp.add_action(self.redo_action, large=True, label="Redo")

        # Navigate group.
        nav_grp = home.add_group("Navigate")
        self.prev_button = QAction(action_icon("prev", self._scheme), "", self)
        self.prev_button.setToolTip("Previous page")
        self.prev_button.triggered.connect(self.previous_page)
        nav_grp.add_action(self.prev_button)
        self._icon_actions["prev"] = self.prev_button

        self._page_spin = QSpinBox()
        self._page_spin.setMinimum(1)
        self._page_spin.setMaximum(1)
        self._page_spin.setFixedWidth(55)
        self._page_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_spin.setToolTip("Current page")
        self._page_spin.valueChanged.connect(self.go_to_page_spin)
        nav_grp.add_widget(self._page_spin)

        self._page_count_label = QLabel("/ 0")
        self._page_count_label.setMinimumWidth(30)
        nav_grp.add_widget(self._page_count_label)

        self.next_button = QAction(action_icon("next", self._scheme), "", self)
        self.next_button.setToolTip("Next page")
        self.next_button.triggered.connect(self.next_page)
        nav_grp.add_action(self.next_button)
        self._icon_actions["next"] = self.next_button

        # Zoom group.
        zoom_grp = home.add_group("Zoom")
        zoom_out_action = QAction(action_icon("zoom_out", self._scheme), "", self)
        zoom_out_action.setToolTip("Zoom out")
        zoom_out_action.triggered.connect(self.zoom_out)
        zoom_grp.add_action(zoom_out_action)
        self._icon_actions["zoom_out"] = zoom_out_action

        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setMinimum(ZOOM_MIN)
        self._zoom_slider.setMaximum(ZOOM_MAX)
        self._zoom_slider.setSingleStep(ZOOM_STEP)
        self._zoom_slider.setPageStep(ZOOM_STEP)
        self._zoom_slider.setValue(ZOOM_DEFAULT)
        self._zoom_slider.setFixedWidth(90)
        self._zoom_slider.setToolTip("Zoom")
        self._zoom_slider.valueChanged.connect(self.slider_zoom_changed)
        zoom_grp.add_widget(self._zoom_slider)

        zoom_in_action = QAction(action_icon("zoom_in", self._scheme), "", self)
        zoom_in_action.setToolTip("Zoom in")
        zoom_in_action.triggered.connect(self.zoom_in)
        zoom_grp.add_action(zoom_in_action)
        self._icon_actions["zoom_in"] = zoom_in_action

        self._zoom_label = QLabel("100%")
        self._zoom_label.setMinimumWidth(38)
        zoom_grp.add_widget(self._zoom_label)

        # Fit group.
        fit_grp = home.add_group("Fit")
        fit_width_action = QAction(action_icon("fit_width", self._scheme), "", self)
        fit_width_action.setToolTip("Fit width")
        fit_width_action.triggered.connect(self.fit_to_width)
        fit_grp.add_action(fit_width_action, large=True, label="Width")
        self._icon_actions["fit_width"] = fit_width_action

        fit_page_action = QAction(action_icon("fit_page", self._scheme), "", self)
        fit_page_action.setToolTip("Fit page")
        fit_page_action.triggered.connect(self.fit_to_page)
        fit_grp.add_action(fit_page_action, large=True, label="Page")
        self._icon_actions["fit_page"] = fit_page_action

        # --- MARKUP TAB ---
        markup = ribbon.add_tab("markup", "Markup")

        # Select: icon-only under the group title (avoids "Select" twice).
        select_grp = markup.add_group("Select")
        select_grp.add_action(self._tool_actions[ToolMode.PAN], large=True, label="")

        # Primary markup stays large; secondary tools are icon-only.
        text_markup_grp = markup.add_group("Text Markup")
        text_markup_grp.add_action(
            self._tool_actions[ToolMode.HIGHLIGHT], large=True, label="Highlight"
        )
        text_markup_grp.add_action(self._tool_actions[ToolMode.UNDERLINE], large=False)
        text_markup_grp.add_action(self._tool_actions[ToolMode.STRIKEOUT], large=False)

        shapes_grp = markup.add_group("Shapes")
        shapes_grp.add_action(self._tool_actions[ToolMode.PEN], large=True, label="Pen")
        shapes_grp.add_action(
            self._tool_actions[ToolMode.SHAPE], large=True, label="Shape"
        )

        notes_grp = markup.add_group("Notes")
        notes_grp.add_action(self._tool_actions[ToolMode.NOTE], large=True, label="Note")
        notes_grp.add_action(self._tool_actions[ToolMode.DELETE_ANNOT], large=False)

        stamp_grp = markup.add_group("Stamp")
        self._wire_phase_tool_icons()
        if hasattr(self, "watermark_action"):
            stamp_grp.add_action(self.watermark_action, large=True, label="Watermark")
        if hasattr(self, "stamp_action"):
            stamp_grp.add_action(self.stamp_action, large=True, label="Stamp")

        color_grp = markup.add_group("Color")
        self._color_box = QComboBox()
        self._color_box.setIconSize(QSize(14, 14))
        for name, rgb in ANNOT_COLORS.items():
            self._color_box.addItem(swatch_icon(rgb), name.title(), name)
        self._color_box.setToolTip("Markup colour")
        self._color_box.setFixedWidth(100)
        self._color_box.currentIndexChanged.connect(self._on_color_changed)
        color_grp.add_widget(self._color_box)

        # --- EDIT TAB ---
        edit_tab = ribbon.add_tab("edit", "Edit")

        text_grp = edit_tab.add_group("Text")
        text_grp.add_action(self._tool_actions[ToolMode.TEXT], large=True, label="Text")
        text_grp.add_action(
            self._tool_actions[ToolMode.EDIT_TEXT], large=True, label="Edit"
        )

        insert_grp = edit_tab.add_group("Insert")
        insert_grp.add_action(
            self._tool_actions[ToolMode.IMAGE], large=True, label="Image"
        )

        remove_grp = edit_tab.add_group("Remove")
        remove_grp.add_action(self._tool_actions[ToolMode.ERASE], large=False)
        remove_grp.add_action(
            self._tool_actions[ToolMode.REDACT], large=True, label="Redact"
        )

        forms_grp = edit_tab.add_group("Forms")
        self.form_action.setIcon(action_icon("form", self._scheme))
        forms_grp.add_action(self.form_action, large=True, label="Form")
        self._icon_actions["form"] = self.form_action

        # --- ORGANIZE TAB ---
        organize = ribbon.add_tab("organize", "Organize")

        pages_grp = organize.add_group("Pages")
        self.organize_action.setIcon(action_icon("organize", self._scheme))
        self.delete_action.setIcon(action_icon("delete_page", self._scheme))
        pages_grp.add_action(self.organize_action, large=True, label="Organize")
        pages_grp.add_action(self.delete_action, large=True, label="Delete")
        self._icon_actions["organize"] = self.organize_action
        self._icon_actions["delete_page"] = self.delete_action

        rotate_grp = organize.add_group("Rotate")
        rotate_ccw_action = QAction(action_icon("rotate_ccw", self._scheme), "", self)
        rotate_ccw_action.setToolTip("Rotate counterclockwise")
        rotate_ccw_action.triggered.connect(self.rotate_counterclockwise)
        rotate_grp.add_action(rotate_ccw_action, large=True, label="Left")
        self._icon_actions["rotate_ccw"] = rotate_ccw_action

        rotate_cw_action = QAction(action_icon("rotate_cw", self._scheme), "", self)
        rotate_cw_action.setToolTip("Rotate clockwise")
        rotate_cw_action.triggered.connect(self.rotate_clockwise)
        rotate_grp.add_action(rotate_cw_action, large=True, label="Right")
        self._icon_actions["rotate_cw"] = rotate_cw_action

        # --- REVIEW TAB (Compare, PDF/A, search, batch — visible on the ribbon) ---
        review_tab = ribbon.add_tab("review", "Review")

        find_grp = review_tab.add_group("Find")
        if hasattr(self, "search_action"):
            find_grp.add_action(self.search_action, large=True, label="Search")
        if hasattr(self, "ocr_action"):
            find_grp.add_action(self.ocr_action, large=True, label="OCR")
        if hasattr(self, "extract_text_action"):
            find_grp.add_action(self.extract_text_action, large=False)

        compare_grp = review_tab.add_group("Compare")
        if hasattr(self, "compare_action"):
            compare_grp.add_action(self.compare_action, large=True, label="Compare")
        if hasattr(self, "pdfa_action"):
            compare_grp.add_action(self.pdfa_action, large=True, label="PDF/A")

        workflow_grp = review_tab.add_group("Workflow")
        if hasattr(self, "batch_action"):
            workflow_grp.add_action(self.batch_action, large=True, label="Batch")

        # --- VIEW TAB ---
        view_tab = ribbon.add_tab("view", "View")

        panels_grp = view_tab.add_group("Panels")
        self.toggle_thumbs_action.setIcon(action_icon("sidebar", self._scheme))
        self.toggle_info_action.setIcon(action_icon("panel", self._scheme))
        panels_grp.add_action(self.toggle_thumbs_action, large=True, label="Pages")
        panels_grp.add_action(self.toggle_info_action, large=True, label="Props")
        self._icon_actions["sidebar"] = self.toggle_thumbs_action
        self._icon_actions["panel"] = self.toggle_info_action

    def _wire_phase_tool_icons(self) -> None:
        """Icons for Tools-menu actions that also appear on the Review / Markup ribbon."""
        mapping = (
            ("search", "search_action"),
            ("ocr", "ocr_action"),
            ("batch", "batch_action"),
            ("watermark", "watermark_action"),
            ("stamp", "stamp_action"),
            ("compare", "compare_action"),
            ("pdfa", "pdfa_action"),
        )
        for icon_name, attr in mapping:
            action = getattr(self, attr, None)
            if action is not None:
                self._assign_action_icon(icon_name, action)

    def create_docks(self) -> None:
        """Create the thumbnail sidebar, bookmarks, text extract, and properties panels."""
        self.thumbnails = ThumbnailPanel(self)
        self.thumbnails.page_selected.connect(self._on_thumbnail_selected)
        self._thumb_dock = QDockWidget("Pages", self)
        self._thumb_dock.setObjectName("thumbnail_dock")
        self._thumb_dock.setWidget(self.thumbnails)
        self._thumb_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._thumb_dock)

        self.bookmarks_panel = BookmarksPanel(self)
        self.bookmarks_panel.page_requested.connect(self._on_bookmark_selected)
        self._bookmarks_dock = QDockWidget("Bookmarks", self)
        self._bookmarks_dock.setObjectName("bookmarks_dock")
        self._bookmarks_dock.setWidget(self.bookmarks_panel)
        self._bookmarks_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._bookmarks_dock)
        self.tabifyDockWidget(self._thumb_dock, self._bookmarks_dock)
        self._thumb_dock.raise_()
        # Progressive disclosure: hide side chrome until a document is open.
        self._thumb_dock.hide()
        self._bookmarks_dock.hide()

        self.info_panel = InfoPanel(self)
        self.info_panel.delete_requested.connect(self._on_delete_annotation)
        self._info_dock = QDockWidget("Properties", self)
        self._info_dock.setObjectName("info_dock")
        self._info_dock.setWidget(self.info_panel)
        self._info_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._info_dock)
        self._info_dock.hide()

        self.text_extract_panel = TextExtractPanel(self)
        self._text_extract_dock = QDockWidget("Text Extraction", self)
        self._text_extract_dock.setObjectName("text_extract_dock")
        self._text_extract_dock.setWidget(self.text_extract_panel)
        self._text_extract_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._text_extract_dock)
        self._text_extract_dock.hide()

        self.toggle_thumbs_action.setChecked(False)
        self.toggle_info_action.setChecked(False)
        self._thumb_dock.visibilityChanged.connect(
            lambda visible: self.toggle_thumbs_action.setChecked(visible)
        )
        self._info_dock.visibilityChanged.connect(
            lambda visible: self.toggle_info_action.setChecked(visible)
        )

    def _on_thumbnail_selected(self, page: int) -> None:
        """Handle thumbnail click by navigating to that page."""
        if self.viewer is not None:
            self.viewer.go_to_page(page)

    def _on_bookmark_selected(self, page: int) -> None:
        """Handle bookmark click by navigating to that page."""
        if self.viewer is not None:
            self.viewer.go_to_page(page)

    def _on_delete_annotation(self, page: int, index: int) -> None:
        """Delete an annotation chosen in the properties panel."""
        self.editor.delete_annotation_at_index(page, index)

    def create_status_bar(self) -> None:
        """Create the status bar used for operation feedback."""
        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage("Open a PDF to begin")

    def _sync_empty_workspace(self) -> None:
        """Show welcome home when no tabs remain; document surface otherwise."""
        has_docs = self._tabs.count() > 0
        if has_docs:
            self._workspace.setCurrentWidget(self._tabs)
            self._ribbon.set_compact(False)
            if not self._docks_auto_shown:
                self._thumb_dock.show()
                self._thumb_dock.raise_()
                self.toggle_thumbs_action.setChecked(True)
                self._docks_auto_shown = True
        else:
            self._workspace.setCurrentWidget(self._welcome)
            self._ribbon.set_compact(True)
            self._welcome.refresh_recents()
            self._thumb_dock.hide()
            self._bookmarks_dock.hide()
            self._info_dock.hide()
            self._text_extract_dock.hide()
            self.toggle_thumbs_action.setChecked(False)
            self.toggle_info_action.setChecked(False)
            self._docks_auto_shown = False
            if self.statusBar() is not None:
                self.statusBar().showMessage("Open a PDF to begin")

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------
    def open_file(self, path: Optional[str] = None) -> None:
        """Open a PDF from a dialog or an explicit path."""
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Open PDF", str(Path.home()), PDF_FILTER)
            if not path:
                return
        self._load_path(path)

    def _load_path(self, path: str) -> None:
        file_path = Path(path)

        # If the file is already open, switch to that tab.
        existing_idx = self._tabs.find_tab(file_path)
        if existing_idx >= 0:
            self._tabs.setCurrentIndex(existing_idx)
            self.statusBar().showMessage(f"Switched to {file_path.name}")
            return

        try:
            FileHandler.validate_pdf(path)
            document = PDFHandler.open_document(path)
        except ValidationError:
            self._show_error("Invalid PDF", MSG_INVALID_PDF)
            return
        except FileOperationError:
            self._show_error("File not found", MSG_FILE_NOT_FOUND)
            return
        except PDFLoadError as exc:
            message = str(exc)
            if "password" in message.lower():
                self._show_error("Encrypted PDF", MSG_ENCRYPTED_PDF)
            else:
                self._show_error("Could not open PDF", message or MSG_LOAD_ERROR)
            return
        except PDFMasterException as exc:
            self._show_error("Could not open PDF", str(exc))
            return

        # Open a new tab for this document.
        self._tabs.open_document(document)
        self._connect_current_tab()
        self.thumbnails.set_document(document)
        self.bookmarks_panel.set_document(document)
        self.info_panel.set_document(document)
        self.text_extract_panel.set_document(document)
        self.editor.reset()
        self.set_tool(ToolMode.PAN)
        self._set_document_actions_enabled(True)
        self.setWindowTitle(self._format_window_title(document.filename))
        self.statusBar().showMessage(
            MSG_OPEN_SUCCESS.format(filename=document.filename, pages=document.page_count)
        )
        try:
            FileHandler.save_recent_file(path, CONFIG_DIR, MAX_RECENT_FILES)
        except FileOperationError:
            logger.warning("Could not update recent files list")
        self._reload_recent_menu()
        self.update_page_info()
        self.update_zoom_display()
        self._sync_empty_workspace()
        logger.info("UI opened %s", document.filename)

        if document.was_repaired:
            QMessageBox.warning(
                self,
                "Damaged PDF repaired",
                MSG_REPAIRED_PDF.format(filename=document.filename),
            )

    def save_file(self) -> None:
        """Save the open document in place."""
        if self.document is None:
            self.statusBar().showMessage(MSG_NO_DOCUMENT)
            return
        try:
            saved = self.document.save(incremental=True)
        except PageOperationError:
            logger.exception("In-place save failed, trying a full rewrite")
            try:
                saved = self.document.save(incremental=False)
            except PageOperationError as exc:
                self._show_error("Save failed", str(exc) or MSG_SAVE_ERROR)
                return
        self.statusBar().showMessage(MSG_SAVE_SUCCESS.format(filename=saved.name))
        self.setWindowTitle(self._format_window_title(saved.name))

    def save_file_as(self) -> None:
        """Save the open document to a user-chosen path."""
        if self.document is None:
            self.statusBar().showMessage(MSG_NO_DOCUMENT)
            return
        suggested = str(FileHandler.get_output_path(self.document.file_path))
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF As", suggested, PDF_FILTER)
        if not path:
            return
        try:
            saved = self.document.save(FileHandler.ensure_pdf_suffix(path), incremental=False)
        except PageOperationError as exc:
            self._show_error("Save failed", str(exc) or MSG_SAVE_ERROR)
            return
        self.statusBar().showMessage(MSG_SAVE_SUCCESS.format(filename=saved.name))
        self.setWindowTitle(self._format_window_title(saved.name))

    def _reload_recent_menu(self) -> None:
        if self._recent_menu is None:
            return
        self._recent_menu.clear()
        try:
            recent = FileHandler.get_recent_files(CONFIG_DIR)
        except FileOperationError:
            recent = []
        if not recent:
            empty = QAction("(None)", self)
            empty.setEnabled(False)
            self._recent_menu.addAction(empty)
        else:
            for item in recent:
                action = QAction(item, self)
                action.triggered.connect(lambda _checked=False, p=item: self.open_file(p))
                self._recent_menu.addAction(action)
        self._welcome.refresh_recents()

    # ------------------------------------------------------------------
    # Tab management
    # ------------------------------------------------------------------
    def _connect_current_tab(self) -> None:
        """Wire up signals from the current tab's viewer."""
        viewer = self.viewer
        if viewer is None:
            return

        # Check if we've already connected to this viewer to avoid duplicates.
        if getattr(viewer, "_mw_connected", False):
            return
        viewer._mw_connected = True

        # Connect to the new tab's viewer.
        viewer.page_changed.connect(self.update_page_info)
        viewer.zoom_changed.connect(self.update_zoom_display)
        viewer.render_failed.connect(self._on_render_failed)
        viewer.area_selected.connect(self.editor.handle_area)
        viewer.point_selected.connect(self.editor.handle_point)
        viewer.ink_drawn.connect(self.editor.handle_ink)

    def _on_tab_changed(self, index: int) -> None:
        """Handle switching between tabs."""
        if index < 0:
            # No tabs open.
            self.thumbnails.set_document(None)
            self.bookmarks_panel.set_document(None)
            self.info_panel.set_document(None)
            self.text_extract_panel.set_document(None)
            self._set_document_actions_enabled(False)
            self.setWindowTitle(self._format_window_title())
            self.update_page_info(0)
            return

        self._connect_current_tab()
        doc = self.document
        if doc:
            self.thumbnails.set_document(doc)
            self.bookmarks_panel.set_document(doc)
            self.info_panel.set_document(doc)
            self.text_extract_panel.set_document(doc)
            self._set_document_actions_enabled(True)
            self.setWindowTitle(self._format_window_title(doc.filename))
            self.update_page_info(self.viewer.current_page if self.viewer else 0)
            self.update_zoom_display(self.viewer.zoom_level if self.viewer else 1.0)
            self.update_history_actions()

    def _on_tab_count_changed(self, count: int) -> None:
        """Update UI when tabs are opened/closed."""
        self._set_document_actions_enabled(count > 0)
        self._sync_empty_workspace()

    # ------------------------------------------------------------------
    # Navigation / zoom / rotate
    # ------------------------------------------------------------------
    def next_page(self) -> None:
        self.viewer.next_page()
        self.statusBar().showMessage("Next page")

    def previous_page(self) -> None:
        self.viewer.previous_page()
        self.statusBar().showMessage("Previous page")

    def first_page(self) -> None:
        self.viewer.first_page()
        self.statusBar().showMessage("First page")

    def last_page(self) -> None:
        self.viewer.last_page()
        self.statusBar().showMessage("Last page")

    def go_to_page_spin(self, value: int) -> None:
        if self._updating_ui or self.document is None:
            return
        self.viewer.go_to_page(value - 1)

    def zoom_in(self) -> None:
        self.viewer.zoom_in()
        self.statusBar().showMessage("Zoomed in")

    def zoom_out(self) -> None:
        self.viewer.zoom_out()
        self.statusBar().showMessage("Zoomed out")

    def slider_zoom_changed(self, value: int) -> None:
        if self._updating_ui:
            return
        self.viewer.set_zoom(value / 100.0)

    def fit_to_width(self) -> None:
        self.viewer.fit_to_width()
        self.statusBar().showMessage("Fit to width")

    def fit_to_page(self) -> None:
        self.viewer.fit_to_page()
        self.statusBar().showMessage("Fit to page")

    def rotate_clockwise(self) -> None:
        self._rotate(90)

    def rotate_counterclockwise(self) -> None:
        self._rotate(-90)

    def _rotate(self, degrees: int) -> None:
        if self.document is None:
            return
        try:
            applied = self.viewer.rotate_page(degrees)
        except PageOperationError as exc:
            self._show_error("Could not rotate page", str(exc))
            return
        self.statusBar().showMessage(
            MSG_PAGE_ROTATED.format(page=self.viewer.current_page + 1, rotation=applied)
        )

    def reset_view(self) -> None:
        self.viewer.reset_view()
        self.statusBar().showMessage("View reset to 100% and 0°")

    def delete_current_page(self) -> None:
        if self.document is None:
            self.statusBar().showMessage(MSG_NO_DOCUMENT)
            return
        if self.document.page_count <= 1:
            QMessageBox.information(self, APP_NAME, MSG_LAST_PAGE)
            return
        page = self.viewer.current_page + 1
        confirm = QMessageBox.question(
            self,
            "Delete page",
            f"Delete page {page} of {self.document.page_count}? This can be saved to the file.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            self.document.delete_page(self.viewer.current_page)
        except PageOperationError as exc:
            self._show_error("Could not delete page", str(exc))
            return
        self.refresh_after_edit()
        self.statusBar().showMessage(MSG_PAGE_DELETED.format(page=page))

    def update_page_info(self, _page: int = 0) -> None:
        """Refresh page spinbox, counter, and window title after navigation."""
        self._updating_ui = True
        try:
            if self.document is None or self.viewer is None:
                self._page_spin.setMinimum(1)
                self._page_spin.setMaximum(1)
                self._page_spin.setValue(1)
                self._page_count_label.setText("/ 0")
                return
            count = self.document.page_count
            current = self.viewer.current_page + 1
            self._page_spin.setMinimum(1)
            self._page_spin.setMaximum(max(1, count))
            self._page_spin.setValue(current)
            self._page_count_label.setText(f"/ {count}")
            self.thumbnails.set_current_page(current - 1)
            self.info_panel.refresh(current - 1)
            self.text_extract_panel.set_current_page(current - 1)
        finally:
            self._updating_ui = False

    def update_zoom_display(self, zoom: float = 0.0) -> None:
        """Keep the slider and percentage label in sync with the viewer."""
        self._updating_ui = True
        try:
            percent = int(round((zoom or self.viewer.zoom_level) * 100))
            percent = max(ZOOM_MIN, min(ZOOM_MAX, percent))
            self._zoom_slider.setValue(percent)
            self._zoom_label.setText(f"{percent}%")
        finally:
            self._updating_ui = False

    def _on_render_failed(self, message: str) -> None:
        """Surface a background render failure without a modal dialog."""
        logger.error("Render failed: %s", message)
        self.statusBar().showMessage(f"Render failed: {message}")

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            (
                f"<h3>{APP_NAME} {APP_VERSION}</h3>"
                f"<p>{APP_DESCRIPTION}</p>"
                f"<p>Author: {APP_AUTHOR}<br>License: {APP_LICENSE}</p>"
                "<p>Built with PySide6, PyMuPDF, and PyPDF.</p>"
            ),
        )

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Close all tabs and exit, prompting for unsaved changes."""
        # Drain thumbnail workers first.
        self.thumbnails.set_document(None)
        self.thumbnails.wait_for_render()
        self.bookmarks_panel.set_document(None)
        self.info_panel.set_document(None)
        self.text_extract_panel.set_document(None)

        # Close all tabs (will prompt for unsaved changes).
        if not self._tabs.close_all():
            event.ignore()
            return

        logger.info("Application window closing")
        event.accept()

    def _confirm_discard_changes(self) -> bool:
        """Check if the current document has unsaved changes."""
        if self.document is None or not self.document.is_modified:
            return True
        result = QMessageBox.question(
            self,
            "Unsaved changes",
            "The document has unsaved changes. Save before continuing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if result == QMessageBox.StandardButton.Cancel:
            return False
        if result == QMessageBox.StandardButton.Save:
            self.save_file()
            return not self.document.is_modified
        return True

    def refresh_after_edit(self) -> None:
        """Re-render the page and resync the page controls after an edit.

        Edits can change the page count (page organiser, undo), so the
        current page is clamped before refreshing.
        """
        if self.document is None or self.viewer is None:
            return
        last = max(0, self.document.page_count - 1)
        if self.viewer.current_page > last:
            self.viewer.go_to_page(last)
        self.viewer.refresh()
        self._tabs.refresh_current()
        self.thumbnails.refresh()
        self.update_page_info()

    def update_history_actions(self) -> None:
        """Enable Undo/Redo only when there is something to apply."""
        history = self.history
        has_document = self.document is not None
        can_undo = has_document and history is not None and history.can_undo
        can_redo = has_document and history is not None and history.can_redo
        self.undo_action.setEnabled(can_undo)
        self.redo_action.setEnabled(can_redo)

    def _set_document_actions_enabled(self, enabled: bool) -> None:
        for action in (
            self.save_action,
            self.save_as_action,
            self.print_action,
            self.print_preview_action,
            self.export_images_action,
            self.find_replace_action,
            self.organize_action,
            self.form_action,
            self.clear_markup_action,
            self.flatten_action,
            self.delete_action,
            getattr(self, "watermark_action", None),
            getattr(self, "stamp_action", None),
            getattr(self, "compare_action", None),
            getattr(self, "pdfa_action", None),
            getattr(self, "add_signature_field_action", None),
            self.fit_width_action,
            self.fit_page_action,
            self.zoom_in_action,
            self.zoom_out_action,
            self.reset_zoom_action,
            self.rotate_cw_action,
            self.rotate_ccw_action,
            self.prev_action,
            self.next_action,
            self.first_action,
            self.last_action,
        ):
            if action is not None:
                action.setEnabled(enabled)
        for action in self._tool_actions.values():
            action.setEnabled(enabled)
        for widget in (
            self._page_spin,
            self._zoom_slider,
        ):
            widget.setEnabled(enabled)
        self.update_history_actions()

    def _show_error(self, title: str, message: str) -> None:
        logger.error("%s: %s", title, message)
        self.statusBar().showMessage(message)
        QMessageBox.critical(self, title, message)

    # ------------------------------------------------------------------
    # Phase 3 features: Search, OCR, Batch, Security
    # ------------------------------------------------------------------
    def open_search_dialog(self) -> None:
        """Open the document search dialog."""
        if self.document is None:
            self.statusBar().showMessage(MSG_NO_DOCUMENT)
            return
        dialog = SearchDialog(self.document, self)
        dialog.go_to_page.connect(lambda page: self.viewer.go_to_page(page) if self.viewer else None)
        dialog.show()

    def open_ocr_dialog(self) -> None:
        """Open the OCR dialog for scanned pages."""
        if self.document is None:
            self.statusBar().showMessage(MSG_NO_DOCUMENT)
            return
        current_page = self.viewer.current_page if self.viewer else 0
        dialog = OCRDialog(self.document, current_page, self)
        dialog.exec()

    def open_batch_dialog(self) -> None:
        """Open the batch processing dialog."""
        dialog = BatchDialog(self)
        dialog.exec()

    def open_compare_dialog(self) -> None:
        """Compare the open document with another PDF."""
        if self.document is None:
            self.statusBar().showMessage(MSG_NO_DOCUMENT)
            return
        dialog = CompareDialog(self.document.file_path, self)
        dialog.exec()

    def open_pdfa_dialog(self) -> None:
        """Inspect PDF/A markers on the open document."""
        if self.document is None:
            self.statusBar().showMessage(MSG_NO_DOCUMENT)
            return
        dialog = PdfaDialog(self.document, self)
        dialog.exec()

    def toggle_text_panel(self) -> None:
        """Toggle the text extraction panel visibility."""
        if self._text_extract_dock.isVisible():
            self._text_extract_dock.hide()
        else:
            self._text_extract_dock.show()
            if self.document and self.viewer:
                self.text_extract_panel.set_current_page(self.viewer.current_page)

    def show_security_info(self) -> None:
        """Show security information about the current document."""
        if self.document is None:
            self.statusBar().showMessage(MSG_NO_DOCUMENT)
            return
        dialog = SecurityInfoDialog(self.document, self)
        dialog.exec()

    def add_signature_field(self) -> None:
        """Add an empty signature widget on the current page."""
        if self.document is None:
            self.statusBar().showMessage(MSG_NO_DOCUMENT)
            return
        name, ok = QInputDialog.getText(
            self,
            "Signature Field",
            "Field name:",
            text="Signature",
        )
        if not ok:
            return
        self.editor.add_signature_field(name)

    def set_document_password(self) -> None:
        """Set password protection on the current document."""
        if self.document is None:
            self.statusBar().showMessage(MSG_NO_DOCUMENT)
            return

        dialog = SetPasswordDialog(self.document, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        settings = dialog.get_settings()
        suggested = str(FileHandler.get_output_path(self.document.file_path, "_protected"))
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Protected PDF", suggested, PDF_FILTER
        )
        if not path:
            return

        try:
            from pathlib import Path
            output = Path(path)
            SecurityService.set_password(
                self.document,
                output,
                user_password=settings["user_password"],
                owner_password=settings["owner_password"],
                permissions=settings["permissions"],
                encryption=settings["encryption"],
            )
            self.statusBar().showMessage(f"Password protection saved to {output.name}")
        except Exception as exc:
            self._show_error("Password Error", str(exc))

    def remove_document_password(self) -> None:
        """Remove password protection from the current document."""
        if self.document is None:
            self.statusBar().showMessage(MSG_NO_DOCUMENT)
            return

        suggested = str(FileHandler.get_output_path(self.document.file_path, "_decrypted"))
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Decrypted PDF", suggested, PDF_FILTER
        )
        if not path:
            return

        try:
            from pathlib import Path
            output = Path(path)
            SecurityService.remove_password(self.document, output)
            self.statusBar().showMessage(f"Decrypted PDF saved to {output.name}")
        except Exception as exc:
            self._show_error("Decryption Error", str(exc))
