# Install PDFMaster

Straight paths from download to working on a PDF.

**Product overview:** [`docs/index.html`](docs/index.html) · **Why PDFMaster:** [`REFLECTION.md`](REFLECTION.md) · **Media:** [`PRESS.md`](PRESS.md)

---

## Path 1 — Setup.exe (recommended for most users)

1. Go to [Releases](https://github.com/Remo-Consultants/pdfmaster/releases/latest)
2. Download **`PDFMaster-*-Setup.exe`** from the latest release
3. Run it (admin elevation is normal for Program Files)
4. Finish the wizard — Start Menu and desktop shortcuts are created
5. Start **PDFMaster**
6. Press **Ctrl+O**, pick a PDF, scroll / zoom / save as usual

**Uninstall:** Start Menu → PDFMaster → Uninstall, or Windows Settings → Apps.

---

## Path 2 — Portable ZIP

1. Download **`PDFMaster-*-win64.zip`** from the same release
2. Extract to any folder (e.g. `Documents\PDFMaster` or a USB drive)
3. Double-click **`PDFMaster.exe`**
4. Optional: pin the exe to the taskbar

No installer, no Start Menu entry unless you create a shortcut yourself.

---

## Path 3 — Run from source

Requires Python 3.10+ on PATH.

```powershell
git clone https://github.com/Remo-Consultants/pdfmaster.git
cd pdfmaster
python -m venv venv
.\venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m src.main
```

Optional editable install:

```powershell
pip install -e .
```

---

## Path 4 — Build Windows packages (maintainers)

### Prerequisites

| Tool | Why |
| --- | --- |
| Python venv with app deps | Runtime libraries |
| `pip install pyinstaller` | Folder / ZIP build |
| [NSIS 3](https://nsis.sourceforge.io/) (`makensis`) | Setup.exe — `winget install NSIS.NSIS` |

App icons live in `resources/icons/pdfmaster.ico` and `.png`.

### Build

```powershell
.\venv\Scripts\activate
pip install pyinstaller
python installer/build_installer.py --clean --nsis
```

| Output | Description |
| --- | --- |
| `dist/PDFMaster/PDFMaster.exe` | Runnable folder build |
| `dist/PDFMaster-<version>-win64.zip` | Portable archive |
| `dist/PDFMaster-<version>-Setup.exe` | NSIS installer |

Scripts:

- [`pdfmaster.spec`](pdfmaster.spec) — PyInstaller layout  
- [`installer/build_installer.py`](installer/build_installer.py) — orchestrates clean / zip / NSIS  
- [`installer/pdfmaster.nsi`](installer/pdfmaster.nsi) — Start Menu, desktop, Add/Remove Programs, optional PDF open-with

### Attach artifacts to a GitHub release

```powershell
gh release upload v0.7.0 `
  dist/PDFMaster-0.7.0-win64.zip `
  dist/PDFMaster-0.7.0-Setup.exe `
  --clobber
```

---

## After install — first actions

| Goal | How |
| --- | --- |
| Open a file | `Ctrl+O` |
| Search | `Ctrl+F` |
| Extract text | `Ctrl+T` |
| OCR (optional engine) | Tools → OCR, or `Ctrl+Shift+T` |
| Protect a copy | Tools → Set Password |
| Batch a folder | Tools → Batch Processing |
| Save | `Ctrl+S` |

Logs: `%USERPROFILE%\.pdfmaster\logs\pdfmaster.log`

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Setup blocked by SmartScreen | More info → Run anyway (unsigned local builds) |
| Missing `PDFMaster.exe` in ZIP | Extract the whole archive; run from `PDFMaster\` folder |
| OCR says unavailable | Install Tesseract or `pip install easyocr` (source builds) |
| Source: `No module named src` | `cd` into the repo root before `python -m src.main` |
| PyInstaller build fails | Use the project venv: `.\venv\Scripts\python.exe installer/build_installer.py` |

More day-to-day help: [`QUICKSTART.md`](QUICKSTART.md).
