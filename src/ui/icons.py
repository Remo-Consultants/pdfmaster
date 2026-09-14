"""Theme-aware icons rendered from SVG for sharp HiDPI display.

Each icon is an SVG silhouette with ``{ink}`` / ``{accent}`` colour
placeholders. At build time we rasterise every size the ribbon asks for
at the screen's real device-pixel size (no setDevicePixelRatio), so Qt's
icon matcher — which ignores DPR metadata — always finds an exact
bitmap and never upscales a soft one.
"""

from __future__ import annotations

from typing import Dict, Optional

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QIcon,
    QImage,
    QPainter,
    QPixmap,
)
from PySide6.QtSvg import QSvgRenderer

from src.ui.theme import color as theme_color
from src.ui.tools import ToolMode

# Logical sizes the UI requests.
_SIZES = (16, 18, 20, 22, 24, 28, 32, 36, 40, 48, 64)
_cache: Dict[str, QIcon] = {}


def _device_pixel_ratio() -> float:
    app = QGuiApplication.instance()
    if app is None:
        return 1.0
    screen = app.primaryScreen()
    if screen is None:
        return 1.0
    return max(1.0, float(screen.devicePixelRatio()))


# ----------------------------------------------------------------------
# SVG templates (24×24 viewBox). {ink} and {accent} are filled in.
# ----------------------------------------------------------------------
_SVG_HEAD = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
_SVG_TAIL = "</svg>"


def _svg(*parts: str) -> str:
    return _SVG_HEAD + "".join(parts) + _SVG_TAIL


