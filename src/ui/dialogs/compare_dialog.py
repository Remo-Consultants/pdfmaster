"""Dialogs for document comparison and PDF/A inspection."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
)

from src.constants import PDF_FILTER
from src.services.compare_service import CompareReport, CompareService
from src.services.pdfa_service import PdfaReport, PdfaService
from src.utils.exceptions import PDFMasterException
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CompareDialog(QDialog):
    """Compare the open PDF with another file on disk."""

    def __init__(self, left_path: Path | str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Compare Documents")
        self.resize(780, 520)
        self._left_path = Path(left_path)
        self._report: CompareReport | None = None

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.left_label = QLabel(self._left_path.name)
        self.left_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        form.addRow("Current:", self.left_label)

        row = QHBoxLayout()
        self.right_edit = QLineEdit()
        self.right_edit.setPlaceholderText("Choose a PDF to compare against…")
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        row.addWidget(self.right_edit, 1)
        row.addWidget(browse)
        form.addRow("Other:", row)
        layout.addLayout(form)

        self.run_button = QPushButton("Compare")
        self.run_button.clicked.connect(self._run)
        layout.addWidget(self.run_button)

        self.summary = QLabel("Choose a second PDF, then click Compare.")
        layout.addWidget(self.summary)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.page_list = QListWidget()
        self.page_list.currentRowChanged.connect(self._show_page)
        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)
        splitter.addWidget(self.page_list)
        splitter.addWidget(self.detail)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        close = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close:
            close.clicked.connect(self.accept)
        layout.addWidget(buttons)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Compare with PDF", "", PDF_FILTER)
        if path:
            self.right_edit.setText(path)

    def _run(self) -> None:
        other = self.right_edit.text().strip()
        if not other:
            self.summary.setText("Choose a second PDF first.")
            return
        try:
            self._report = CompareService.compare_files(self._left_path, other)
        except PDFMasterException as exc:
            self.summary.setText(str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            logger.exception("Compare failed")
            self.summary.setText(str(exc))
            return

        report = self._report
        if report.identical:
            self.summary.setText(
                f"Identical text across {report.left_pages} page(s)."
            )
        else:
            self.summary.setText(
                f"{report.changed_count} page(s) differ "
                f"(left {report.left_pages} · right {report.right_pages})."
            )

        self.page_list.clear()
        for page in report.pages:
            label = f"Page {page.page + 1} — {page.status}"
            if page.status == "changed":
                label += f" ({page.similarity:.0%} similar)"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, page.page)
            self.page_list.addItem(item)
        if self.page_list.count():
            self.page_list.setCurrentRow(0)

    def _show_page(self, row: int) -> None:
        if self._report is None or row < 0 or row >= len(self._report.pages):
            self.detail.clear()
            return
        page = self._report.pages[row]
        lines = [
            f"Status: {page.status}",
            f"Similarity: {page.similarity:.1%}",
            "",
            "Left preview:",
            page.left_preview or "(empty)",
            "",
            "Right preview:",
            page.right_preview or "(empty)",
        ]
        if page.unified:
            lines.extend(["", "Unified diff:", page.unified])
        self.detail.setPlainText("\n".join(lines))


class PdfaDialog(QDialog):
    """Show PDF/A inspection results for the open document."""

    def __init__(self, document, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("PDF/A Check")
        self.resize(520, 420)

        layout = QVBoxLayout(self)
        self.headline = QLabel("Inspecting…")
        self.headline.setStyleSheet("font-size: 15px; font-weight: 600;")
        layout.addWidget(self.headline)

        self.body = QPlainTextEdit()
        self.body.setReadOnly(True)
        layout.addWidget(self.body, 1)

        note = QLabel(
            "Desktop check only — not a full veraPDF conformance suite."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        close = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close:
            close.clicked.connect(self.accept)
        layout.addWidget(buttons)

        self._populate(document)

    def _populate(self, document) -> None:
        try:
            report: PdfaReport = PdfaService.inspect(document)
        except Exception as exc:  # noqa: BLE001
            self.headline.setText("PDF/A check failed")
            self.body.setPlainText(str(exc))
            return

        self.headline.setText(report.label)
        lines = [
            f"Declared PDF/A: {'yes' if report.declares_pdfa else 'no'}",
            f"Part / conformance: {report.part or '—'} / {report.conformance or '—'}",
            f"OutputIntent present: {'yes' if report.has_output_intent else 'no'}",
            f"PDF version / format: {report.pdf_version or '—'}",
            "",
            "Findings:",
        ]
        if not report.issues:
            lines.append("  (none)")
        else:
            for issue in report.issues:
                lines.append(f"  [{issue.severity}] {issue.message}")
        self.body.setPlainText("\n".join(lines))
