"""Security service for PDF password protection and digital signatures."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import pymupdf as fitz

from src.core.document import Document
from src.utils.exceptions import PageOperationError
from src.utils.logger import get_logger

logger = get_logger(__name__)


USER_PERMISSION = fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY | fitz.PDF_PERM_ANNOTATE


class SecurityInfo:
    """Information about a PDF's security settings."""

    def __init__(
        self,
        is_encrypted: bool = False,
        has_user_password: bool = False,
        has_owner_password: bool = False,
        permissions: int = -1,
        encryption_method: str = "None",
    ) -> None:
        self.is_encrypted = is_encrypted
        self.has_user_password = has_user_password
        self.has_owner_password = has_owner_password
        self.permissions = permissions
        self.encryption_method = encryption_method

    @property
    def can_print(self) -> bool:
        return not self.is_encrypted or (self.permissions & fitz.PDF_PERM_PRINT)

    @property
    def can_copy(self) -> bool:
        return not self.is_encrypted or (self.permissions & fitz.PDF_PERM_COPY)

    @property
    def can_modify(self) -> bool:
        return not self.is_encrypted or (self.permissions & fitz.PDF_PERM_MODIFY)

    @property
    def can_annotate(self) -> bool:
        return not self.is_encrypted or (self.permissions & fitz.PDF_PERM_ANNOTATE)

    def __str__(self) -> str:
        if not self.is_encrypted:
            return "Not encrypted"
        perms = []
        if self.can_print:
            perms.append("print")
        if self.can_copy:
            perms.append("copy")
        if self.can_modify:
            perms.append("modify")
        if self.can_annotate:
            perms.append("annotate")
        return f"Encrypted ({self.encryption_method}), permissions: {', '.join(perms) or 'none'}"


class SecurityService:
    """Service for PDF security operations."""

    ENCRYPTION_METHODS = {
        fitz.PDF_ENCRYPT_KEEP: "Keep existing",
        fitz.PDF_ENCRYPT_NONE: "None",
        fitz.PDF_ENCRYPT_RC4_40: "RC4 40-bit",
        fitz.PDF_ENCRYPT_RC4_128: "RC4 128-bit",
        fitz.PDF_ENCRYPT_AES_128: "AES 128-bit",
        fitz.PDF_ENCRYPT_AES_256: "AES 256-bit",
    }

    @staticmethod
    def get_security_info(document: Document) -> SecurityInfo:
        """Get security information about a document."""
        with document.transaction(mark_modified=False) as pdf:
            is_encrypted = pdf.is_encrypted
            if not is_encrypted:
                return SecurityInfo()

            permissions = pdf.permissions
            method = "Unknown"

            metadata = pdf.metadata or {}
            encryption = metadata.get("encryption", "")
            if "AES-256" in encryption or "AES256" in encryption:
                method = "AES 256-bit"
            elif "AES-128" in encryption or "AES128" in encryption:
                method = "AES 128-bit"
            elif "RC4" in encryption:
                method = "RC4"
            elif encryption:
                method = encryption

            return SecurityInfo(
                is_encrypted=True,
                has_user_password=True,
                has_owner_password=True,
                permissions=permissions,
                encryption_method=method,
            )

    @staticmethod
    def set_password(
        document: Document,
        output_path: Path,
        user_password: str = "",
        owner_password: str = "",
        permissions: int = USER_PERMISSION,
        encryption: int = fitz.PDF_ENCRYPT_AES_256,
    ) -> Path:
        """Save the document with password protection.

        Args:
            document: The document to protect.
            output_path: Where to save the protected PDF.
            user_password: Password required to open the document (can be empty).
            owner_password: Password required to change permissions.
            permissions: Bitfield of allowed operations.
            encryption: Encryption algorithm to use.

        Returns:
            Path to the saved file.
        """
        if not owner_password:
            owner_password = user_password

        with document.transaction(mark_modified=False) as pdf:
            try:
                pdf.save(
                    output_path,
                    encryption=encryption,
                    user_pw=user_password,
                    owner_pw=owner_password,
                    permissions=permissions,
                )
            except Exception as exc:
                logger.error("Failed to set password: %s", exc)
                raise PageOperationError(f"Could not encrypt PDF: {exc}") from exc

        logger.info(
            "Saved encrypted PDF to %s (encryption=%s)",
            output_path,
            SecurityService.ENCRYPTION_METHODS.get(encryption, "unknown"),
        )
        return output_path

    @staticmethod
    def remove_password(
        document: Document,
        output_path: Path,
    ) -> Path:
        """Save the document without password protection.

        The document must already be opened/authenticated.
        """
        with document.transaction(mark_modified=False) as pdf:
            try:
                pdf.save(
                    output_path,
                    encryption=fitz.PDF_ENCRYPT_NONE,
                )
            except Exception as exc:
                logger.error("Failed to remove password: %s", exc)
                raise PageOperationError(f"Could not decrypt PDF: {exc}") from exc

        logger.info("Saved decrypted PDF to %s", output_path)
        return output_path

    @staticmethod
    def open_with_password(file_path: Path, password: str) -> Document:
        """Open a password-protected PDF.

        Note: This creates a temporary decrypted copy in memory.
        """
        try:
            pdf = fitz.open(file_path)
            if pdf.is_encrypted:
                if not pdf.authenticate(password):
                    pdf.close()
                    raise PageOperationError("Incorrect password")
            doc = Document.__new__(Document)
            doc._logger = logger
            doc._pdf = pdf
            doc._file_path = Path(file_path).resolve()
            doc._filename = doc._file_path.name
            doc._is_open = True
            doc._modified = False
            doc._was_repaired = False
            doc._lock = __import__("threading").RLock()
            return doc
        except PageOperationError:
            raise
        except Exception as exc:
            logger.error("Failed to open encrypted PDF: %s", exc)
            raise PageOperationError(f"Could not open encrypted PDF: {exc}") from exc