ACTION_SVGS: Dict[str, str] = {
    "open": _svg(
        '<path fill="{ink}" d="M3 6.5A1.5 1.5 0 0 1 4.5 5H9l1.5 1.5H19.5A1.5 1.5 0 0 1 21 8v1H4.5A1.5 1.5 0 0 0 3 10.5V6.5Z"/>',
        '<path fill="{accent}" d="M3 10h18l-1.2 8.1A2 2 0 0 1 17.82 20H6.18A2 2 0 0 1 4.2 18.1L3 10Z"/>',
    ),
    "save": _svg(
        '<path fill="{ink}" d="M5 3h11l3 3v14a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z"/>',
        '<rect fill="{accent}" x="8" y="13" width="8" height="5" rx="0.8"/>',
        '<rect fill="{accent}" x="8" y="4" width="6" height="5" rx="0.6" opacity="0.85"/>',
    ),
    "print": _svg(
        '<path fill="{ink}" d="M7 3h10v4H7V3Zm-3 6h16a2 2 0 0 1 2 2v5h-4v4H7v-4H3v-5a2 2 0 0 1 2-2Z"/>',
        '<rect fill="{accent}" x="8" y="14" width="8" height="5" rx="0.6"/>',
        '<circle fill="{accent}" cx="6.5" cy="11.5" r="1"/>',
    ),
    "undo": _svg(
        '<path fill="none" stroke="{ink}" stroke-width="2.2" stroke-linecap="round" '
        'stroke-linejoin="round" d="M8 10H4V6"/>',
        '<path fill="none" stroke="{ink}" stroke-width="2.2" stroke-linecap="round" '
        'd="M5 10a7 7 0 1 1 2 5.3"/>',
    ),
    "redo": _svg(
        '<path fill="none" stroke="{ink}" stroke-width="2.2" stroke-linecap="round" '
        'stroke-linejoin="round" d="M16 10h4V6"/>',
        '<path fill="none" stroke="{ink}" stroke-width="2.2" stroke-linecap="round" '
        'd="M19 10a7 7 0 1 0-2 5.3"/>',
    ),
    "zoom_in": _svg(
        '<circle fill="none" stroke="{ink}" stroke-width="2" cx="10.5" cy="10.5" r="6"/>',
        '<path fill="none" stroke="{ink}" stroke-width="2.2" stroke-linecap="round" d="M15.5 15.5 20 20"/>',
        '<path fill="none" stroke="{accent}" stroke-width="2" stroke-linecap="round" d="M8 10.5h5M10.5 8v5"/>',
    ),
    "zoom_out": _svg(
        '<circle fill="none" stroke="{ink}" stroke-width="2" cx="10.5" cy="10.5" r="6"/>',
        '<path fill="none" stroke="{ink}" stroke-width="2.2" stroke-linecap="round" d="M15.5 15.5 20 20"/>',
        '<path fill="none" stroke="{accent}" stroke-width="2" stroke-linecap="round" d="M8 10.5h5"/>',
    ),
    "fit_width": _svg(
        '<rect fill="{ink}" x="7" y="4" width="10" height="16" rx="1.5"/>',
        '<path fill="{accent}" d="M2 12l4-3.5v7L2 12Zm20 0-4-3.5v7l4-3.5Z"/>',
        '<path fill="none" stroke="{accent}" stroke-width="1.8" stroke-linecap="round" d="M6 12h12"/>',
    ),
    "fit_page": _svg(
        '<rect fill="{ink}" x="7" y="4" width="10" height="16" rx="1.5"/>',
        '<path fill="{accent}" d="M12 1.5l3.5 4h-7L12 1.5Zm0 21-3.5-4h7L12 22.5Z"/>',
        '<path fill="none" stroke="{accent}" stroke-width="1.8" stroke-linecap="round" d="M12 5.5v13"/>',
    ),
    "rotate_cw": _svg(
        '<path fill="none" stroke="{ink}" stroke-width="2.2" stroke-linecap="round" '
        'd="M19 12a7 7 0 1 1-2-4.9"/>',
        '<path fill="{ink}" d="M19 4v6h-6l6-6Z"/>',
    ),
    "rotate_ccw": _svg(
        '<path fill="none" stroke="{ink}" stroke-width="2.2" stroke-linecap="round" '
        'd="M5 12a7 7 0 1 0 2-4.9"/>',
        '<path fill="{ink}" d="M5 4v6h6L5 4Z"/>',
    ),
    "prev": _svg(
        '<path fill="{ink}" d="M15.5 5.5 8 12l7.5 6.5V5.5Z"/>',
    ),
    "next": _svg(
        '<path fill="{ink}" d="M8.5 5.5 16 12l-7.5 6.5V5.5Z"/>',
    ),
    "sidebar": _svg(
        '<rect fill="none" stroke="{ink}" stroke-width="1.8" x="3" y="4" width="18" height="16" rx="2"/>',
        '<rect fill="{accent}" x="4.2" y="5.2" width="5" height="13.6" rx="1"/>',
    ),
    "panel": _svg(
        '<rect fill="none" stroke="{ink}" stroke-width="1.8" x="3" y="4" width="18" height="16" rx="2"/>',
        '<rect fill="{accent}" x="14.8" y="5.2" width="5" height="13.6" rx="1"/>',
    ),
    "organize": _svg(
        '<rect fill="{ink}" x="3" y="4" width="8" height="11" rx="1.2"/>',
        '<rect fill="{accent}" x="13" y="8" width="8" height="11" rx="1.2"/>',
    ),
    "merge": _svg(
        '<rect fill="{ink}" x="3" y="5" width="8" height="14" rx="1.2"/>',
        '<rect fill="{accent}" x="13" y="5" width="8" height="14" rx="1.2"/>',
        '<path fill="none" stroke="{ink}" stroke-width="1.8" stroke-linecap="round" d="M11 12h2"/>',
    ),
    "delete_page": _svg(
        '<path fill="{ink}" d="M9 4h6l1 2h4v2H4V6h4l1-2Zm1 6h2v8h-2v-8Zm4 0h2v8h-2v-8ZM6 8h12l-1 12H7L6 8Z"/>',
    ),
    "form": _svg(
        '<rect fill="none" stroke="{ink}" stroke-width="1.8" x="4" y="3" width="16" height="18" rx="1.5"/>',
        '<path fill="none" stroke="{accent}" stroke-width="1.8" stroke-linecap="round" d="M7 8h10M7 12h10M7 16h6"/>',
    ),
    "search": _svg(
        '<circle fill="none" stroke="{ink}" stroke-width="2" cx="10" cy="10" r="6"/>',
        '<path fill="none" stroke="{ink}" stroke-width="2.2" stroke-linecap="round" d="M15 15 20 20"/>',
        '<path fill="none" stroke="{accent}" stroke-width="1.8" stroke-linecap="round" d="M7.5 10h5"/>',
    ),
    "watermark": _svg(
        '<rect fill="none" stroke="{ink}" stroke-width="1.8" x="6" y="4" width="12" height="16" rx="1.2"/>',
        '<path fill="none" stroke="{accent}" stroke-width="1.6" stroke-linecap="round" '
        'd="M8 9h8M8 12h8M8 15h6" opacity="0.55"/>',
        '<path fill="{accent}" d="M9 7h6l-1 2H10l-1-2Z" opacity="0.85"/>',
    ),
    "stamp": _svg(
        '<rect fill="none" stroke="{ink}" stroke-width="1.8" x="5" y="5" width="14" height="14" rx="2"/>',
        '<path fill="{accent}" d="M8 11h8v2H8v-2Z"/>',
        '<path fill="none" stroke="{accent}" stroke-width="1.8" stroke-linecap="round" d="M9 8h6"/>',
    ),
    "compare": _svg(
        '<rect fill="{ink}" x="3" y="5" width="8" height="14" rx="1.2"/>',
        '<rect fill="{accent}" x="13" y="5" width="8" height="14" rx="1.2"/>',
        '<path fill="none" stroke="{ink}" stroke-width="2" stroke-linecap="round" d="M11.5 9v6"/>',
    ),
    "pdfa": _svg(
        '<rect fill="none" stroke="{ink}" stroke-width="1.8" x="4" y="3" width="16" height="18" rx="1.5"/>',
        '<path fill="{accent}" d="M7 8h4.2l1.2 3.5L14 8h3l-3.8 10h-2.4L7 8Z"/>',
        '<path fill="none" stroke="{accent}" stroke-width="1.6" stroke-linecap="round" d="M7 17h10"/>',
    ),
    "batch": _svg(
        '<rect fill="{ink}" x="3" y="6" width="9" height="12" rx="1.2"/>',
        '<rect fill="{accent}" x="12" y="6" width="9" height="12" rx="1.2"/>',
        '<path fill="none" stroke="{ink}" stroke-width="1.8" stroke-linecap="round" d="M7.5 12h9"/>',
    ),
    "ocr": _svg(
        '<rect fill="none" stroke="{ink}" stroke-width="1.8" x="4" y="5" width="16" height="14" rx="1.5"/>',
        '<path fill="{accent}" d="M7 10h2v4H7v-4Zm4 0h2v4h-2v-4Zm4 0h2v4h-2v-4Z"/>',
        '<path fill="none" stroke="{accent}" stroke-width="1.6" stroke-linecap="round" d="M7 16h10"/>',
    ),
}


