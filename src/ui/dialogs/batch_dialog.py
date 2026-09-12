"""Dialog for batch folder processing operations."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.services.batch_service import (
    COMPRESSION_PRESETS,
    BatchService,
    BatchSummary,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BatchWorker(QThread):
    """Worker thread for batch operations."""

    progress = Signal(int, int, str)
    finished = Signal(object)
    error = Signal(str)

    def __init__(
        self,
        operation: str,
        source_folder: Path,
        output_folder: Path,
        options: dict,
    ) -> None:
        super().__init__()
        self._operation = operation
        self._source = source_folder
        self._output = output_folder
        self._options = options

    def run(self) -> None:
        try:
            def progress_callback(current: int, total: int, path: Path) -> None:
                self.progress.emit(current, total, path.name)

            if self._operation == "compress":
                result = BatchService.batch_compress(
                    self._source,
                    self._output,
                    preset_name=self._options.get("preset", "default"),
                    recursive=self._options.get("recursive", True),
                    preserve_structure=self._options.get("preserve_structure", True),
                    overwrite=self._options.get("overwrite", False),
                    progress_callback=progress_callback,
                )
            elif self._operation == "extract_text":
                result = BatchService.batch_extract_text(
                    self._source,
                    self._output,
                    recursive=self._options.get("recursive", True),
                    progress_callback=progress_callback,
                )
            elif self._operation == "convert_images":
                result = BatchService.batch_convert_to_images(
                    self._source,
                    self._output,
                    image_format=self._options.get("format", "PNG"),
                    dpi=self._options.get("dpi", 150),
                    recursive=self._options.get("recursive", True),
                    progress_callback=progress_callback,
                )
            else:
                self.error.emit(f"Unknown operation: {self._operation}")
                return

            self.finished.emit(result)

        except Exception as exc:
            logger.error("Batch operation failed: %s", exc)
            self.error.emit(str(exc))


class BatchDialog(QDialog):
    """Dialog for batch processing PDF files in folders."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._worker: Optional[BatchWorker] = None

        self.setWindowTitle("Batch Processing")
        self.resize(600, 500)

        layout = QVBoxLayout(self)

        folders_group = QGroupBox("Folders")
        folders_layout = QFormLayout(folders_group)

        source_row = QHBoxLayout()
        self._source_edit = QLineEdit()
        self._source_edit.setPlaceholderText("Select source folder...")
        source_row.addWidget(self._source_edit, 1)
        source_btn = QPushButton("Browse...")
        source_btn.clicked.connect(self._browse_source)
        source_row.addWidget(source_btn)
        folders_layout.addRow("Source:", source_row)

        output_row = QHBoxLayout()
        self._output_edit = QLineEdit()
        self._output_edit.setPlaceholderText("Select output folder...")
        output_row.addWidget(self._output_edit, 1)
        output_btn = QPushButton("Browse...")
        output_btn.clicked.connect(self._browse_output)
        output_row.addWidget(output_btn)
        folders_layout.addRow("Output:", output_row)

        layout.addWidget(folders_group)

        operation_group = QGroupBox("Operation")
        operation_layout = QFormLayout(operation_group)

        self._operation_box = QComboBox()
        self._operation_box.addItem("Compress PDFs", "compress")
        self._operation_box.addItem("Extract Text to TXT", "extract_text")
        self._operation_box.addItem("Convert to Images", "convert_images")
        self._operation_box.currentIndexChanged.connect(self._on_operation_changed)
        operation_layout.addRow("Operation:", self._operation_box)

        self._preset_box = QComboBox()
        for key, preset in COMPRESSION_PRESETS.items():
            self._preset_box.addItem(f"{preset.name} - {preset.description}", key)
        self._preset_box.setCurrentIndex(
            list(COMPRESSION_PRESETS.keys()).index("default")
        )
        operation_layout.addRow("Preset:", self._preset_box)
        self._preset_label = operation_layout.labelForField(self._preset_box)

        self._format_box = QComboBox()
        self._format_box.addItem("PNG", "PNG")
        self._format_box.addItem("JPEG", "JPEG")
        operation_layout.addRow("Format:", self._format_box)
        self._format_label = operation_layout.labelForField(self._format_box)

        self._dpi_box = QComboBox()
        for dpi in [72, 150, 300, 600]:
            self._dpi_box.addItem(f"{dpi} DPI", dpi)
        self._dpi_box.setCurrentIndex(1)
        operation_layout.addRow("Resolution:", self._dpi_box)
        self._dpi_label = operation_layout.labelForField(self._dpi_box)

        layout.addWidget(operation_group)

        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)
        self._recursive_check = QCheckBox("Include subfolders")
        self._recursive_check.setChecked(True)
        options_layout.addWidget(self._recursive_check)
        self._preserve_check = QCheckBox("Preserve folder structure")
        self._preserve_check.setChecked(True)
        options_layout.addWidget(self._preserve_check)
        self._overwrite_check = QCheckBox("Overwrite existing files")
        options_layout.addWidget(self._overwrite_check)
        layout.addWidget(options_group)

        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        progress_layout.addWidget(self._progress_bar)
        self._status_label = QLabel("Ready")
        progress_layout.addWidget(self._status_label)
        self._log_edit = QTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setMaximumHeight(100)
        progress_layout.addWidget(self._log_edit)
        layout.addWidget(progress_group)

        self._buttons = QDialogButtonBox()
        self._start_button = self._buttons.addButton(
            "Start", QDialogButtonBox.ButtonRole.ActionRole
        )
        self._start_button.clicked.connect(self._start_processing)
        self._buttons.addButton(QDialogButtonBox.StandardButton.Close)
        self._buttons.rejected.connect(self.close)
        layout.addWidget(self._buttons)

        self._on_operation_changed(0)

    def _browse_source(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select Source Folder", str(Path.home())
        )
        if folder:
            self._source_edit.setText(folder)
            if not self._output_edit.text():
                self._output_edit.setText(str(Path(folder) / "output"))

    def _browse_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", str(Path.home())
        )
        if folder:
            self._output_edit.setText(folder)

    def _on_operation_changed(self, _index: int) -> None:
        operation = self._operation_box.currentData()

        show_preset = operation == "compress"
        self._preset_box.setVisible(show_preset)
        self._preset_label.setVisible(show_preset)

        show_image = operation == "convert_images"
        self._format_box.setVisible(show_image)
        self._format_label.setVisible(show_image)
        self._dpi_box.setVisible(show_image)
        self._dpi_label.setVisible(show_image)

    def _start_processing(self) -> None:
        source = Path(self._source_edit.text().strip())
        output = Path(self._output_edit.text().strip())

        if not source.is_dir():
            self._log("Error: Source folder does not exist")
            return

        operation = self._operation_box.currentData()
        options = {
            "preset": self._preset_box.currentData(),
            "format": self._format_box.currentData(),
            "dpi": self._dpi_box.currentData(),
            "recursive": self._recursive_check.isChecked(),
            "preserve_structure": self._preserve_check.isChecked(),
            "overwrite": self._overwrite_check.isChecked(),
        }

        self._start_button.setEnabled(False)
        self._progress_bar.setValue(0)
        self._log_edit.clear()
        self._log(f"Starting {operation} operation...")

        self._worker = BatchWorker(operation, source, output, options)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, current: int, total: int, filename: str) -> None:
        percent = int((current / total) * 100) if total > 0 else 0
        self._progress_bar.setValue(percent)
        self._status_label.setText(f"Processing: {filename} ({current + 1}/{total})")

    def _on_finished(self, result: BatchSummary) -> None:
        self._progress_bar.setValue(100)
        self._start_button.setEnabled(True)

        self._log(f"\nCompleted: {result.successful}/{result.total} successful")
        if result.failed > 0:
            self._log(f"Failed: {result.failed}")
        if result.skipped > 0:
            self._log(f"Skipped: {result.skipped}")

        if result.total_input_bytes > 0:
            ratio = result.compression_ratio * 100
            self._log(f"Total reduction: {ratio:.1f}%")

        for r in result.results:
            if not r.success and r.error:
                self._log(f"  Error: {r.source.name} - {r.error}")

        self._status_label.setText("Complete")

    def _on_error(self, message: str) -> None:
        self._start_button.setEnabled(True)
        self._log(f"\nError: {message}")
        self._status_label.setText("Error")

    def _log(self, message: str) -> None:
        self._log_edit.append(message)

    def closeEvent(self, event) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.wait(1000)
        super().closeEvent(event)
