"""Dialogs for PDF security operations - password and encryption."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pymupdf as fitz
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from src.core.document import Document
from src.services.security_service import SecurityService, SecurityInfo
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SecurityInfoDialog(QDialog):
    """Dialog showing security information about a PDF."""

    def __init__(self, document: Document, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Document Security")
        self.resize(400, 300)

        layout = QVBoxLayout(self)

        info = SecurityService.get_security_info(document)

        status_group = QGroupBox("Encryption Status")
        status_layout = QFormLayout(status_group)

        encrypted_label = QLabel("Yes" if info.is_encrypted else "No")
        encrypted_label.setStyleSheet(
            "color: orange; font-weight: bold;" if info.is_encrypted else "color: green;"
        )
        status_layout.addRow("Encrypted:", encrypted_label)

        if info.is_encrypted:
            status_layout.addRow("Method:", QLabel(info.encryption_method))
        layout.addWidget(status_group)

        if info.is_encrypted:
            perms_group = QGroupBox("Permissions")
            perms_layout = QFormLayout(perms_group)
            perms_layout.addRow("Print:", self._perm_label(info.can_print))
            perms_layout.addRow("Copy text:", self._perm_label(info.can_copy))
            perms_layout.addRow("Modify:", self._perm_label(info.can_modify))
            perms_layout.addRow("Annotate:", self._perm_label(info.can_annotate))
            layout.addWidget(perms_group)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _perm_label(self, allowed: bool) -> QLabel:
        label = QLabel("Allowed" if allowed else "Denied")
        label.setStyleSheet("color: green;" if allowed else "color: red;")
        return label


class SetPasswordDialog(QDialog):
    """Dialog for setting PDF password protection."""

    def __init__(self, document: Document, parent=None) -> None:
        super().__init__(parent)
        self._document = document

        self.setWindowTitle("Set Password Protection")
        self.resize(450, 350)

        layout = QVBoxLayout(self)

        info_label = QLabel(
            "Protect this PDF with passwords. The user password is required to open "
            "the document. The owner password allows changing permissions."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666;")
        layout.addWidget(info_label)

        passwords_group = QGroupBox("Passwords")
        passwords_layout = QFormLayout(passwords_group)

        self._user_password = QLineEdit()
        self._user_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._user_password.setPlaceholderText("Required to open the PDF")
        passwords_layout.addRow("User password:", self._user_password)

        self._confirm_user = QLineEdit()
        self._confirm_user.setEchoMode(QLineEdit.EchoMode.Password)
        passwords_layout.addRow("Confirm:", self._confirm_user)

        self._owner_password = QLineEdit()
        self._owner_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._owner_password.setPlaceholderText("Optional, defaults to user password")
        passwords_layout.addRow("Owner password:", self._owner_password)

        layout.addWidget(passwords_group)

        perms_group = QGroupBox("Permissions (for users without owner password)")
        perms_layout = QVBoxLayout(perms_group)
        self._print_check = QCheckBox("Allow printing")
        self._print_check.setChecked(True)
        perms_layout.addWidget(self._print_check)
        self._copy_check = QCheckBox("Allow copying text and images")
        self._copy_check.setChecked(True)
        perms_layout.addWidget(self._copy_check)
        self._modify_check = QCheckBox("Allow modifying the document")
        perms_layout.addWidget(self._modify_check)
        self._annotate_check = QCheckBox("Allow adding annotations")
        self._annotate_check.setChecked(True)
        perms_layout.addWidget(self._annotate_check)
        layout.addWidget(perms_group)

        encryption_group = QGroupBox("Encryption")
        encryption_layout = QFormLayout(encryption_group)
        self._encryption_box = QComboBox()
        self._encryption_box.addItem("AES 256-bit (recommended)", fitz.PDF_ENCRYPT_AES_256)
        self._encryption_box.addItem("AES 128-bit", fitz.PDF_ENCRYPT_AES_128)
        self._encryption_box.addItem("RC4 128-bit (legacy)", fitz.PDF_ENCRYPT_RC4_128)
        encryption_layout.addRow("Method:", self._encryption_box)
        layout.addWidget(encryption_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: red;")
        self._error_label.hide()
        layout.addWidget(self._error_label)

    def _on_accept(self) -> None:
        user_pw = self._user_password.text()
        confirm = self._confirm_user.text()

        if not user_pw:
            self._show_error("User password is required")
            return

        if user_pw != confirm:
            self._show_error("Passwords do not match")
            return

        self.accept()

    def _show_error(self, message: str) -> None:
        self._error_label.setText(message)
        self._error_label.show()

    def get_settings(self) -> dict:
        """Get the password and encryption settings."""
        permissions = 0
        if self._print_check.isChecked():
            permissions |= fitz.PDF_PERM_PRINT
        if self._copy_check.isChecked():
            permissions |= fitz.PDF_PERM_COPY
        if self._modify_check.isChecked():
            permissions |= fitz.PDF_PERM_MODIFY
        if self._annotate_check.isChecked():
            permissions |= fitz.PDF_PERM_ANNOTATE

        return {
            "user_password": self._user_password.text(),
            "owner_password": self._owner_password.text() or self._user_password.text(),
            "permissions": permissions,
            "encryption": self._encryption_box.currentData(),
        }


class PasswordPromptDialog(QDialog):
    """Dialog prompting for a password to open an encrypted PDF."""

    def __init__(self, filename: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Password Required")
        self.resize(350, 150)

        layout = QVBoxLayout(self)

        info = QLabel(f"The file '{filename}' is password protected.\nEnter the password to open it:")
        info.setWordWrap(True)
        layout.addWidget(info)

        self._password_edit = QLineEdit()
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_edit.setPlaceholderText("Password")
        self._password_edit.returnPressed.connect(self.accept)
        layout.addWidget(self._password_edit)

        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: red;")
        self._error_label.hide()
        layout.addWidget(self._error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def password(self) -> str:
        return self._password_edit.text()

    def show_error(self, message: str = "Incorrect password") -> None:
        self._error_label.setText(message)
        self._error_label.show()
        self._password_edit.selectAll()
        self._password_edit.setFocus()
