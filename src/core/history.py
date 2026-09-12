"""Undo/redo history for document edits.

PyMuPDF has no native undo, so history is kept as full in-memory
snapshots of the document. Serializing is cheap (a few milliseconds for
a typical file), but the snapshots are the whole PDF, so the stack is
bounded by both depth and total bytes.
"""

from __future__ import annotations

from typing import List, Optional

from src.constants import MAX_UNDO_MB, MAX_UNDO_STEPS
from src.core.document import Document
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentHistory:
    """Bounded undo/redo stack of document snapshots."""

    def __init__(
        self,
        max_steps: int = MAX_UNDO_STEPS,
        max_bytes: int = MAX_UNDO_MB * 1024 * 1024,
    ) -> None:
        self._undo: List[bytes] = []
        self._redo: List[bytes] = []
        self._max_steps = max(1, max_steps)
        self._max_bytes = max_bytes

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    @property
    def depth(self) -> int:
        return len(self._undo)

    def clear(self) -> None:
        """Drop all history, e.g. when a new document is opened."""
        self._undo.clear()
        self._redo.clear()

    def record(self, document: Document) -> None:
        """Snapshot ``document`` before an edit is applied.

        A new edit invalidates the redo stack, matching what users expect
        from every other editor.
        """
        try:
            payload = document.snapshot()
        except Exception as exc:  # noqa: BLE001 - history must never block an edit
            logger.warning("Skipping undo snapshot: %s", exc)
            return
        self._undo.append(payload)
        self._redo.clear()
        self._trim()
        logger.debug("Undo depth %s (%.1f MB)", len(self._undo), self._total_mb())

    def undo(self, document: Document) -> bool:
        """Restore the previous snapshot. Returns False if nothing to undo."""
        if not self._undo:
            return False
        current = self._safe_snapshot(document)
        payload = self._undo.pop()
        document.restore(payload)
        if current is not None:
            self._redo.append(current)
        logger.info("Undo applied (%s steps left)", len(self._undo))
        return True

    def redo(self, document: Document) -> bool:
        """Re-apply an undone snapshot. Returns False if nothing to redo."""
        if not self._redo:
            return False
        current = self._safe_snapshot(document)
        payload = self._redo.pop()
        document.restore(payload)
        if current is not None:
            self._undo.append(current)
        logger.info("Redo applied (%s steps left)", len(self._redo))
        return True

    @staticmethod
    def _safe_snapshot(document: Document) -> Optional[bytes]:
        try:
            return document.snapshot()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not snapshot current state: %s", exc)
            return None

    def _total_bytes(self) -> int:
        return sum(len(item) for item in self._undo) + sum(len(i) for i in self._redo)

    def _total_mb(self) -> float:
        return self._total_bytes() / (1024 * 1024)

    def _trim(self) -> None:
        while len(self._undo) > self._max_steps:
            self._undo.pop(0)
        while self._undo and self._total_bytes() > self._max_bytes:
            self._undo.pop(0)
