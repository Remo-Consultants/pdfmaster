"""Image conversion helpers shared by the viewer and the print service."""

from __future__ import annotations

from PIL import Image
from PySide6.QtGui import QImage


def pil_to_qimage(image: Image.Image) -> QImage:
    """Convert a PIL image to a QImage by copying the raw RGB buffer.

    Going through raw bytes is roughly 3-4x faster than a PNG round
    trip, which matters because this runs for every page render.
    """
    if image.mode != "RGB":
        image = image.convert("RGB")
    raw = image.tobytes("raw", "RGB")
    qimage = QImage(raw, image.width, image.height, image.width * 3,
                    QImage.Format.Format_RGB888)
    # QImage does not take ownership of ``raw``, so copy before it is freed.
    return qimage.copy()
