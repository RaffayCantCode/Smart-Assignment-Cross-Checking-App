"""
main.py

Entry point. Wires the five screens (home, upload, loading, results, settings)
together via a QStackedWidget. Implements a smooth page transition inline.
"""

import sys
import pydoc

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QPoint
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QGraphicsOpacityEffect

from styles.theme import build_stylesheet, Anim, apply_theme
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
        
        self.stack = None
        self._fade_out_anim = None
        self._fade_in_anim = None
        self._slide_in_anim = None
        self._anim_group = None
        self._next_widget = None

        self.setup_ui(initial=True)

    def setup_ui(self, initial=False):
        if self.stack is not None:
            self.stack.deleteLater()

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
            # Setup opacity effect for transitions
            effect = QGraphicsOpacityEffect(screen)
            effect.setOpacity(1.0)
            screen.setGraphicsEffect(effect)

        # -- wire navigation ---------------------------------------------------
        self.home_screen.mode_confirmed.connect(self._go_to_upload)
        self.home_screen.settings_requested.connect(self._go_to_settings)
        
        self.upload_screen.back_requested.connect(self._go_to_home)
        self.upload_screen.start_requested.connect(self._go_to_loading)
        
        self.loading_screen.finished.connect(self._go_to_results)
        
        self.results_screen.restart_requested.connect(self._go_to_home)
        self.results_screen.new_check_requested.connect(self._go_to_home)
        
        self.settings_screen.back_requested.connect(self._go_to_home)
        self.settings_screen.theme_changed.connect(self._on_theme_changed)

        if initial:
            self.stack.setCurrentWidget(self.home_screen)
        else:
            self.stack.setCurrentWidget(self.settings_screen)

    def _on_theme_changed(self, mode: str):
        apply_theme(mode)
        QApplication.instance().setStyleSheet(build_stylesheet())
        self.setup_ui(initial=False)

    def _fade_to(self, target_widget):
        """Smoothly transitions to the target widget via fade and slide."""
        current_widget = self.stack.currentWidget()
        if current_widget == target_widget:
            return

        self._next_widget = target_widget

        # 1. Fade out current widget
        current_effect = current_widget.graphicsEffect()
        self._fade_out_anim = QPropertyAnimation(current_effect, b"opacity")
        self._fade_out_anim.setDuration(Anim.PAGE // 2)
        self._fade_out_anim.setStartValue(1.0)
        self._fade_out_anim.setEndValue(0.0)
        self._fade_out_anim.setEasingCurve(QEasingCurve.OutCubic)
        
        self._fade_out_anim.finished.connect(self._on_fade_out_finished)
        self._fade_out_anim.start()

    def _on_fade_out_finished(self):
        # 2. Swap widget
        self.stack.setCurrentWidget(self._next_widget)
        
        # 3. Animate new widget in (fade + slide up slightly)
        effect = self._next_widget.graphicsEffect()
        effect.setOpacity(0.0)
        
        self._fade_in_anim = QPropertyAnimation(effect, b"opacity")
        self._fade_in_anim.setDuration(Anim.PAGE)
        self._fade_in_anim.setStartValue(0.0)
        self._fade_in_anim.setEndValue(1.0)
        self._fade_in_anim.setEasingCurve(QEasingCurve.OutCubic)
        
        self._fade_in_anim.start()

    # -- navigation handlers --------------------------------------------------
    def _go_to_home(self):
        self.home_screen.reset()
        self._fade_to(self.home_screen)

    def _go_to_settings(self):
        self._fade_to(self.settings_screen)

    def _go_to_upload(self, mode: str):
        self.upload_screen.configure_for_mode(mode)
        self._fade_to(self.upload_screen)

    def _go_to_loading(self, payload: dict):
        self._fade_to(self.loading_screen)
        # Start immediately so animation plays during fade-in
        self.loading_screen.start(payload)

    def _go_to_results(self, payload: dict):
        self.results_screen.display_results(payload)
        self._fade_to(self.results_screen)


def main():
    app = QApplication(sys.argv)
    apply_theme("System")
    app.setStyleSheet(build_stylesheet())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

