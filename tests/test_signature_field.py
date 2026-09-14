"""Tests for signature field placement."""

from __future__ import annotations

from src.core.document import Document
from src.services.security_service import SignatureService


def test_add_signature_field(make_pdf) -> None:
    with Document(make_pdf()) as doc:
        SignatureService.add_signature_field(
            doc, 0, (72, 500, 292, 556), field_name="SignHere"
        )
        assert doc.is_modified
        fields = SignatureService.get_signatures(doc)
        assert len(fields) >= 1