class SignatureInfo:
    """Information about a digital signature."""

    def __init__(
        self,
        signer: str = "",
        signed_at: str = "",
        reason: str = "",
        location: str = "",
        is_valid: bool = False,
        covers_whole_document: bool = False,
    ) -> None:
        self.signer = signer
        self.signed_at = signed_at
        self.reason = reason
        self.location = location
        self.is_valid = is_valid
        self.covers_whole_document = covers_whole_document


class SignatureService:
    """Service for digital signature operations.

    Note: Full signature validation requires additional dependencies
    (pyhanko, endesive, etc.). This provides basic signature detection.
    """

    @staticmethod
    def get_signatures(document: Document) -> list:
        """List digital signatures in the document."""
        signatures = []

        with document.transaction(mark_modified=False) as pdf:
            for page_num in range(pdf.page_count):
                page = pdf.load_page(page_num)
                for widget in page.widgets() or []:
                    if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                        info = SignatureInfo(
                            signer=widget.field_value or "Unknown",
                            reason=getattr(widget, "signature_reason", "") or "",
                            location=getattr(widget, "signature_location", "") or "",
                        )
                        signatures.append(info)

        logger.debug("Found %d signature field(s)", len(signatures))
        return signatures

    @staticmethod
    def has_signatures(document: Document) -> bool:
        """Check if the document contains any signature fields."""
        return len(SignatureService.get_signatures(document)) > 0

    @staticmethod
    def add_signature_field(
        document: Document,
        page_num: int,
        rect: Tuple[float, float, float, float],
        field_name: str = "Signature",
    ) -> None:
        """Add an empty signature field to a page.

        Note: This creates the field but does not sign it.
        Actual signing requires a certificate and is platform-dependent.
        """
        with document.transaction() as pdf:
            page = pdf.load_page(page_num)
            widget = fitz.Widget()
            widget.field_type = fitz.PDF_WIDGET_TYPE_SIGNATURE
            widget.field_name = field_name
            widget.rect = fitz.Rect(rect)
            widget.border_color = (0, 0, 0)
            widget.border_width = 1
            page.add_widget(widget)

        logger.info("Added signature field '%s' to page %d", field_name, page_num + 1)
