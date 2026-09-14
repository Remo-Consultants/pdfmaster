# PDFMaster Quick Start

First-run walkthrough after you have PDFMaster installed.

> **You are here:** open a PDF and learn the workspace. Install / packaging → [`INSTALL.md`](INSTALL.md) · Product overview → [`README.md`](README.md) · Product page → https://remo-consultants.github.io/pdfmaster/

**Product reflection:** [`REFLECTION.md`](REFLECTION.md) · **Press / media:** [`PRESS.md`](PRESS.md)

---

## Before you start

1. Install via **Setup.exe** or portable ZIP (see [`INSTALL.md`](INSTALL.md)), **or** run from source with the steps in that same guide  
2. Launch **PDFMaster**  
3. Have a sample PDF ready (any normal, non-password file)

Then continue below.

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

- **Ribbon** — Home / Markup / Edit / Organize / **Review** / View
- **Document tabs** — one tab per open PDF; close a tab with its ×
- **Left sidebar** — thumbnails (**F9**) and a **Bookmarks** tab for
  the document outline
- **Right panel** — document details and the markup on the current page
  (**F10**), plus text extraction (**Ctrl+T**)
- **Status bar** — what just happened, and what the current tool expects

Hover any ribbon button for its name and shortcut. PDFMaster follows the
Windows light or dark setting, and changes with it straight away.

### Review tab (search, compare, PDF/A, batch)

Open the **Review** ribbon tab (also under **Tools**):

- **Ctrl+F** — Search Document
- **Ctrl+Shift+T** — OCR Scanned Pages (needs tesseract or easyocr)
- **Ctrl+T** — Extract Text panel
- **Compare** — text diff (optional visual/rendered compare)
- **PDF/A** — declaration and basic findings
- **Batch** — compress / extract / convert a folder of PDFs
- **Tools → Security** — passwords, security info, signature fields
- **Markup** — Watermark… / Stamp…
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

If you develop from source (see [`INSTALL.md`](INSTALL.md)):

```powershell
pytest -v
```

## Common problems

Install and environment issues (Python PATH, venv, PySide6) are covered in [`INSTALL.md`](INSTALL.md).

### "not a valid PDF"

The file is not a real PDF. Open it in Notepad: the first characters must be `%PDF-`.

### Encrypted PDF will not open

Opening a password-protected file needs the password at load time.
**Tools → Security Info** shows encryption status.

### Changes disappeared after close

You need to Save. Edits stay in memory until Save or Save As.

### OneDrive lock / save error

Save As to a local folder such as `Documents\PDFMaster-out`, then copy
back when sync is idle.

---

## Next reading

- [README.md](README.md) — full features and architecture  
- [INSTALL.md](INSTALL.md) — Setup.exe, ZIP, source, packaging  
- [REFLECTION.md](REFLECTION.md) — product manifesto  

---

## Where to find help

- [GitHub Issues](https://github.com/Remo-Consultants/pdfmaster/issues)
- Product page: https://remo-consultants.github.io/pdfmaster/
- Log file: `%USERPROFILE%\.pdfmaster\logs\pdfmaster.log`
