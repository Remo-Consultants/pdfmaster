# PDFMaster Quick Start

Get PDFMaster running in about five minutes.

**Prefer a Windows installer?** See [`INSTALL.md`](INSTALL.md) — download
Setup.exe or the portable ZIP from
[Releases](https://github.com/Remo-Consultants/pdfmaster/releases/latest),
then skip to [First steps](#first-steps).

**Product page:** https://remo-consultants.github.io/pdfmaster/

This page covers the **from-source** path for developers. If you already
have the app installed, skip to [First steps](#first-steps).

---

## What you need

- A Windows 10/11 PC
- Either the release installer/ZIP, **or** Python 3.10+ for source installs
- A sample PDF to open (any normal, non-password file)

Linux and macOS users can follow the source steps. Replace
`venv\Scripts\activate` with `source venv/bin/activate`.

---

## Fastest path — release build

1. Open https://github.com/Remo-Consultants/pdfmaster/releases/latest  
2. Download **Setup.exe** (recommended) or **win64.zip**  
3. Install or extract, launch **PDFMaster**  
4. Continue at [First steps](#first-steps)

---

## Step 1 — Install Python (source only)

1. Open https://www.python.org/downloads/
2. Download Python 3.10 or newer
3. Run the installer
4. Check **Add python.exe to PATH**
5. Finish the installer

Check it worked. Open PowerShell and type:

```powershell
python --version
```

You should see something like `Python 3.12.4`. If the command is not
found, try:

```powershell
py -3 --version
```

and use `py -3` everywhere this guide says `python`.

---

## Step 2 — Open the project folder

In PowerShell:

```powershell
cd pdfmaster
```

(Or clone first: `git clone https://github.com/Remo-Consultants/pdfmaster.git`)

If you cloned or copied the project elsewhere, `cd` to that
`pdfmaster` directory instead. You should see `src`,
`requirements.txt`, and `README.md` when you run `dir`.

---

## Step 3 — Create a virtual environment

A virtual environment is a private Python folder so PDFMaster's
libraries do not mix with other projects.

```powershell
python -m venv venv
venv\Scripts\activate
```

After activate, your prompt usually starts with `(venv)`.

If PowerShell blocks the activate script:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
venv\Scripts\activate
```

---

## Step 4 — Install libraries

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

This installs PySide6, PyMuPDF, PyPDF, Pillow, cryptography, pytest, and
pytest-qt. The first run can take a few minutes.

Sanity check:

```powershell
python -c "import PySide6, fitz, pypdf, PIL; print('PDFMaster deps OK')"
```

---

## Step 5 — Start PDFMaster

```powershell
python -m src.main
```

A window titled **PDFMaster** should open. If it does not, read
[Common problems](#common-problems).

---

## First steps

1. Press **Ctrl+O** (or File → Open)
2. Choose a PDF
3. Scroll with the mouse wheel — the document runs continuously, so you
   can read from one page into the next without clicking anything
4. Click a page in the **sidebar on the left** to jump straight to it
5. Drag the zoom slider, or hold **Ctrl** and scroll
6. Click **Fit Width**, then **Fit Page**
7. Try **View → Rotate Clockwise**
8. Press **Ctrl+F** to search the whole document
9. Open the **Bookmarks** tab on the left (next to thumbnails) if the
   PDF has an outline
10. Press **Ctrl+T** for the text extraction panel; copy what you need
11. If you rotated a page you care about, press **Ctrl+S** to save
12. Close the window with **Ctrl+Q**

That is the reading loop: open, scroll, zoom, search or extract, rotate
or delete, save.

### The window

- **Ribbon** — Home / Markup / Edit / Organize / View tabs with labelled
  groups (File, Zoom, Text Markup, …)
- **Document tabs** — one tab per open PDF; close a tab with its ×
- **Left sidebar** — thumbnails (**F9**) and a **Bookmarks** tab for
  the document outline
- **Right panel** — document details and the markup on the current page
  (**F10**), plus text extraction (**Ctrl+T**)
- **Status bar** — what just happened, and what the current tool expects

Hover any ribbon button for its name and shortcut. PDFMaster follows the
Windows light or dark setting, and changes with it straight away.

### Search, OCR, security, and batch (0.5.0)

These live under the **Tools** menu:

- **Ctrl+F** — Search Document (case / whole-word options, jump to hits)
- **Ctrl+Shift+T** — OCR Scanned Pages (needs tesseract or easyocr)
- **Ctrl+T** — Extract Text panel (page, range, or all pages → clipboard)
- **Watermark…** / **Stamp…** — diagonal text watermarks or rubber/image stamps
- **Compare Documents…** — text diff (optional visual/rendered compare)
- **PDF/A Check…** — see if the file declares PDF/A and basic findings
- **Batch Processing** — compress / extract / convert a folder of PDFs
- **Security Info** / **Set Password** / **Remove Password** / **Add Signature Field**

---

## Editing a PDF

Editing works by picking a tool, then using it on the page. Markup tools
live on the **Markup** ribbon tab; content tools on **Edit**. All
thirteen tools are also in the **Tools** menu, and the number keys
`1`–`9` select the primary tools. The status bar tells you what the
active tool expects you to do.

1. Press **2** (or Tools → Highlight) and drag across a line of text
2. Change the colour on the **Markup** tab (**Color** group) and highlight something else
3. Press **1** to go back to **Select**, so dragging stops making edits
4. Press **Ctrl+Z** to undo, **Ctrl+Y** to redo

To change words that are already in the PDF, choose **Edit Text** and
drag over them. A dialog shows what is there now and lets you rewrite
it. Two things to expect, because of how PDFs work: longer text gets
shrunk to fit the available space, and if the document's font is not
embedded, a similar standard font is substituted. PDFMaster tells you
when either happened.

Other things worth trying:

- **Sticky Note** — click anywhere and type a comment
- **Pen** — hold the mouse down and draw
- **Add Text** / **Add Image** — drag a box, then fill it
- **Redact** — drag over something sensitive to delete it for good
- **Ctrl+H** — find and replace text across the document
- **Ctrl+Shift+O** — reorder, duplicate, or import pages
- **Ctrl+Shift+F** — fill in a form, if the PDF has one

Press **F10** to open the properties panel: it lists the markup on the
page you are viewing, and lets you delete any item from the list rather
than having to click it on the page.

Nothing touches the file on disk until you press **Ctrl+S**.

---

## Printing

Press **Ctrl+P** for the normal Windows print dialog, where you can pick
a printer, a page range, and the number of copies. **Ctrl+Shift+P**
shows a preview first. Pages are scaled to fit the paper, and landscape
documents automatically print on landscape sheets.

No printer? Windows ships with *Microsoft Print to PDF*, which works
here and is a good way to check the output.

To get images instead, use **Ctrl+Shift+E** to export pages as PNG or
JPEG at up to 600 dpi.

---

## Keyboard cheat sheet

| Key | What it does |
| --- | --- |
| Ctrl+O | Open |
| Ctrl+S | Save |
| Ctrl+P | Print |
| Ctrl+Shift+P | Print preview |
| Ctrl+Shift+E | Export pages as images |
| Ctrl+Z / Ctrl+Y | Undo / redo |
| Ctrl+H | Find and replace |
| Ctrl+Shift+O | Organize pages |
| Ctrl+Shift+F | Fill form |
| 1 – 9 | Pick an editing tool |
| F9 | Show/hide page thumbnails |
| F10 | Show/hide the properties panel |
| Ctrl+Q | Quit |
| Ctrl+0 | Reset zoom and rotation |
| Ctrl++ | Zoom in |
| Ctrl+- | Zoom out |
| Page Down | Next page |
| Page Up | Previous page |
| Ctrl+Home | First page |
| Ctrl+End | Last page |

---

## Where files go

| Thing | Location |
| --- | --- |
| Your PDFs | Stay where you opened them |
| Log file | `%USERPROFILE%\.pdfmaster\logs\pdfmaster.log` |
| Recent list | `%USERPROFILE%\.pdfmaster\recent_files.txt` |

You do not need to create those folders. The app creates them.

---

## Run tests (optional)

With the same venv active:

```powershell
pytest -v
```

You want a green pass on all 50 tests. These include headless GUI tests
that open the real window and click through navigation, zoom, rotation,
and page deletion, so a green run is a strong signal the app works.

---

## Common problems

### `python` not found

Python is not on PATH. Reinstall and enable **Add to PATH**, or use
`py -3`.

### `pip` fails with permission errors

You forgot to activate `venv`, or you are installing into a protected
system Python. Activate the venv and try again. Do not use
`sudo pip` on Linux for this project.

### `No module named src`

You are not in the repo root. `cd` there, then
`python -m src.main`.

### Window opens then closes

Look at the terminal for a traceback. A typical cause is a broken
PySide6 install. Re-run `pip install --force-reinstall PySide6`.

### "not a valid PDF"

The file is not a real PDF (for example a `.pdf` that is actually
HTML). Open it in Notepad: the first characters must be `%PDF-`.

### Encrypted PDF will not open

Opening a password-protected file still needs the password at load time.
To protect an open file yourself, use **Tools → Set Password** and save
a protected copy. **Tools → Security Info** shows encryption status.

### Changes disappeared after close

You need to Save. Rotate and delete are kept in memory until Save or
Save As.

### OneDrive lock / save error

Save As to a local folder such as `Documents\PDFMaster-out`, then copy
back when sync is idle. Your edits stay loaded in the window when a save
is refused, so nothing is lost.

### A page looks blank for a moment after zooming

Rendering runs in the background so the window never freezes. On a very
large page you may briefly see the previous zoom level before the sharp
version replaces it.

### Logs not created

The process never reached `setup_logging`. Run from a terminal (not by
double-clicking a broken shortcut) so you can see the error.

---

## Next reading

- [README.md](README.md) — full features, architecture, FAQ
- `src/constants.py` — change window size, zoom limits, colors
- `src/ui/main_window.py` — menus and ribbon
- `src/ui/widgets/ribbon.py` — ribbon tabs and groups
- `src/ui/widgets/document_tabs.py` — multi-document tabs

---

## Where to find help

1. This file for setup
2. README troubleshooting section for runtime issues
3. The log file for exact exception text
4. Your IDE's Python interpreter setting — it must point at `venv`

You are done when: the window opens, a PDF displays, zoom and page
navigation work, and the app exits with no traceback in the terminal.
