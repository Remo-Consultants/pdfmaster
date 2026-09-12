"""Editing tool modes shared by the viewer and the main window."""

from __future__ import annotations

from enum import Enum
from typing import Dict, Set, Tuple


class ToolMode(str, Enum):
    """What a mouse drag on the page currently means."""

    PAN = "pan"
    HIGHLIGHT = "highlight"
    UNDERLINE = "underline"
    STRIKEOUT = "strikeout"
    NOTE = "note"
    PEN = "pen"
    SHAPE = "shape"
    TEXT = "text"
    IMAGE = "image"
    EDIT_TEXT = "edit_text"
    REDACT = "redact"
    ERASE = "erase"
    DELETE_ANNOT = "delete_annot"


TOOL_LABELS: Dict[ToolMode, str] = {
    ToolMode.PAN: "Select",
    ToolMode.HIGHLIGHT: "Highlight",
    ToolMode.UNDERLINE: "Underline",
    ToolMode.STRIKEOUT: "Strikeout",
    ToolMode.NOTE: "Sticky Note",
    ToolMode.PEN: "Pen",
    ToolMode.SHAPE: "Rectangle",
    ToolMode.TEXT: "Add Text",
    ToolMode.IMAGE: "Add Image",
    ToolMode.EDIT_TEXT: "Edit Text",
    ToolMode.REDACT: "Redact",
    ToolMode.ERASE: "Erase",
    ToolMode.DELETE_ANNOT: "Delete Markup",
}

TOOL_HINTS: Dict[ToolMode, str] = {
    ToolMode.PAN: "Scroll and read. No edits are made.",
    ToolMode.HIGHLIGHT: "Drag across text to highlight it.",
    ToolMode.UNDERLINE: "Drag across text to underline it.",
    ToolMode.STRIKEOUT: "Drag across text to strike it out.",
    ToolMode.NOTE: "Click where you want to attach a note.",
    ToolMode.PEN: "Draw freehand with the mouse held down.",
    ToolMode.SHAPE: "Drag to draw a rectangle outline.",
    ToolMode.TEXT: "Drag a box, then type the text to add.",
    ToolMode.IMAGE: "Drag a box, then choose an image to place.",
    ToolMode.EDIT_TEXT: "Drag over existing text to rewrite it.",
    ToolMode.REDACT: "Drag over content to remove it permanently.",
    ToolMode.ERASE: "Drag over content to white it out.",
    ToolMode.DELETE_ANNOT: "Click a highlight or note to delete it.",
}

# Tools that need a dragged rectangle.
DRAG_TOOLS: Set[ToolMode] = {
    ToolMode.HIGHLIGHT,
    ToolMode.UNDERLINE,
    ToolMode.STRIKEOUT,
    ToolMode.SHAPE,
    ToolMode.TEXT,
    ToolMode.IMAGE,
    ToolMode.EDIT_TEXT,
    ToolMode.REDACT,
    ToolMode.ERASE,
}

# Tools that act on a single click.
CLICK_TOOLS: Set[ToolMode] = {ToolMode.NOTE, ToolMode.DELETE_ANNOT}

# Tools that collect a freehand path.
FREEHAND_TOOLS: Set[ToolMode] = {ToolMode.PEN}

# Tools whose overlay should be drawn filled rather than as an outline.
FILLED_PREVIEW: Set[ToolMode] = {
    ToolMode.HIGHLIGHT,
    ToolMode.REDACT,
    ToolMode.ERASE,
}


# Tools shown on the toolbar. The rest stay in the Tools menu so the
# toolbar does not overflow into a chevron on a normal-sized window.
PRIMARY_TOOLS: Tuple[ToolMode, ...] = (
    ToolMode.PAN,
    ToolMode.HIGHLIGHT,
    ToolMode.UNDERLINE,
    ToolMode.NOTE,
    ToolMode.PEN,
    ToolMode.TEXT,
    ToolMode.EDIT_TEXT,
    ToolMode.REDACT,
    ToolMode.DELETE_ANNOT,
)


def is_interactive(mode: ToolMode) -> bool:
    """Whether the tool reacts to mouse input on the page."""
    return mode in DRAG_TOOLS or mode in CLICK_TOOLS or mode in FREEHAND_TOOLS
