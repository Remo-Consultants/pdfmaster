"""Application-wide configuration constants for PDFMaster."""

from pathlib import Path

# ---------------------------------------------------------------------------
# Application identity
# ---------------------------------------------------------------------------
APP_NAME = "PDFMaster"
APP_VERSION = "0.7.0"
APP_AUTHOR = "PDFMaster Contributors"
APP_DESCRIPTION = "A professional PDF viewer and editor for Windows"
APP_LICENSE = "MIT"
ORGANIZATION_NAME = "PDFMaster"

# App / window icon (PNG for Qt; ICO for Windows packaging).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_ICON_PNG = _PROJECT_ROOT / "resources" / "icons" / "pdfmaster.png"
APP_ICON_ICO = _PROJECT_ROOT / "resources" / "icons" / "pdfmaster.ico"
APP_ICON_PATH = APP_ICON_PNG if APP_ICON_PNG.is_file() else APP_ICON_ICO

# ---------------------------------------------------------------------------
# Window geometry
# ---------------------------------------------------------------------------
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
# The ribbon and thumbnail sidebar need room at small window sizes.
WINDOW_MIN_WIDTH = 1024
WINDOW_MIN_HEIGHT = 640

# ---------------------------------------------------------------------------
# Zoom (percent values used by the UI slider; viewer uses a 1.0-based scale)
# ---------------------------------------------------------------------------
ZOOM_MIN = 25
ZOOM_MAX = 400
ZOOM_STEP = 10
ZOOM_DEFAULT = 100
ZOOM_MIN_FACTOR = ZOOM_MIN / 100.0
ZOOM_MAX_FACTOR = ZOOM_MAX / 100.0
ZOOM_STEP_FACTOR = ZOOM_STEP / 100.0
ZOOM_DEFAULT_FACTOR = ZOOM_DEFAULT / 100.0

# ---------------------------------------------------------------------------
# Viewer appearance
# ---------------------------------------------------------------------------
VIEWER_BACKGROUND = "#1e1e1e"
VIEWER_PAGE_SHADOW = "#000000"
STATUS_READY = "Ready"

# ---------------------------------------------------------------------------
# File handling
# ---------------------------------------------------------------------------
PDF_EXTENSIONS = [".pdf"]
PDF_FILTER = "PDF Files (*.pdf);;All Files (*.*)"
PDF_MAGIC = b"%PDF-"
# The spec allows junk before the header, so search instead of matching byte 0.
PDF_HEADER_SEARCH_BYTES = 1024
MAX_RECENT_FILES = 10
MAX_FILE_SIZE_MB = 500

# ---------------------------------------------------------------------------
# Paths (~/.pdfmaster on all platforms)
# ---------------------------------------------------------------------------
CONFIG_DIR = Path.home() / ".pdfmaster"
LOG_DIR = CONFIG_DIR / "logs"
LOG_FILE = LOG_DIR / "pdfmaster.log"
RECENT_FILES_PATH = CONFIG_DIR / "recent_files.txt"

# ---------------------------------------------------------------------------
# Keyboard shortcuts
# ---------------------------------------------------------------------------
SHORTCUTS = {
    "open": "Ctrl+O",
    "save": "Ctrl+S",
    "print": "Ctrl+P",
    "print_preview": "Ctrl+Shift+P",
    "undo": "Ctrl+Z",
    "redo": "Ctrl+Y",
    "organize_pages": "Ctrl+Shift+O",
    "fill_forms": "Ctrl+Shift+F",
    "export_images": "Ctrl+Shift+E",
    "exit": "Ctrl+Q",
    "reset_zoom": "Ctrl+0",
    "zoom_in": "Ctrl++",
    "zoom_out": "Ctrl+-",
    "previous_page": "PgUp",
    "next_page": "PgDown",
    "first_page": "Ctrl+Home",
    "last_page": "Ctrl+End",
    "delete_page": "Delete",
    "rotate_cw": "Ctrl+R",
    "rotate_ccw": "Ctrl+Shift+R",
    "fit_width": "Ctrl+1",
    "fit_page": "Ctrl+2",
    "search": "Ctrl+F",
    "ocr": "Ctrl+Shift+T",
    "extract_text": "Ctrl+T",
    "toggle_bookmarks": "F11",
    "toggle_text_panel": "F12",
}

# ---------------------------------------------------------------------------
# User-facing messages
# ---------------------------------------------------------------------------
MSG_OPEN_SUCCESS = "Opened {filename} ({pages} pages)"
MSG_SAVE_SUCCESS = "Saved {filename}"
MSG_PAGE_DELETED = "Deleted page {page}"
MSG_PAGE_ROTATED = "Rotated page {page} to {rotation}°"
MSG_NO_DOCUMENT = "No document is open."
MSG_LAST_PAGE = "Cannot delete the last remaining page."
MSG_INVALID_PDF = "The selected file is not a valid PDF."
MSG_FILE_NOT_FOUND = "The selected file could not be found."
MSG_FILE_TOO_LARGE = "The selected file exceeds the {limit} MB size limit."
MSG_ENCRYPTED_PDF = "This PDF is password-protected and cannot be opened."
MSG_RENDER_ERROR = "Could not render page {page}."
MSG_SAVE_ERROR = "Could not save the document."
MSG_LOAD_ERROR = "Could not open the PDF file."
MSG_RENDERING = "Rendering page {page}..."
MSG_REPAIRED_PDF = (
    "{filename} was damaged and has been repaired for viewing. "
    "Some content may be missing. Use Save As to keep the repaired copy."
)