TOOL_SVGS: Dict[ToolMode, str] = {
    ToolMode.PAN: _svg(
        '<path fill="{ink}" d="M6 3v15l3.5-3.2 2.2 5.2 2.6-1.1-2.2-5.2L16 13.5 6 3Z"/>',
    ),
    ToolMode.HIGHLIGHT: _svg(
        '<path fill="{ink}" d="M8 14V7.5L11 3.5 14 7.5V14H8Z"/>',
        '<rect fill="{accent}" x="4" y="16" width="16" height="4" rx="1.5"/>',
    ),
    ToolMode.UNDERLINE: _svg(
        '<path fill="{ink}" d="M7 5h3.2l1.8 8L13.8 5H17l-3.2 14h-3.6L7 5Z"/>',
        '<path fill="none" stroke="{accent}" stroke-width="2.2" stroke-linecap="round" d="M6 20h12"/>',
    ),
    ToolMode.STRIKEOUT: _svg(
        '<path fill="{ink}" d="M7 4h3.2l1.8 8L13.8 4H17l-3.2 14h-3.6L7 4Z"/>',
        '<path fill="none" stroke="{accent}" stroke-width="2.2" stroke-linecap="round" d="M5 12h14"/>',
    ),
    ToolMode.NOTE: _svg(
        '<path fill="{ink}" d="M5 4h14v10h-5l-3 4v-4H5V4Z"/>',
        '<rect fill="{accent}" x="8" y="8" width="8" height="1.8" rx="0.6"/>',
        '<rect fill="{accent}" x="8" y="11.5" width="5" height="1.8" rx="0.6"/>',
    ),
    ToolMode.PEN: _svg(
        '<path fill="none" stroke="{ink}" stroke-width="2.2" stroke-linecap="round" '
        'd="M4 18c3-8 6 4 10-6s5-2 6-4"/>',
        '<circle fill="{accent}" cx="19" cy="7" r="2"/>',
    ),
    ToolMode.SHAPE: _svg(
        '<rect fill="none" stroke="{ink}" stroke-width="2" x="4" y="6" width="16" height="12" rx="2"/>',
    ),
    ToolMode.TEXT: _svg(
        '<path fill="{ink}" d="M6 5h12v3h-4.2v11h-3.6V8H6V5Z"/>',
        '<path fill="none" stroke="{accent}" stroke-width="2" stroke-linecap="round" d="M16 16h4M18 14v4"/>',
    ),
    ToolMode.IMAGE: _svg(
        '<rect fill="none" stroke="{ink}" stroke-width="1.8" x="3" y="5" width="18" height="14" rx="2"/>',
        '<circle fill="{accent}" cx="8.5" cy="10" r="1.8"/>',
        '<path fill="{accent}" d="M4 17l5-5 3 3 3-4 5 6H4Z"/>',
    ),
    ToolMode.EDIT_TEXT: _svg(
        '<path fill="{ink}" d="M5 4h3l1.5 7L11 4h3l-2.8 12H8.2L5 4Z"/>',
        '<path fill="none" stroke="{accent}" stroke-width="2" stroke-linecap="round" d="M13 18 19 10"/>',
    ),
    ToolMode.REDACT: _svg(
        '<rect fill="{ink}" x="4" y="8" width="16" height="5" rx="1"/>',
        '<path fill="none" stroke="{ink}" stroke-width="2" stroke-linecap="round" d="M5 17h8"/>',
    ),
    ToolMode.ERASE: _svg(
        '<path fill="{ink}" d="M6.5 14.5 13 4.5l4.5 3-6.5 10H6.5Z"/>',
        '<path fill="{accent}" d="M6.5 14.5h8.5l1 2.5H5.5Z"/>',
        '<path fill="none" stroke="{ink}" stroke-width="1.8" stroke-linecap="round" d="M4 20h12"/>',
    ),
    ToolMode.DELETE_ANNOT: _svg(
        '<rect fill="{accent}" x="3" y="10" width="11" height="4" rx="1"/>',
        '<path fill="none" stroke="{ink}" stroke-width="2.2" stroke-linecap="round" '
        'd="M14 7 20 17M20 7l-6 10"/>',
    ),
}


