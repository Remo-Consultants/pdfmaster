# PDFMaster — Press & PR Kit

**One-line:** PDFMaster is a free, offline-first Windows PDF viewer and editor with commercial-grade ribbon UX, true redaction, and MIT-licensed source.

**Tagline:** *The desk, not the cloud.*

**Version:** 0.7.0  
**License:** MIT  
**Platform:** Windows 10/11 (64-bit); source runs on Linux/macOS  
**Organization:** [Remo Consultants](https://github.com/Remo-Consultants)  
**Product page:** https://remo-consultants.github.io/pdfmaster/  
**Downloads:** https://github.com/Remo-Consultants/pdfmaster/releases/latest  

**Related:** [Product reflection](REFLECTION.md) · [README](README.md) · [Product page](docs/index.html)

---

## Boilerplate (short)

PDFMaster is a professional desktop PDF workspace for Windows. It combines a ribbon interface, multi-document tabs, markup and editing tools, AES security, document compare, PDF/A inspection, and batch processing — entirely offline. Files never leave the user's machine. PDFMaster is open source under the MIT license.

---

## Boilerplate (long)

For decades, PDF software has meant powerful tools tied to subscriptions and cloud-adjacent workflows. PDFMaster offers a different contract: **commercial craft, local custody, open ownership.**

Built with PySide6 and PyMuPDF, PDFMaster delivers the workspace patterns users expect from industry-leading editors — labelled ribbon groups, continuous page scrolling with soft shadows, thumbnails and bookmarks, bounded undo — while keeping every operation on the desktop. True redaction removes content from the file; atomic saves protect originals; a layered architecture keeps the UI maintainable as features grow.

PDFMaster 0.7 adds document compare (page-by-page text diff) and desktop PDF/A inspection. Earlier releases shipped search, OCR, text extraction, watermarks, stamps, forms, and NSIS/PyInstaller packaging for Setup.exe and portable ZIP distribution.

PDFMaster is independent and not affiliated with Adobe, Foxit, Microsoft, or the PDF Association.

---

## Key messages

1. **Offline-first by design** — no account required to open a PDF  
2. **Ribbon workspace without a subscription** — Home, Markup, Edit, Organize, View  
3. **True redaction** — content removal, not cosmetic overlay  
4. **Compare & PDF/A on the desk** — no external SaaS for basic compliance tasks  
5. **MIT source** — auditable, forkable, packagable for internal IT  

---

## Differentiators vs. commercial suites

| Topic | PDFMaster story |
| --- | --- |
| Data residency | Files stay on disk; no default upload path |
| Cost | Free / MIT; no tier gating for redaction or security |
| Honesty | Font substitution and text-fit limits are disclosed in UI |
| Engineering | 260+ automated tests including headless Qt UI flows |
| Packaging | Setup.exe, portable ZIP, and reproducible PyInstaller build |

---

## Feature highlights (0.7.0)

- View: zoom 25–400%, fit modes, thumbnails, bookmarks, properties  
- Markup: highlight, underline, strikeout, notes, pen, shapes, stamps, watermarks  
- Edit: replace text, add text/images, find/replace, forms, flatten  
- Organize: reorder, insert, duplicate, delete, rotate, import pages  
- Security: AES encrypt/decrypt copies, security info  
- Tools: search, OCR (optional engine), text extract, batch folder ops  
- **New in 0.7:** compare two PDFs; PDF/A declaration check  

---

## Quotes (approved for media use)

> "The PDF on your desk is yours. It should open instantly, edit honestly, and leave when you close the app — not linger in someone else's cloud."  
> — PDFMaster product reflection

> "The desk, not the cloud."  
> — PDFMaster tagline

---

## Assets

| Asset | Path |
| --- | --- |
| Hero banner (SVG) | `docs/assets/banner.svg` |
| App mark (SVG) | `docs/assets/mark.svg` |
| Product page | `docs/index.html` |
| Manifesto | `REFLECTION.md` |
| Full README | `README.md` |

For PNG/ICO app icons, see `resources/icons/` in the repository (when present in release branches).

---

## Suggested headlines

- **PDFMaster 0.7 Brings Document Compare and PDF/A Checks to a Free Offline PDF Editor**
- **Remo Consultants Ships PDFMaster: Ribbon-Grade PDF Tools Without the Cloud**
- **MIT-Licensed PDFMaster Targets Professionals Who Want Adobe-Style UX and Local File Custody**

---

## 60-second pitch (spoken)

PDFMaster is a Windows PDF viewer and editor that feels like the commercial tools you already know — ribbon, tabs, continuous pages — but your files never leave your PC. It is MIT-licensed and free. You get markup, true redaction, AES security, search, OCR, batch jobs, and in 0.7, document compare and PDF/A inspection. No account. No subscription. Just the desk.

---

## Social copy (ready to post)

**LinkedIn (short)**

PDFMaster 0.7 is out: a free, offline-first PDF workspace for Windows with ribbon UX, true redaction, compare, and PDF/A checks — MIT licensed. *The desk, not the cloud.*

Download: https://github.com/Remo-Consultants/pdfmaster/releases/latest  
Story: https://github.com/Remo-Consultants/pdfmaster/blob/main/REFLECTION.md

**X / Twitter (280 chars)**

PDFMaster 0.7 — ribbon-grade PDF tools for Windows, fully offline. Compare docs, PDF/A check, true redaction, MIT. No cloud. No account. *The desk, not the cloud.* https://github.com/Remo-Consultants/pdfmaster/releases/latest

---

## GitHub release notes template (0.7.0)

Copy into a release description when tagging `v0.7.0`:

```markdown
## PDFMaster 0.7.0 — Compare & PDF/A on the desk

**The desk, not the cloud.** Professional PDF work stays on your machine.

### Highlights
- **Compare Documents** — page-by-page text diff vs another PDF (Tools → Compare)
- **PDF/A Check** — declaration, part/conformance, OutputIntent, structured findings
- Watermarks, stamps, security, batch, OCR, and full ribbon workspace (0.5–0.6)

### Install
| Option | File |
| --- | --- |
| Recommended | `PDFMaster-0.7.0-Setup.exe` |
| Portable | `PDFMaster-0.7.0-win64.zip` |

### Docs
- [Quick start](QUICKSTART.md) · [Install](INSTALL.md) · [Reflection](REFLECTION.md) · [Press kit](PRESS.md)
- Product page: https://remo-consultants.github.io/pdfmaster/

### Notes
PDFMaster is independent and not affiliated with Adobe, Foxit, or the PDF Association.
```

---

## Contact & support

- **Issues / feedback:** https://github.com/Remo-Consultants/pdfmaster/issues  
- **Documentation:** README.md, REFLECTION.md, QUICKSTART.md, INSTALL.md, docs/index.html  

---

## Legal

PDFMaster is provided under the MIT License. Adobe, Acrobat, Foxit, and Windows are trademarks of their respective owners. PDFMaster is an independent project and is not endorsed by those entities.
