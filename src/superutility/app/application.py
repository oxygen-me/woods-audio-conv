import sys
from PySide6.QtWidgets import QApplication

from app.paths import APP_NAME
from ui.main_window import MainWindow

def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Multimedia Superutility")
    window = MainWindow()
    window.show()
    raise SystemExit(app.exec())
