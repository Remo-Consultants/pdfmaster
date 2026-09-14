<p align="center">
  <img src="docs/assets/mark.svg" alt="" width="72" height="72" />
</p>

<h1 align="center">PDFMaster — Product Reflection</h1>

<p align="center"><em>The desk, not the cloud.</em></p>

<p align="center">
  <a href="README.md">README</a> ·
  <a href="https://remo-consultants.github.io/pdfmaster/">Product page</a> ·
  <a href="PRESS.md">Press kit</a> ·
  <a href="QUICKSTART.md">Quick start</a>
</p>

---

## A letter on PDF software

For thirty years, the PDF has been the **lingua franca of serious work**: contracts, filings, research, invoices, manuals, evidence. Adobe invented the format and, for a long time, owned the experience of working with it. Foxit and others followed — often faster, sometimes cheaper, always chasing the same mental model: a dense ribbon, many tabs, and the quiet assumption that **your documents are a product surface**.

PDFMaster begins with a different assumption:

> **The PDF on your desk is yours.**  
> It should open instantly, edit honestly, and leave when you close the app — not linger in someone else's cloud.

We are not building a portal. We are building a **native workspace** that feels as deliberate as the best commercial tools, without asking you to rent your own files back.

---

## Design ethos

### 1. Offline-first is a feature, not a fallback

Every capability in PDFMaster is designed to run **without a network**. Search, OCR, batch jobs, compare, PDF/A inspection, encryption — all local. There is no account to create, no telemetry pipeline baked into the read path, no "sign in to continue."

This is not nostalgia. It is **trust architecture**: legal, medical, financial, and government workflows still treat the desktop as the boundary of control. PDFMaster meets them there.

### 2. Commercial craft, open ownership

Users trained on Adobe Acrobat and Foxit PDF Editor expect:

- A **ribbon** with named groups, not a mystery toolbar  
- **Multiple documents** in tabs, each with independent state  
- **Continuous reading** with pages that feel like paper on a desk  
- **Immediate feedback** — status bar, undo, tool hints  

PDFMaster delivers that composition in PySide6 (Qt 6), with a theme that **tracks Windows light and dark** without a restart. HiDPI SVG icons. Soft shadows under pages so edges remain visible on any canvas grey.

The difference: the result is **MIT-licensed**. You can install it, fork it, ship it inside your organization, and audit the code that touches your PDFs.

### 3. Honest editing

PDFs are not Word documents. Text sits in arbitrary positions; fonts may not embed; replacement has physical limits. PDFMaster does not pretend otherwise:

- When text is replaced, the app **shrinks to fit** before it lies about layout  
- When a font is missing, it **says so** and substitutes a standard face  
- When you **redact**, content is **removed**, not covered with a black rectangle that copy-paste can still recover  

That honesty is how you earn power users — paralegals, engineers, compliance officers — who have been burned by tools that optimize for demos instead of saved files.

### 4. Layered engineering

The UI never calls PyMuPDF directly. A single `Document` owns the open handle under a lock; processors and services mutate through **`Document.transaction()`** so background rendering and edits never race.

Failures become **typed exceptions** surfaced in the status bar and in rotating logs. Saves are **atomic**: a failed overwrite never corrupts the original on disk.

This structure is how you keep a ribbon-heavy app maintainable as features accumulate — compare, PDF/A, batch, security — without turning every dialog into a special case.

### 5. Restraint in roadmap

We ship **complete slices**, not infinite previews. Version 0.7 adds compare and PDF/A inspection because those are daily desktop tasks that should not require a subscription or a server.

What we have **not** promised: mandatory cloud sync, social sharing, or AI that sends your document to a third party. When cloud or signature features arrive, they will be **opt-in**, explicit, and secondary to the offline core.

---

## Who PDFMaster is for

| Persona | Why PDFMaster |
| --- | --- |
| **Solo professional** | One installer, no subscription, full markup and security |
| **IT / internal tools team** | MIT source, PyInstaller + NSIS packaging, predictable logs |
| **Developer** | Clear layers, 260+ tests, pytest-qt headless UI coverage |
| **Privacy-sensitive org** | Files stay local; no account wall on open |
| **Student / researcher** | Search, extract, OCR, compare — without uploading to a SaaS |

PDFMaster is **not** trying to replace every Acrobat Enterprise workflow on day one. It **is** trying to be the best **owned** PDF desk you can download today.

---

## How we compare (in spirit)

| Dimension | Adobe Acrobat | Foxit PDF Editor | PDFMaster |
| --- | --- | --- | --- |
| **Business model** | Subscription / enterprise | Perpetual + subscription tiers | Free (MIT) |
| **Default data path** | Cloud-adjacent ecosystem | Mixed | Local disk only |
| **Workspace** | Industry reference ribbon | Strong commercial UI | Ribbon + tabs, Qt-native |
| **Redaction** | Professional (tier-dependent) | Professional | True content removal |
| **Extensibility** | Plugins, SDK (licensed) | SDK (licensed) | Python source, fork-friendly |
| **Auditability** | Closed source | Closed source | Open source |

We compete on **clarity and custody**, not on badge count. Where commercial suites add another panel, we ask whether the task belongs on the desk at all.

---

## Brand voice

- **Confident, not loud** — we describe what the product does; we do not trash competitors by name in the UI  
- **Precise** — "true redaction," "atomic save," "declares PDF/A" mean specific technical behaviors  
- **Human** — quick start guides read for humans, not for linter bots  
- **Visual** — teal and ink palette, Instrument Serif headlines on the product page, page-stack metaphor in brand assets  

Tagline: **The desk, not the cloud.**

---

## What "professional" means here

Professional PDF software is not a skin. It is:

1. **Predictable keyboard** — `Ctrl+O`, `Ctrl+F`, `Ctrl+Z` behave every session  
2. **Recoverability** — bounded undo, logs when something fails  
3. **Respect for the file** — validate on open, cap size sanely, repair when possible with explicit warning  
4. **Print and export that match intent** — fit to paper, landscape auto, export DPI that stops before absurd memory use  
5. **Security without theater** — AES encryption you can write to a copy; security info you can read before you share  

PDFMaster treats these as **non-negotiables**, not premium upsells.

---

## Invitation

If you maintain documents that matter — if you have ever closed a PDF tool wondering where your file was uploaded — PDFMaster is built for you.

Download a release. Open your hardest PDF. Redact a line, compare two versions, run a PDF/A check, password-protect a copy. If the desk feels right, star the repo, file an issue, or send a pull request.

We are building the PDF workspace **you own**.

<p align="center">
  <strong><a href="https://github.com/Remo-Consultants/pdfmaster/releases/latest">Download PDFMaster</a></strong>
</p>

<p align="center">
  Remo Consultants · MIT License · v0.7.0
</p>
