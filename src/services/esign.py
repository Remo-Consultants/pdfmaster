"""Saved signature image used by the Sign tool.

The signature is an appearance placed on the page. It is stored once
under the PDFMaster config folder and reused until the user replaces it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter

from src.constants import CONFIG_DIR

SIGNATURE_FILE = "signature.png"
SIGNATURE_META = "signature.json"

# id, label, font families to try, italic, underline
SIGNATURE_STYLES = (
    ("script", "Script", ("Segoe Script", "Segoe Print", "Georgia"), False, False),
    ("handwritten", "Handwritten", ("Segoe Print", "Ink Free", "Segoe Script"), False, False),
    ("brush", "Brush", ("Ink Free", "Segoe Script", "Segoe Print"), False, False),
    ("classic", "Classic", ("Georgia", "Times New Roman", "Palatino Linotype"), True, False),
    ("formal", "Formal", ("Segoe UI", "Calibri", "Arial"), False, True),
)


def signature_dir() -> Path:
    path = CONFIG_DIR / "signatures"
    path.mkdir(parents=True, exist_ok=True)
    return path


def signature_path() -> Optional[Path]:
    """Path of the saved signature, if one exists."""
    candidate = signature_dir() / SIGNATURE_FILE
    if candidate.is_file() and candidate.stat().st_size > 0:
        return candidate
    return None


def signature_name() -> str:
    meta = signature_dir() / SIGNATURE_META
    if not meta.is_file():
        return ""
    try:
        payload = json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return str(payload.get("name") or "")


def save_signature(image: QImage, name: str = "") -> Path:
    """Crop, store, and return the signature PNG."""
    cropped = crop_signature(image)
    destination = signature_dir() / SIGNATURE_FILE
    if not cropped.save(str(destination), "PNG"):
        raise OSError(f"Could not save signature to {destination}")
    meta = {"name": name.strip()}
    (signature_dir() / SIGNATURE_META).write_text(
        json.dumps(meta), encoding="utf-8"
    )
    return destination


def crop_signature(image: QImage) -> QImage:
    """Trim transparent margins so the stamp hugs the ink."""
    source = image.convertToFormat(QImage.Format.Format_ARGB32)
    width = source.width()
    height = source.height()
    min_x, min_y = width, height
    max_x, max_y = -1, -1
    for y in range(height):
        for x in range(width):
            if source.pixelColor(x, y).alpha() > 12:
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
    if max_x < 0:
        return source
    pad = 8
    left = max(0, min_x - pad)
    top = max(0, min_y - pad)
    right = min(width - 1, max_x + pad)
    bottom = min(height - 1, max_y + pad)
    return source.copy(left, top, right - left + 1, bottom - top + 1)


def render_typed_signature(
    name: str,
    width: int = 900,
    height: int = 220,
    style: str = "script",
) -> QImage:
    """Draw a name in one of the suggested signature styles."""
    chosen = next((item for item in SIGNATURE_STYLES if item[0] == style), SIGNATURE_STYLES[0])
    _style_id, _label, families, italic, underline = chosen
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    pixel_size = max(28, min(78, int(width / max(len(name.strip()), 1) * 1.15)))
    font = _font_for(families, pixel_size, italic)
    painter.setFont(font)
    painter.setPen(QColor("#1c1917"))
    text = name.strip()
    bounds = painter.boundingRect(image.rect(), Qt.AlignmentFlag.AlignCenter, text)
    painter.drawText(image.rect(), Qt.AlignmentFlag.AlignCenter, text)
    if underline:
        painter.drawLine(int(bounds.left()), int(bounds.bottom()) + 4, int(bounds.right()), int(bounds.bottom()) + 4)
    painter.end()
    return image


def _font_for(families: tuple, pixel_size: int, italic: bool) -> QFont:
    installed = set(QFontDatabase.families())
    for family in families:
        if family not in installed:
            continue
        font = QFont(family)
        font.setPixelSize(pixel_size)
        font.setItalic(italic)
        return font
    font = QFont()
    font.setPixelSize(pixel_size)
    font.setItalic(True)
    return font