# ---------------------------------------------------------------------------
# Default runtime settings
# ---------------------------------------------------------------------------
DEFAULT_SETTINGS = {
    "zoom": ZOOM_DEFAULT,
    "fit_mode": "none",
    "show_status_bar": True,
    "remember_recent": True,
    "log_level": "INFO",
}

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Render cache is bounded by both entry count and total pixel memory,
# because one A4 page at 400% zoom is already ~30 MB.
MAX_RENDER_CACHE = 12
MAX_RENDER_CACHE_MB = 192

# ---------------------------------------------------------------------------
# Editing (Phase 2)
# ---------------------------------------------------------------------------
MAX_UNDO_STEPS = 20
MAX_UNDO_MB = 256

# Annotation colours as RGB floats in the 0-1 range that PyMuPDF expects.
ANNOT_COLORS = {
    "yellow": (1.0, 0.92, 0.23),
    "green": (0.55, 0.86, 0.42),
    "blue": (0.40, 0.70, 1.0),
    "pink": (1.0, 0.55, 0.75),
    "orange": (1.0, 0.70, 0.28),
    "red": (0.94, 0.33, 0.31),
    "black": (0.0, 0.0, 0.0),
    "white": (1.0, 1.0, 1.0),
}
DEFAULT_HIGHLIGHT_COLOR = "yellow"
DEFAULT_INK_COLOR = "red"
DEFAULT_TEXT_COLOR = "black"
DEFAULT_INK_WIDTH = 2.0
DEFAULT_FONT = "helv"
DEFAULT_FONT_SIZE = 12.0
# Base-14 fonts are always available without embedding.
STANDARD_FONTS = {
    "helv": "Helvetica",
    "hebo": "Helvetica Bold",
    "heit": "Helvetica Italic",
    "tiro": "Times Roman",
    "tibo": "Times Bold",
    "tiit": "Times Italic",
    "cour": "Courier",
    "cobo": "Courier Bold",
}
# Replacement text is shrunk in these steps until it fits its box.
TEXT_FIT_STEPS = (1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.6, 0.5)
MIN_FONT_SIZE = 4.0
IMAGE_EXPORT_FORMATS = ["PNG", "JPEG"]
IMAGE_EXPORT_FILTER = "PNG Image (*.png);;JPEG Image (*.jpg)"
IMAGE_IMPORT_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*.*)"
EXPORT_DPI_CHOICES = [72, 150, 300, 600]
DEFAULT_EXPORT_DPI = 150
# A4 at 600 dpi is a 33-megapixel image per sheet; 300 is the sweet spot.
PRINT_MAX_DPI = 300

# ---------------------------------------------------------------------------
# Editing messages
# ---------------------------------------------------------------------------
MSG_NO_SELECTION = "Drag across the page to select an area first."
MSG_ANNOT_ADDED = "Added {kind} on page {page}"
MSG_TEXT_REPLACED = "Replaced text on page {page}"
MSG_TEXT_NOT_FOUND = "No text found in the selected area."
MSG_TEXT_TOO_LONG = (
    "The replacement text will not fit in that space, even at the smallest "
    "readable size. Try shorter text or select a larger area."
)
MSG_FONT_SUBSTITUTED = (
    "The original font ({font}) is not embedded, so {substitute} was used. "
    "The replaced text may not match the surrounding text exactly."
)
MSG_NO_FORM = "This PDF does not contain any fillable form fields."
MSG_FORM_SAVED = "Updated {count} form field(s)"
MSG_REDACTED = "Redacted {count} area(s) on page {page}"
MSG_PAGES_REORDERED = "Page order updated"
MSG_PAGE_INSERTED = "Inserted a blank page at position {page}"
MSG_PAGE_DUPLICATED = "Duplicated page {page}"
MSG_PAGES_IMPORTED = "Imported {count} page(s) from {filename}"
MSG_PRINT_SENT = "Sent {pages} page(s) to {printer}"
MSG_PRINT_CANCELLED = "Printing cancelled"
MSG_NO_PRINTER = "No printer is available on this system."
MSG_EXPORTED = "Exported {count} image(s) to {folder}"
MSG_NOTHING_TO_UNDO = "Nothing to undo"
MSG_NOTHING_TO_REDO = "Nothing to redo"
MSG_UNDONE = "Undo applied"
MSG_REDONE = "Redo applied"
MSG_SEARCH_NO_RESULTS = "No results found for '{query}'"
MSG_SEARCH_FOUND = "Found {count} result(s) for '{query}'"
MSG_OCR_COMPLETE = "OCR complete: {chars} characters extracted"
MSG_OCR_NOT_AVAILABLE = "OCR is not available. Install tesseract-ocr or easyocr."
MSG_TEXT_EXTRACTED = "Extracted {chars} characters from {pages} page(s)"
MSG_PASSWORD_SET = "Password protection applied"
MSG_PASSWORD_REMOVED = "Password protection removed"
MSG_BATCH_COMPLETE = "Batch operation complete: {success}/{total} files processed"
