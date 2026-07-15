"""
main.py

Entry point. Run with:

    python main.py

Wires the five screens (home, upload, loading, results, settings)
together via a QStackedWidget. Each screen is a self-contained widget
that only knows how to emit signals about user intent (e.g.
"mode_confirmed", "start_requested") - MainWindow is the only place
that knows about navigation order, so swapping the flow around later
only touches this file.
"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout

from styles.theme import build_stylesheet, Colors
from gui.home import HomeScreen
from gui.upload import UploadScreen
from gui.loading import LoadingScreen
from gui.results import ResultsScreen
from gui.settings import SettingsScreen


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("RootWindow")
        self.setWindowTitle("Smart Assignment Cross-Checking App")
        self.resize(1200, 800)
        self.setMinimumSize(1000, 700)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # -- instantiate screens --------------------------------------------
        self.home_screen = HomeScreen()
        self.upload_screen = UploadScreen()
        self.loading_screen = LoadingScreen()
        self.results_screen = ResultsScreen()
        self.settings_screen = SettingsScreen()

        for screen in (
            self.home_screen,
            self.upload_screen,
            self.loading_screen,
            self.results_screen,
            self.settings_screen,
        ):
            self.stack.addWidget(screen)

        # -- wire navigation ---------------------------------------------------
        self.home_screen.mode_confirmed.connect(self._go_to_upload)
        self.upload_screen.back_requested.connect(self._go_to_home)
        self.upload_screen.start_requested.connect(self._go_to_loading)
        self.loading_screen.finished.connect(self._go_to_results)
        self.results_screen.restart_requested.connect(self._go_to_home)
        self.results_screen.new_check_requested.connect(self._go_to_home)
        self.settings_screen.back_requested.connect(self._go_to_home)

        self.stack.setCurrentWidget(self.home_screen)

    # -- navigation handlers --------------------------------------------------
    def _go_to_home(self):
        self.home_screen.reset()
        self.stack.setCurrentWidget(self.home_screen)

    def _go_to_upload(self, mode: str):
        self.upload_screen.configure_for_mode(mode)
        self.stack.setCurrentWidget(self.upload_screen)

    def _go_to_loading(self, payload: dict):
        self.stack.setCurrentWidget(self.loading_screen)
        self.loading_screen.start(payload)

    def _go_to_results(self, payload: dict):
        self.results_screen.display_results(payload)
        self.stack.setCurrentWidget(self.results_screen)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(build_stylesheet())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
