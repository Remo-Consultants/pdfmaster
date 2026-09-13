"""Document processors: annotations, page structure, content, forms, redaction."""

from src.processors.annotations import AnnotationProcessor
from src.processors.content import ContentEditor
from src.processors.forms import FormProcessor
from src.processors.page_ops import PageOrganizer
from src.processors.redaction import Redactor
from src.processors.watermark import WatermarkProcessor, STAMP_PRESETS

__all__ = [
    "AnnotationProcessor",
    "ContentEditor",
    "FormProcessor",
    "PageOrganizer",
    "Redactor",
    "STAMP_PRESETS",
    "WatermarkProcessor",
]
