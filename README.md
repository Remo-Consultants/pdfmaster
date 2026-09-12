# PDFMaster

**A professional PDF viewer and editor for Windows (0.4.0)**

PDFMaster is a desktop application for opening, reading, annotating, and
editing PDF files. It is built with Python 3.10+, PySide6 (Qt 6) for the
user interface, and PyMuPDF for high-speed page rendering and edits.

Version 0.4.0 focuses on a commercial-style workspace: a ribbon of
labelled tool groups, multi-document tabs, continuous scrolling, and a
system light/dark theme.

---

## Table of contents

1. [Why PDFMaster](#why-pdfmaster)
2. [Features](#features)
3. [Screenshots and UI tour](#screenshots-and-ui-tour)
4. [System requirements](#system-requirements)
5. [Technology stack](#technology-stack)
6. [Installation](#installation)
7. [Running the application](#running-the-application)
8. [Usage guide](#usage-guide)
9. [Keyboard shortcuts](#keyboard-shortcuts)
10. [Project structure](#project-structure)
11. [Architecture](#architecture)
12. [Configuration and data files](#configuration-and-data-files)
13. [Logging](#logging)
14. [Error handling](#error-handling)
15. [Development setup](#development-setup)
16. [Testing](#testing)
17. [Packaging](#packaging)
18. [Performance notes](#performance-notes)
19. [Security notes](#security-notes)
20. [Troubleshooting](#troubleshooting)
21. [FAQ](#faq)
22. [Contributing](#contributing)
23. [Roadmap](#roadmap)
24. [Changelog](#changelog)
25. [License](#license)
26. [Credits](#credits)

---

## Why PDFMaster

Most people open PDFs dozens of times a day. They need a viewer that:

- Starts quickly
- Renders pages clearly at any zoom
- Lets them rotate a scanned page
- Lets them drop a blank or duplicate page
- Saves the result without uploading the file to a website

PDFMaster is designed for that workflow. Files stay on your computer.
There is no account, no telemetry, and no cloud dependency.

The MVP does **not** try to be Adobe Acrobat. It does the core loop well
so later features have a stable base: a `Document` model, a Qt viewer
widget, and a main window that already owns menus, shortcuts, and a
status bar.

---

## Features

### PDF viewing (MVP)

- Open PDF files from a file dialog or the **Open Recent** menu
- Open several documents at once in a tab bar (each tab keeps its own
  zoom, page, and undo history)
- Continuous scrolling through the whole document on a soft-shadowed
  page canvas
- Page counter showing `current / total`
- Jump to a page with the ribbon page box or the thumbnail sidebar
- Next / previous page navigation
- Pages render on a background thread, so the window stays responsive
  even on large engineering drawings
- Damaged PDFs are repaired for viewing with a warning that content may
  be missing

### Zoom controls (MVP)

- Zoom in and out in 10% steps
- Zoom slider from 25% to 400%
- Fit to page width
- Fit entire page in the window
- Reset to 100% zoom and 0° rotation
- Live zoom percentage in the ribbon
- Ctrl + mouse wheel zoom

### Page operations (MVP)

- Delete the current page (blocked if it is the last page)
- Rotate clockwise 90°
- Rotate counterclockwise 90°
- Reset rotation to 0°
- Save in place or Save As

### User interface

- Native desktop window via Qt 6 / PySide6
- Menu bar: File, Edit, Tools, View, Help
- Ribbon with **Home**, **Markup**, **Edit**, **Organize**, and **View**
  tabs and labelled groups (File, Zoom, Text Markup, …)
- Multi-document tab bar with close buttons and unsaved-change prompts
- Page thumbnail sidebar for navigation (`F9`)
- Properties panel listing document facts and the markup on the current
  page, with delete (`F10`)
- Continuous scrolling through the whole document
- Light or dark theme, following the Windows setting automatically
- HiDPI SVG icons that stay sharp on scaled displays
- Status bar for the current operation
- Window title shows the file name
- Unsaved-change prompt on close or when closing a tab

### File operations (MVP)

- PDF header validation (`%PDF-` found within the first kilobyte, as the
  spec permits leading bytes)
- Friendly errors for missing, corrupt, or encrypted files
- Atomic overwrite: a failed save never loses your edits or leaves a
  partial file behind
- Save As adds a missing `.pdf` extension automatically
- Recent-file tracking under `~/.pdfmaster/`
- Safe document close and resource cleanup

### Annotation and markup (Phase 2)

- Highlight, underline, strikeout, and squiggly markup by dragging across
  text; words are selected when at least half of them fall in the drag
- Sticky notes attached to a clicked point
- Freehand pen drawing and rectangle outlines
- Eight markup colours, chosen from the Markup ribbon
- Click-to-delete for individual markup, or clear a whole page
- Flatten, which bakes markup and form values into the page permanently

### Content editing (Phase 2)

- Edit existing text: drag over a line, see what is there, and rewrite it
- Find and replace across the current page or the whole document
- Add new text boxes in any of the eight standard fonts
- Place images, logos, and scanned signatures
- Erase (white out) an area, leaving the rest of the page untouched
- Automatic font substitution and size fitting, with a plain-language
  report when either was needed

### Page organisation (Phase 2)

- Reorder pages with move up/down
- Insert blank pages that match the surrounding page size
- Duplicate, delete, and rotate one or many pages at once
- Import page ranges from another PDF into the open document

### Forms and redaction (Phase 2)

- Detect AcroForm fields and fill text boxes, checkboxes, and dropdowns
- Validation against a dropdown's allowed options, and read-only fields
  are respected
- Redaction that genuinely deletes content rather than covering it, with
  a confirmation showing exactly what will be destroyed

### Printing and export (Phase 2)

- System print dialog with page ranges, current page, copies, and collation
- Print preview backed by the same rendering path as the real job
- Automatic landscape/portrait paper matching and fit-to-paper scaling
- Export pages as PNG or JPEG at 72–600 dpi, with a page-range selector

### Undo and redo (Phase 2)

- Every edit is undoable via `Ctrl+Z` / `Ctrl+Y`
- History is bounded to 20 steps or 256 MB, whichever comes first
- Opening another document clears the history

---

## Screenshots and UI tour

When you launch PDFMaster you see:

1. **Menu bar** at the top (File, Edit, Tools, View, Help)
2. **Ribbon** with Home / Markup / Edit / Organize / View tabs. Each tab
   has labelled groups of commands (File, Zoom, Text Markup, …)
3. **Document tabs** under the ribbon — one tab per open PDF
4. **Page sidebar** on the left, showing a thumbnail per page
5. **Viewer** in the middle, scrolling continuously through the document
6. **Properties panel** on the right (hidden until you press `F10`)
7. **Status bar** at the bottom

After you open a file:

- The window title becomes `filename.pdf — PDFMaster`
- The spin box shows the current page and the label after it shows `/ N`
- The zoom label shows the current percentage
- The sidebar highlights the page you are reading, and clicking a
  thumbnail jumps to that page

Pages are centred on a grey canvas with a drop shadow, stacked
vertically with a gap between them. Only the pages near the viewport are
rasterized, so a 500-page file opens as quickly as a 5-page one. Fit
Width and Fit Page recalculate the scale from the current viewport size,
so resizing the window and then choosing Fit Page again is expected.

### Theme

PDFMaster reads the Windows light/dark preference at startup and follows
it live if you change it. Ribbon icons are SVG silhouettes rasterised at
the screen's pixel density, so they stay sharp on HiDPI displays and
recolour with the theme.

---

## System requirements

| Item | Minimum | Recommended |
| --- | --- | --- |
| Operating system | Windows 7+ (64-bit) | Windows 10 / 11 |
| Python | 3.10 | 3.11 or 3.12 |
| RAM | 4 GB | 8 GB+ |
| Display | 1280 × 720 | 1920 × 1080 or higher |
| Disk | 200 MB for the app and libraries | SSD |

Linux and macOS are supported at the library level (PySide6 and PyMuPDF
are cross-platform). The MVP is tested primarily on Windows. On Linux
you may need extra Qt platform packages from your distro.

---

## Technology stack

| Layer | Library | Role |
| --- | --- | --- |
| GUI | PySide6 >= 6.6.0 | Windows, menus, widgets, shortcuts |
| Rendering | PyMuPDF (fitz) >= 1.24.0 | Fast C-based page rasterization and text extract |
| Structure | PyPDF >= 4.0.0 | Merge / split helpers in `PDFHandler` |
| Images | Pillow >= 10.0.0 | PIL images between renderer and Qt |
| Crypto (future) | cryptography >= 42.0.0 | Reserved for Phase 2 security features |
| Tests | pytest, pytest-cov | Automated checks |

PyMuPDF is typically 10–50× faster than pure-Python PDF renderers
because page drawing runs in C. Rendering happens on a `QThreadPool`
worker; the worker produces a `QImage` from the raw RGB buffer and the
GUI thread turns it into a `QPixmap`. Recent `(page, zoom)` renders are
cached in memory under a byte budget.

Because PyMuPDF is not thread-safe, every access to the underlying
handle is serialized through a lock inside `Document`.

---

## Installation

### Windows

1. Install Python 3.10 or later from https://www.python.org/downloads/
   - Enable **Add python.exe to PATH**
2. Open **Command Prompt** or **PowerShell**
3. Go to the project folder:

```bat
cd pdfmaster_project
```

4. Create and activate a virtual environment:

```bat
python -m venv venv
venv\Scripts\activate
```

5. Upgrade pip and install dependencies:

```bat
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Optional: install the package itself so the `pdfmaster` command works:

```bat
pip install -e .
```

### Linux

```bash
cd pdfmaster_project
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Debian/Ubuntu users may also need:

```bash
sudo apt-get install -y libgl1 libxkbcommon0 libegl1
```

### macOS

```bash
cd pdfmaster_project
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If `PySide6` fails to install, confirm you are using a 64-bit CPython
build (not a Homebrew python that is too old).

### Verify the install

```bash
python -c "import PySide6, fitz, pypdf, PIL; print('ok')"
```

You should see `ok`. If an import fails, re-run `pip install -r
requirements.txt` and read the pip error (compiler missing, wrong
Python, or no network).

---

## Running the application

From the project root, with the virtual environment active:

```bash
python -m src.main
```

Or, after `pip install -e .`:

```bash
pdfmaster
```

You can also run the file directly:

```bash
python src/main.py
```

`src/main.py` inserts the project root onto `sys.path` so both styles
work.

The first launch creates:

- `~/.pdfmaster/`
- `~/.pdfmaster/logs/pdfmaster.log`
- `~/.pdfmaster/recent_files.txt` (after you open a file)

On Windows, `~` is your user profile, for example
`C:\Users\YourName\.pdfmaster\`.

---

## Usage guide

### Open a PDF

1. Choose **File → Open...** or press `Ctrl+O`
2. Select a `.pdf` file
3. The first page appears in the viewer

Invalid files (wrong extension, missing `%PDF-` header, empty path) are
rejected with a dialog. Password-protected PDFs are refused in the MVP.

### Navigate pages

- Toolbar **Prev** / **Next**
- Type a number in the page spin box and press Enter
- `Page Up` / `Page Down`
- `Ctrl+Home` first page, `Ctrl+End` last page
- **View → Navigate** menu

The status bar briefly reports the action.

### Zoom

- Toolbar **+** / **−**
- Drag the zoom slider
- **View → Zoom In / Zoom Out**
- `Ctrl++` (or `Ctrl+=`) and `Ctrl+-`
- Hold **Ctrl** and scroll the mouse wheel
- **Fit Width** scales the page to the viewer width
- **Fit Page** scales the page so both width and height fit
- **Reset** or `Ctrl+0` restores 100% zoom and 0° rotation

Zoom is limited to 25%–400%.

### Rotate a page

- **View → Rotate Clockwise** (`Ctrl+R`)
- **View → Rotate Counterclockwise** (`Ctrl+Shift+R`)

Rotation is stored on the page (0°, 90°, 180°, 270°) and is written when
you save.

### Delete a page

1. Go to the page you want to remove
2. **Edit → Delete Page** or press `Delete`
3. Confirm the dialog

You cannot delete the last remaining page. The change is in memory until
you save.

### Save

- **File → Save** (`Ctrl+S`) writes back to the original path
- **File → Save As...** writes a new file (default suffix `_edited`)

If the document was modified, closing the window or opening another file
asks whether to save, discard, or cancel.

### Recent files

**File → Open Recent** lists the last 10 successfully opened PDFs.
Missing files are skipped the next time the list is loaded.

---

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+O` | Open PDF |
| `Ctrl+S` | Save |
| `Ctrl+P` | Print |
| `Ctrl+Shift+P` | Print preview |
| `Ctrl+Shift+E` | Export pages as images |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+H` | Find and replace |
| `Ctrl+Shift+O` | Organize pages |
| `Ctrl+Shift+F` | Fill form |
| `1`–`9` | Select an editing tool, in toolbar order |
| `F9` | Show or hide the page thumbnails |
| `F10` | Show or hide the properties panel |
| `Ctrl+Q` | Exit |
| `Ctrl+0` | Reset zoom and rotation |
| `Ctrl++` / `Ctrl+=` | Zoom in |
| `Ctrl+-` | Zoom out |
| `Ctrl+1` | Fit width |
| `Ctrl+2` | Fit page |
| `Page Up` | Previous page |
| `Page Down` | Next page |
| `Ctrl+Home` | First page |
| `Ctrl+End` | Last page |
| `Ctrl+R` | Rotate clockwise |
| `Ctrl+Shift+R` | Rotate counterclockwise |
| `Delete` | Delete current page |

Shortcuts are defined in `src/constants.py` (`SHORTCUTS`) so you can
change them in one place.

---

## Project structure

```
pdfmaster_project/
├── src/
│   ├── __init__.py
│   ├── main.py                 # QApplication entry point
│   ├── constants.py            # Names, sizes, zoom, messages, shortcuts
│   ├── core/
│   │   ├── __init__.py
│   │   ├── document.py         # Document model (PyMuPDF)
│   │   ├── history.py          # Undo/redo snapshots
│   │   └── pdf_handler.py      # Merge, split, extract, info
│   ├── processors/             # Document editing
│   │   ├── __init__.py
│   │   ├── annotations.py      # Highlight, note, ink, shapes
│   │   ├── content.py          # Replace text, add text/images, erase
│   │   ├── forms.py            # AcroForm reading and filling
│   │   ├── page_ops.py         # Reorder, insert, duplicate, import
│   │   └── redaction.py        # Permanent content removal
│   ├── services/
│   │   ├── __init__.py
│   │   └── print_service.py    # Printing, preview, image export
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py      # Menus, ribbon, docks, shortcuts
│   │   ├── edit_controller.py  # Tool → document operations
│   │   ├── tools.py            # ToolMode enum and labels
│   │   ├── icons.py            # SVG ribbon / tool icons
│   │   ├── theme.py            # Light / dark palettes
│   │   ├── dialogs/
│   │   │   ├── __init__.py
│   │   │   ├── export_dialog.py
│   │   │   ├── form_dialog.py
│   │   │   ├── page_organizer.py
│   │   │   └── text_dialogs.py
│   │   └── widgets/
│   │       ├── __init__.py
│   │       ├── document_viewer.py   # Continuous scrolling canvas
│   │       ├── document_tabs.py     # Multi-document tab bar
│   │       ├── ribbon.py            # Ribbon tabs and groups
│   │       ├── info_panel.py        # Properties / markup list
│   │       └── thumbnail_panel.py   # Page sidebar
│   └── utils/
│       ├── __init__.py
│       ├── exceptions.py
│       ├── file_handler.py
│       ├── image_utils.py      # PIL to QImage conversion
│       └── logger.py
├── tests/                      # 238 tests
│   ├── conftest.py
│   ├── test_annotations.py
│   ├── test_content.py
│   ├── test_document.py
│   ├── test_document_save.py
│   ├── test_edit_ui.py
│   ├── test_exceptions.py
│   ├── test_file_handler.py
│   ├── test_forms_redaction.py
│   ├── test_history.py
│   ├── test_page_ops.py
│   ├── test_pdf_handler.py
│   ├── test_print_service.py
│   ├── test_ui.py
│   └── test_ui_layout.py       # Toolbar, panels, theme, scrolling
├── resources/icons/            # App logo (pdfmaster.png / .ico)
├── README.md
├── QUICKSTART.md
├── requirements.txt
├── setup.py
├── LICENSE
└── .gitignore
```

### What each module does

**`src/main.py`**  
Sets up logging, creates `QApplication` and `MainWindow`, runs the Qt
event loop, and returns the process exit code.

**`src/constants.py`**  
Single place for window size, zoom limits, file filters, status
messages, paths under `~/.pdfmaster`, and keyboard shortcuts.

**`src/core/document.py`**  
Owns a `fitz.Document`. Loads, validates, renders, rotates, deletes,
extracts, saves, and closes. Supports `with Document(path) as doc:`.

**`src/core/pdf_handler.py`**  
Static helpers for workflows that may involve more than one file: merge,
split by ranges, extract a page list, rotate a page list, and summarize
PDF info.

**`src/core/history.py`**  
Bounded undo/redo built on full document snapshots, because PyMuPDF has
no native undo. Serializing is only a few milliseconds, but a snapshot
is the whole PDF, so the stack is capped by depth and by total bytes.

**`src/processors/`**  
One module per editing concern: `annotations` for markup, `content` for
text and image changes, `page_ops` for structure, `forms` for AcroForm
fields, and `redaction` for permanent removal. Every one of them mutates
the PDF through `Document.transaction()`, so edits are serialized against
background rendering. All coordinates are unrotated PDF points.

**`src/services/print_service.py`**  
Rasterizes pages onto a `QPrinter`, resolves the dialog's page-range
settings, matches paper orientation to the page, and exports images.
Render resolution is capped at 300 dpi.

**`src/ui/widgets/document_viewer.py`**  
A `QScrollArea` that lays every page out in one tall canvas and paints
only the pages touching the viewport, so cost tracks what is on screen
rather than the page count. It dispatches renders to a worker thread,
caches the results under a memory budget, discards superseded requests,
and emits `page_changed`, `zoom_changed`, `render_finished`, and
`render_failed`. It also handles tool input: it paints live drag
feedback and converts mouse positions into a page index plus PDF
coordinates, going through that page's derotation matrix, which is what
makes clicks land correctly on a rotated page. Because a drag can land
on any visible page, the editing signals carry the page index rather
than relying on which page is "current".

**`src/ui/widgets/thumbnail_panel.py`**  
The page sidebar. Thumbnails render on a background thread at a small
fixed width and only for rows near the viewport. Rebuilds are guarded so
that repopulating the list cannot emit a selection change and scroll the
viewer to an unrelated page.

**`src/ui/widgets/info_panel.py`**  
Document properties plus the markup on the current page, with a delete
button. Every read is defensive: a failure here logs and shows a dash
rather than breaking the window.

**`src/ui/theme.py`**  
One table of colours per scheme, turned into a `QPalette` and a
stylesheet. `detect_scheme()` reads the OS preference, and the window
subscribes to `colorSchemeChanged` so the theme follows Windows live.

**`src/ui/icons.py`**  
SVG silhouettes for ribbon and tool icons, rasterised at the screen's
device pixel density so they stay sharp on HiDPI displays and recolour
with the active theme.

**`src/ui/edit_controller.py`**  
Turns a finished drag or click into an edit. Holds the undo history,
snapshots before each change, opens the right dialog, refreshes the
viewer, and translates processor exceptions into readable messages.

**`src/ui/main_window.py`**  
Wires the viewer to menus, the ribbon, docks, dialogs, and shortcuts.
Shows user-facing errors.

**`src/utils/exceptions.py`**  
`PDFMasterException` and specific subclasses for load, render, page,
file, and validation failures.

**`src/utils/logger.py`**  
Console + rotating file log under `~/.pdfmaster/logs/`.

**`src/utils/file_handler.py`**  
Exists checks, PDF magic bytes, sizes, output names, safe delete,
recent-file list.

---

## Architecture

PDFMaster uses a simple three-layer split:

```
┌─────────────────────────────────────────┐
│  UI  (PySide6)                          │
│  MainWindow  →  DocumentViewer          │
└─────────────────┬───────────────────────┘
                  │ uses
┌─────────────────▼───────────────────────┐
│  Core                                   │
│  Document  ←  PDFHandler                │
└─────────────────┬───────────────────────┘
                  │ uses
┌─────────────────▼───────────────────────┐
│  Utils                                  │
│  FileHandler, logger, exceptions        │
└─────────────────────────────────────────┘
```

Rules of thumb:

- The UI never talks to PyMuPDF or PyPDF directly.
- `Document` is the only object that holds an open `fitz` handle.
- Failures become custom exceptions, then a `QMessageBox` plus a log
  line.
- File paths are validated before any PDF library is invoked.

This keeps Phase 2 features (processors and services) from leaking into
the window class.

---

## Configuration and data files

PDFMaster does not ship a large settings dialog in the MVP. Defaults
live in `src/constants.py`:

| Constant | Default | Meaning |
| --- | --- | --- |
| `WINDOW_WIDTH` / `WINDOW_HEIGHT` | 1400 × 900 | First-launch size |
| `WINDOW_MIN_WIDTH` / `WINDOW_MIN_HEIGHT` | 800 × 600 | Smallest window |
| `ZOOM_MIN` / `ZOOM_MAX` | 25 / 400 | Percent limits |
| `ZOOM_STEP` | 10 | Button increment |
| `VIEWER_BACKGROUND` | `#1e1e1e` | Dark canvas |
| `MAX_RECENT_FILES` | 10 | Recent menu length |
| `MAX_FILE_SIZE_MB` | 500 | Soft open limit |
| `MAX_RENDER_CACHE` | 12 | Cached page pixmaps |
| `MAX_RENDER_CACHE_MB` | 192 | Memory ceiling for that cache |
| `PDF_HEADER_SEARCH_BYTES` | 1024 | How far to search for `%PDF-` |

User data:

| Path | Purpose |
| --- | --- |
| `~/.pdfmaster/logs/pdfmaster.log` | Rotating application log |
| `~/.pdfmaster/recent_files.txt` | One absolute path per line |

---

## Logging

`setup_logging()` in `src/utils/logger.py` attaches:

- A stderr stream handler
- A rotating file handler (2 MB × 5 backups)

Format:

```
2026-09-11 15:30:00 - pdfmaster.src.core.document - INFO - Loaded PDF 'manual.pdf' (12 pages, 1.40 MB)
```

Levels:

- **DEBUG** — render sizes, cache, path checks
- **INFO** — open, save, rotate, delete, startup/shutdown
- **WARNING** — recoverable problems (incremental save fallback)
- **ERROR** — failures shown to the user

Call `get_logger(__name__)` in new modules so records stay under the
`pdfmaster` namespace.

---

## Error handling

Never swallow errors. The hierarchy is:

- `PDFMasterException` — catch-all for app errors
- `PDFLoadError` — open / parse / encryption
- `PDFRenderError` — page rasterization
- `PageOperationError` — rotate, delete, extract, save
- `FileOperationError` — filesystem
- `ValidationError` — bad paths, non-PDF files, empty ranges

The main window maps these to short dialogs. The viewer shows a text
placeholder if a single page fails to render instead of crashing.

---

## Development setup

```bash
cd pdfmaster_project
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
pip install -e .
```

Suggested workflow:

1. Change code under `src/`
2. Run `python -m src.main` and click through the flow you changed
3. Run `pytest`
4. Check `~/.pdfmaster/logs/pdfmaster.log` if something failed silently
   in the UI

Code style:

- PEP 8
- Type hints on public methods
- Docstrings on classes and functions
- Meaningful names (`page_num` is 0-based in core, 1-based in the UI)

---

## Testing

```bash
pytest
pytest -v
pytest --cov=src --cov-report=term-missing
```

50 tests, ~80% line coverage. Included suites:

- `tests/test_exceptions.py` — exception hierarchy
- `tests/test_file_handler.py` — validation, sizes, recent files
- `tests/test_document.py` — open, text, rotate, delete, extract,
  encrypted-file rejection
- `tests/test_document_save.py` — save, Save As, atomic overwrite, and
  recovery when the target file is locked
- `tests/test_pdf_handler.py` — merge, split, extract, rotate, info
- `tests/test_ui.py` — the window driven headlessly through `pytest-qt`:
  navigation, zoom, fit modes, rotation, delete, Save As, cache budget

GUI tests run offscreen (`QT_QPA_PLATFORM=offscreen`, set automatically
in `tests/conftest.py`), so they work over SSH and in CI. Because
rendering is asynchronous, UI tests wait on the viewer's
`render_finished` signal rather than sleeping.

---

## Packaging

`setup.py` exposes:

```
pdfmaster=src.main:main
```

Editable install:

```bash
pip install -e .
```

A frozen Windows `.exe` (PyInstaller / cx_Freeze) is **not** part of
the MVP. When you add it, keep the `src` layout and bundle Qt plugins
explicitly.

---

## Performance notes

- Pages are rendered lazily. Opening a 500-page PDF does not rasterize
  all pages.
- Rendering runs on a background thread. An A1 drawing with 4000 strokes
  at 400% zoom takes ~600 ms to rasterize but blocks the GUI thread for
  roughly 30 ms, so the window keeps repainting and responding.
- Only one render runs at a time, and superseded requests are discarded.
  Dragging the zoom slider does not queue up dozens of stale renders.
- The previous page stays on screen while the next render is in flight,
  which avoids flicker.
- PIL images are converted to `QImage` from the raw RGB buffer. An
  earlier PNG encode/decode round trip was ~3.7× slower for no benefit.
- The cache is bounded by both entry count (`MAX_RENDER_CACHE`) and total
  bytes (`MAX_RENDER_CACHE_MB`). One A4 page at 400% is about 30 MB, so
  the byte budget is what actually limits memory.
- Fit Width / Fit Page use the page size in PDF points (72 DPI at 100%).
  `Document.get_page_size` already reports rotated dimensions, so
  callers must not swap width and height again.

---

## Security notes

- Every open path is checked for existence and a `%PDF-` header within
  the first kilobyte (the spec allows leading bytes, so requiring the
  header at offset zero rejected legitimate files).
- Encrypted PDFs are not unlocked in the MVP; they raise `PDFLoadError`.
- Paths are resolved with `pathlib` (`expanduser` + `resolve`).
- The app never sends files to a network service.
- `cryptography` is installed for a future encryption/decryption
  feature and is unused in MVP code paths.

Do not open PDFs from untrusted sources in any viewer if you are unsure
of the file. PDF is a complex format.

---

## Troubleshooting

### `python` is not recognized

Python is not on PATH. Reinstall Python and tick **Add to PATH**, or
call `py -3` on Windows.

### `No module named PySide6` / `fitz` / `pypdf`

The virtual environment is missing or inactive. Activate `venv` and run
`pip install -r requirements.txt` again.

### Application window never appears

On Linux, missing OpenGL / xkb libraries are a common cause. Install
the distro packages listed in the Linux install section. On Windows,
update GPU drivers if Qt fails to create a window.

### "The selected file is not a valid PDF"

The file does not start with `%PDF-`. It may be an HTML download, a
renamed Word file, or a truncated copy.

### "This PDF is password-protected"

The MVP does not prompt for a password. Decrypt a copy in another tool
or wait for Phase 2 security features.

### Pages look blurry

Zoom in, or use Fit Width on a high-DPI screen. Rendering is raster, so
100% is 72 DPI relative to PDF points.

### Save fails

The file is probably open in another program (a browser preview or
another PDF reader), or the folder is read-only. PDFMaster detects this
before touching your original file, so nothing is lost: the error dialog
tells you to use **Save As** to another directory, and your edits are
still loaded in the window.

### Delete / rotate did not persist

Those edits stay in memory until you save.

### Log file is missing

Launch at least once. The logger creates `~/.pdfmaster/logs/` on
startup.

### Tests fail with import errors

Run pytest from `pdfmaster_project` so `tests/conftest.py` can put the
project root on `sys.path`.

### High memory use

Close other apps, zoom out, or split a huge PDF with `PDFHandler`
before viewing.

---

## FAQ

**Does PDFMaster edit text inside the page?**  
Not in the MVP. You can rotate and delete pages, not change sentences.

**Can it merge or split from the GUI?**  
Not yet. `PDFHandler.merge_documents` and `split_document` exist for
scripts and for Phase 2 UI.

**Where are my files stored?**  
Wherever you opened them. PDFMaster does not copy your PDFs into
`~/.pdfmaster/` except for the recent-file list (paths only) and logs.

**Is OneDrive / Dropbox OK?**  
Yes for viewing. For save, wait until the cloud client has finished
syncing, or save a local copy.

**Why PySide6 instead of Tkinter or web tech?**  
Qt gives native menus, shortcuts, and a scroll area that behaves like a
desktop viewer. PySide6 is the official LGPL Qt-for-Python binding.

**Why both PyMuPDF and PyPDF?**  
PyMuPDF is excellent at rendering. PyPDF is convenient for some
page-assembly tasks. The viewer path uses PyMuPDF.

**Can I change the dark background?**  
Edit `VIEWER_BACKGROUND` in `src/constants.py`.

---

## Contributing

This is an MVP. Useful contributions:

1. Bug reports with a sample PDF (if you are allowed to share it)
2. Tests around `Document` and `FileHandler`
3. Accessibility (keyboard focus, high-contrast)
4. Phase 2 features behind new modules, not dumped into `MainWindow`

Please:

- Follow PEP 8 and existing naming
- Add or update tests
- Do not commit `venv/`, logs, or personal PDFs
- Keep secrets out of the repo

Suggested branch naming: `fix/save-overwrite`, `feat/thumbnails`.

---

## Roadmap

### Phase 2 (shipped in 0.2.0)

- Annotations: highlight, underline, strikeout, notes, pen, shapes
- Content editing: replace existing text, add text, add images, erase
- Page organisation: reorder, insert, duplicate, delete, import
- Form filling and true redaction
- Printing with preview, page ranges, and orientation matching
- Image export (PNG, JPEG) at selectable dpi
- Undo and redo

### Phase 3 (shipped in 0.5.0)

- Text extraction panel and copy-to-clipboard
- OCR for scanned pages (tesseract and easyocr backends)
- Password set / remove with AES-256 encryption
- Batch folder processing and compression presets
- Bookmarks / outline in the sidebar
- Document-wide search
- Installer / Start Menu shortcut (PyInstaller + NSIS)

### Phase 4 (ideas)

- Digital signatures with certificate support
- Cloud storage integration (OneDrive, Google Drive, Dropbox)
- PDF/A compliance validation and conversion
- Watermarks and stamps
- Document comparison / diff view
- Advanced OCR with PDF/A output
- Multi-language spell check
- Accessibility features (screen reader support)

---

## Changelog

### 0.5.0 — 2026-09-12

Phase 3: search, OCR, security, and batch processing.

- **Added:** Document-wide search (`Ctrl+F`) with case-insensitive and
  whole-word matching, result navigation, and context preview.
- **Added:** OCR support for scanned pages using tesseract or easyocr.
  Extracts text from images with configurable language and DPI settings.
- **Added:** Text extraction panel (`Ctrl+T`) with page range selection and
  copy-to-clipboard functionality.
- **Added:** Bookmarks/outline panel showing the document's table of
  contents as a clickable tree for navigation.
- **Added:** Password protection — set user/owner passwords with
  configurable permissions (print, copy, modify, annotate) and AES-256
  encryption, or remove existing passwords.
- **Added:** Security info dialog showing encryption status and current
  permissions.
- **Added:** Batch processing dialog for folder-wide operations:
  compress PDFs with presets (screen/ebook/printer/prepress), extract
  text to TXT files, or convert pages to images.
- **Added:** Compression presets with configurable image quality, DPI,
  and garbage collection settings.
- **Added:** PyInstaller spec file and NSIS installer script for
  creating Windows distributions with Start Menu shortcuts.
- **Changed:** Package version bumped to 0.5.0.
- **Tests:** 238 → 259 tests, 85% → 86% coverage.

### 0.4.0 — 2026-09-12

Commercial-style workspace.

- **Added:** Ribbon with Home, Markup, Edit, Organize, and View tabs and
  labelled command groups.
- **Added:** Multi-document tab bar — open several PDFs at once; each tab
  keeps its own viewer state and undo history.
- **Added:** Soft multi-layer page shadows for a clearer paper look.
- **Changed:** Icons are SVG-based and rasterised for HiDPI, so they stay
  sharp on scaled Windows displays.
- **Changed:** Ribbon captions use short labels so text no longer clips
  or overlaps icons; disabled labels stay readable in dark theme.
- **Changed:** Package version bumped to 0.4.0.

### 0.3.0 — 2026-09-11

Interface rework.

- **Fixed:** Most editing tools were unreachable from the toolbar. The
  tools toolbar was placed on the same row as the main toolbar, and its
  thirteen text labels needed 1,943 px, so both rows were truncated
  behind an overflow chevron at every realistic window size. The tools
  are now icons on their own row, needing 637 px. Covered by a test that
  fails if either toolbar overflows.
- **Fixed:** After any edit, the viewer jumped to a different page.
  Rebuilding the thumbnail list emitted `currentRowChanged`, which was
  treated as the user clicking a thumbnail. The rebuild is now guarded.
- **Added:** Page thumbnail sidebar (`F9`) with background rendering and
  click-to-navigate.
- **Added:** Properties panel (`F10`) showing document facts and the
  markup on the current page, with delete.
- **Added:** Continuous scrolling. All pages are laid out in one canvas
  and only those near the viewport are rasterized, so page count no
  longer drives cost.
- **Added:** Light and dark themes that follow the Windows setting and
  switch live, plus toolbar icons drawn in code so they recolour with
  the theme and need no image assets.
- **Changed:** The toolbar is icon-only. The nine common tools are on
  the toolbar; all thirteen remain in the Tools menu, and number keys
  `1`–`9` follow toolbar order.
- **Changed:** Editing signals now carry the page index, because in
  continuous mode a drag can land on a page other than the current one.
- **Changed:** Minimum window size is 1024x640, up from 800x600, since
  the toolbars need about 890 px and the sidebar another 170.
- **Tests:** 214 → 238 tests, 83% → 85% coverage.

### 0.2.0 — 2026-09-11

Phase 2: editing and printing.

- **Added:** Annotation tools — highlight, underline, strikeout,
  squiggly, sticky notes, freehand pen, and rectangles, in eight
  colours, with click-to-delete and per-page clearing.
- **Added:** Text editing. Drag over existing text to rewrite it. The
  original glyphs are redacted and the new text is drawn in place, with
  the box expanded into free space before any font shrinking, and a
  report when a font was substituted or the size reduced.
- **Added:** Find and replace across one page or the whole document.
- **Added:** New text boxes, image and signature placement, and an
  erase tool.
- **Added:** Page organiser — reorder, insert blank, duplicate, delete,
  rotate, and import pages from another PDF.
- **Added:** Form filling for text, checkbox, and dropdown fields, with
  option validation and read-only handling.
- **Added:** Redaction that deletes content rather than covering it,
  behind a confirmation that shows what will be destroyed.
- **Added:** Printing with the system dialog, print preview, page
  ranges, fit-to-paper, and automatic landscape/portrait matching.
  Render resolution is capped at 300 dpi, since A4 at 600 dpi is a
  33-megapixel image per sheet.
- **Added:** Image export as PNG or JPEG at 72–600 dpi.
- **Added:** Undo and redo, bounded to 20 steps or 256 MB.
- **Added:** `Document.transaction()`, so processors mutate the PDF
  under the same lock that guards background rendering.
- **Fixed:** Clicks now map correctly to PDF coordinates on rotated
  pages, using the page's derotation matrix.
- **Changed:** `pil_to_qimage` moved to `src/utils/image_utils.py` to
  break a circular import between the print service and the UI.
- **Tests:** 50 → 204 tests, 80% → 83% coverage. Added a 60-second
  per-test timeout and an auto-cancel guard for dialogs, after an
  unattended modal hung a run indefinitely.

### 0.1.1 — 2026-09-11

Fixes and hardening found during a review of the 0.1.0 MVP.

- **Fixed:** Fit Width and Fit Page were wrong after rotating a page.
  Rotation was counted twice, so a rotated page overflowed the viewport
  by roughly 2×.
- **Fixed:** A failed overwrite (locked or read-only file) closed the
  PDF handle, left the document unusable, discarded unsaved edits, and
  leaked a temp file next to the original. Saving is now atomic with
  in-memory recovery.
- **Fixed:** Save As no longer writes extensionless files.
- **Fixed:** PDFs with bytes before the `%PDF-` header are accepted, as
  the specification allows.
- **Added:** Background rendering. The GUI thread is no longer blocked
  for the duration of a rasterization.
- **Added:** Warning when a damaged PDF had to be repaired to open.
- **Changed:** Raw-buffer image conversion instead of a PNG round trip.
- **Changed:** Render cache is bounded by memory, not just entry count.
- **Removed:** Dead viewer-level rotation state; rotation lives only on
  the document.
- **Tests:** 15 → 50 tests, 30% → 80% coverage, including headless GUI
  tests with `pytest-qt`.

### 0.1.0 — 2026-09-11

- Initial MVP release
- Open, view, zoom, fit width/page, rotate, delete, save
- Recent files, logging, custom exceptions
- Keyboard shortcuts
- Pytest coverage for file validation and document operations
- MIT license

---

## License

PDFMaster is released under the **MIT License**. See [LICENSE](LICENSE)
for the full text.

You may use, copy, modify, merge, publish, distribute, sublicense, and
sell copies of the software, provided the copyright notice and
permission notice are included.

---

## Credits

- [PySide6](https://doc.qt.io/qtforpython/) — Qt for Python
- [PyMuPDF](https://pymupdf.readthedocs.io/) — rendering and PDF I/O
- [pypdf](https://pypdf.readthedocs.io/) — PDF structure helpers
- [Pillow](https://python-pillow.org/) — image conversion
- [pytest](https://pytest.org/) — tests

PDFMaster is an independent project and is not affiliated with Adobe,
Microsoft, or the PDF Association.

---

## Support

1. Read [QUICKSTART.md](QUICKSTART.md) for a five-minute setup
2. Search [Troubleshooting](#troubleshooting) for the error text
3. Check `~/.pdfmaster/logs/pdfmaster.log`
4. Open an issue with OS, Python version, and a redacted log excerpt

Thank you for using PDFMaster.