# ----------------------------------------------------------------------
# Rasterisation
# ----------------------------------------------------------------------
def _coloured_svg(template: str, scheme: str, accent_override: Optional[str]) -> bytes:
    # Ink/accent come from the quiet-paper theme tokens (teal brand accent).
    ink = theme_color("icon", scheme)
    accent = accent_override or theme_color("accent", scheme)
    return template.format(ink=ink, accent=accent).encode("utf-8")


def _build_icon(template: str, scheme: str, accent_override: Optional[str] = None) -> QIcon:
    """Rasterise SVG at every UI size × screen DPR (exact physical match)."""
    renderer = QSvgRenderer(QByteArray(_coloured_svg(template, scheme, accent_override)))
    if not renderer.isValid():
        return QIcon()

    dpr = _device_pixel_ratio()
    icon = QIcon()
    for logical in _SIZES:
        physical = max(1, int(round(logical * dpr)))
        image = QImage(physical, physical, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        renderer.render(painter, QRectF(0, 0, physical, physical))
        painter.end()
        pixmap = QPixmap.fromImage(image)
        # Intentionally no setDevicePixelRatio: availableSizes must report
        # physical pixels so Qt's matcher finds an exact hit.
        for mode in (QIcon.Mode.Normal, QIcon.Mode.Active, QIcon.Mode.Selected):
            icon.addPixmap(pixmap, mode, QIcon.State.Off)
            icon.addPixmap(pixmap, mode, QIcon.State.On)
    return icon


def tool_icon(mode: ToolMode, scheme: str, accent: Optional[str] = None) -> QIcon:
    dpr = _device_pixel_ratio()
    key = f"tool:{mode.value}:{scheme}:{accent or ''}:dpr{dpr:.2f}"
    if key not in _cache:
        template = TOOL_SVGS.get(mode)
        if template is None:
            return QIcon()
        _cache[key] = _build_icon(template, scheme, accent)
    return _cache[key]


def action_icon(name: str, scheme: str) -> QIcon:
    dpr = _device_pixel_ratio()
    key = f"action:{name}:{scheme}:dpr{dpr:.2f}"
    if key not in _cache:
        template = ACTION_SVGS.get(name)
        if template is None:
            return QIcon()
        _cache[key] = _build_icon(template, scheme, None)
    return _cache[key]


def swatch_icon(rgb, size: int = 40) -> QIcon:
    dpr = _device_pixel_ratio()
    physical = max(1, int(round(size * dpr)))
    image = QImage(physical, physical, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    from PySide6.QtGui import QBrush, QPen
    painter.setPen(QPen(QColor(120, 120, 120), max(1, int(1.5 * dpr))))
    painter.setBrush(QBrush(QColor.fromRgbF(*rgb)))
    margin = 3 * dpr
    painter.drawEllipse(QRectF(margin, margin, physical - 2 * margin, physical - 2 * margin))
    painter.end()
    icon = QIcon()
    icon.addPixmap(QPixmap.fromImage(image))
    return icon


def clear_cache() -> None:
    _cache.clear()
