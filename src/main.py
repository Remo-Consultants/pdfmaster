"""PDFMaster application entry point."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Allow `python src/main.py` in addition to `python -m src.main`.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from src.constants import APP_ICON_PATH, APP_NAME, APP_VERSION, ORGANIZATION_NAME
from src.ui.main_window import MainWindow
from src.utils.logger import get_logger, setup_logging


def main() -> int:
    """Create the Qt application, show the main window, and run the event loop."""
    setup_logging(level=logging.INFO)
    logger = get_logger("main")
    logger.info("Starting %s %s", APP_NAME, APP_VERSION)

    # Helps Windows pin the custom icon on the taskbar instead of python.exe.
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                f"{ORGANIZATION_NAME}.{APP_NAME}"
            )
        except Exception:  # noqa: BLE001 - never block startup on branding
            pass

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(ORGANIZATION_NAME)

    if APP_ICON_PATH.is_file():
        icon = QIcon(str(APP_ICON_PATH))
        app.setWindowIcon(icon)
    else:
        logger.warning("App icon missing at %s", APP_ICON_PATH)

    window = MainWindow()
    window.show()

    exit_code = app.exec()
    logger.info("Exiting %s with code %s", APP_NAME, exit_code)
    return int(exit_code)


if __name__ == "__main__":
    sys.exit(main())
