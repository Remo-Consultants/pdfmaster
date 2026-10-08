"""Create the signature that the Sign tool places on a page."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QImage, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.services.esign import (
    SIGNATURE_STYLES,
    render_typed_signature,
    save_signature,
    signature_name,
)

_INK = QColor("#1c1917")
_IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.webp)"


class SignaturePad(QWidget):
    """A transparent pad the user draws a signature on."""

    ink_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(150)
        self.setMaximumHeight(190)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._image = QImage(self.size(), QImage.Format.Format_ARGB32_Premultiplied)
        self._image.fill(Qt.GlobalColor.transparent)
        self._last: Optional[QPoint] = None

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        resized = QImage(self.size(), QImage.Format.Format_ARGB32_Premultiplied)
        resized.fill(Qt.GlobalColor.transparent)
        painter = QPainter(resized)
        painter.drawImage(0, 0, self._image)
        painter.end()
        self._image = resized

    def clear(self) -> None:
        self._image.fill(Qt.GlobalColor.transparent)
        self._last = None
        self.update()

    def image(self) -> QImage:
        return self._image

    def has_ink(self) -> bool:
        for y in range(0, self._image.height(), 3):
            for x in range(0, self._image.width(), 3):
                if self._image.pixelColor(x, y).alpha() > 12:
                    return True
        return False

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._last = event.position().toPoint()
            self._stroke(self._last, self._last)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._last is not None and event.buttons() & Qt.MouseButton.LeftButton:
            point = event.position().toPoint()
            self._stroke(self._last, point)
            self._last = point
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._last = None
        super().mouseReleaseEvent(event)

    def _stroke(self, start: QPoint, end: QPoint) -> None:
        painter = QPainter(self._image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(_INK, 3.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(start, end)
        painter.end()
        self.update()
        self.ink_changed.emit()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        painter.setPen(QPen(QColor("#e7e4f2")))
        baseline = self.height() - 36
        painter.drawLine(24, baseline, self.width() - 24, baseline)
        painter.drawImage(0, 0, self._image)
        painter.end()


class SignDialog(QDialog):
    """Draw, type, or import the signature stored for later placement."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create signature")
        self.setMinimumWidth(560)
        self.resize(620, 560)
        screen = self.screen()
        if screen is not None:
            available = screen.availableGeometry()
            self.setMaximumHeight(max(420, available.height() - 80))
            self.resize(640, min(680, available.height() - 80))
        self._imported: Optional[QImage] = None
        self._style = "script"
        self._choice = "style"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        note = QLabel("Type your name and pick a style, or draw your own. Save uses the one you chose.")
        note.setWordWrap(True)
        layout.addWidget(note)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self._build_type_page())
        content_layout.addWidget(self._build_draw_page())
        content_layout.addWidget(self._build_image_row())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.setMinimumHeight(36)
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.setObjectName("primaryCta")
        save.setMinimumSize(108, 36)
        save.setDefault(True)
        save.clicked.connect(self._save)
        button_row.addWidget(cancel)
        button_row.addWidget(save)
        layout.addLayout(button_row)
        self._refresh_styles()

    def _build_type_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Type your name"))
        self._name = QLineEdit()
        self._name.setPlaceholderText("Type your name")
        self._name.setText(signature_name())
        self._name.setMinimumHeight(34)
        self._name.textChanged.connect(self._refresh_styles)
        layout.addWidget(self._name)

        self._style_group = QButtonGroup(self)
        self._style_group.setExclusive(True)
        self._style_buttons: dict[str, QToolButton] = {}

        styles = QWidget()
        styles_layout = QVBoxLayout(styles)
        styles_layout.setContentsMargins(0, 0, 0, 0)
        styles_layout.setSpacing(8)
        for style_id, label, *_rest in SIGNATURE_STYLES:
            button = QToolButton()
            button.setCheckable(True)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setText(label)
            button.setMinimumHeight(84)
            button.setStyleSheet(
                "QToolButton { background: white; color: #1c1b2e; border: 1px solid #e7e4f2; "
                "border-radius: 10px; padding: 6px; }"
                "QToolButton:checked { color: #1c1b2e; border: 2px solid #4f46e5; background: #ece9fe; }"
            )
            button.clicked.connect(lambda _checked=False, chosen=style_id: self._select_style(chosen))
            self._style_group.addButton(button)
            self._style_buttons[style_id] = button
            styles_layout.addWidget(button)
        self._style_buttons["script"].setChecked(True)

        style_scroll = QScrollArea()
        style_scroll.setWidgetResizable(True)
        style_scroll.setFrameShape(QFrame.Shape.NoFrame)
        style_scroll.setWidget(styles)
        style_scroll.setMinimumHeight(180)
        style_scroll.setMaximumHeight(240)
        layout.addWidget(style_scroll)
        return page

    def _build_draw_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        header = QHBoxLayout()
        header.addWidget(QLabel("Draw"))
        header.addStretch(1)
        clear_button = QPushButton("Clear drawing")
        clear_button.clicked.connect(self._clear_drawing)
        header.addWidget(clear_button)
        layout.addLayout(header)
        self._pad = SignaturePad()
        self._pad.ink_changed.connect(self._choose_drawing)
        self._pad_frame = QFrame()
        self._pad_frame.setObjectName("signaturePadFrame")
        frame_layout = QVBoxLayout(self._pad_frame)
        frame_layout.setContentsMargins(2, 2, 2, 2)
        frame_layout.addWidget(self._pad)
        layout.addWidget(self._pad_frame)
        self._mark_choice()
        return page

    def _build_image_row(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 8, 0, 0)
        choose = QPushButton("Import image…")
        choose.clicked.connect(self._choose_image)
        layout.addWidget(choose)
        self._image_preview = QLabel("")
        self._image_preview.setMinimumHeight(36)
        layout.addWidget(self._image_preview, 1)
        return row

    def _select_style(self, style_id: str) -> None:
        self._style = style_id
        self._choice = "style"
        self._mark_choice()

    def _choose_drawing(self) -> None:
        self._choice = "draw"
        self._mark_choice()

    def _clear_drawing(self) -> None:
        self._pad.clear()
        if self._choice == "draw":
            self._choice = "style"
            self._mark_choice()

    def _mark_choice(self) -> None:
        drawing = self._choice == "draw"
        border = "#4f46e5" if drawing else "#e7e4f2"
        width = "2px" if drawing else "1px"
        self._pad_frame.setStyleSheet(
            f"QFrame#signaturePadFrame {{ border: {width} solid {border}; border-radius: 10px; background: white; }}"
        )

    def _refresh_styles(self) -> None:
        name = self._name.text().strip() or "Your name"
        for style_id, _label, *_rest in SIGNATURE_STYLES:
            image = render_typed_signature(name, width=640, height=120, style=style_id)
            pixmap = QPixmap.fromImage(image).scaled(
                460,
                52,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            button = self._style_buttons[style_id]
            button.setIconSize(pixmap.size())
            button.setIcon(QIcon(pixmap))

    def _choose_image(self) -> None:
        chosen, _ = QFileDialog.getOpenFileName(self, "Signature image", str(Path.home()), _IMAGE_FILTER)
        if not chosen:
            return
        image = QImage(chosen)
        if image.isNull():
            self._image_preview.setText("That file could not be read.")
            self._imported = None
            return
        self._imported = image
        self._choice = "image"
        self._mark_choice()
        self._image_preview.setPixmap(
            QPixmap.fromImage(image).scaled(
                520,
                160,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _save(self) -> None:
        name = self._name.text().strip()
        if self._choice == "draw":
            if not self._pad.has_ink():
                return
            image = self._pad.image()
        elif self._choice == "image":
            if self._imported is None or self._imported.isNull():
                return
            image = self._imported
        else:
            if not name:
                self._name.setFocus()
                return
            image = render_typed_signature(name, style=self._style)
        save_signature(image, name)
        self.accept()
