"""
gui/loading.py

Simulated "AI processing" screen. Everything here is fake: a QTimer
ticks a progress value up and swaps status text at thresholds, while
a small custom-painted widget spins to look like an active scan.

When backend integration happens, `start()` is the one method that
needs to change - instead of a QTimer driving progress, real
callbacks/signals from the analysis pipeline would update
`set_progress()` instead.
"""

from PySide6.QtCore import Qt, QTimer, Property, QPropertyAnimation, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QSizePolicy
from PySide6.QtGui import QPainter, QPen, QColor, QFont

from styles.theme import Colors, Fonts

STATUS_STEPS = [
    (0, "Preparing assignments..."),
    (20, "Reading documents..."),
    (40, "Extracting text..."),
    (60, "Analyzing content..."),
    (80, "Comparing similarities..."),
    (100, "Generating results..."),
]


class ScanRing(QWidget):
    """A simple custom-painted rotating arc, purely decorative."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 140)
        self._angle = 0
        self.anim = QPropertyAnimation(self, b"angle")
        self.anim.setStartValue(0)
        self.anim.setEndValue(360)
        self.anim.setDuration(1400)
        self.anim.setLoopCount(-1)

    def getAngle(self):
        return self._angle

    def setAngle(self, value):
        self._angle = value
        self.update()

    angle = Property(int, getAngle, setAngle)

    def start(self):
        self.anim.start()

    def stop(self):
        self.anim.stop()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(10, 10, -10, -10)

        # faint background ring
        pen_bg = QPen(QColor(Colors.BORDER_LIGHT))
        pen_bg.setWidth(8)
        pen_bg.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_bg)
        painter.drawArc(rect, 0, 360 * 16)

        # rotating accent arc
        pen_fg = QPen(QColor(Colors.ACCENT))
        pen_fg.setWidth(8)
        pen_fg.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_fg)
        span = 100 * 16
        start_angle = int(-self._angle * 16)
        painter.drawArc(rect, start_angle, span)

        # center glyph
        painter.setPen(QColor(Colors.TEXT_PRIMARY))
        font = QFont()
        font.setPointSize(20)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, "AI")


class LoadingScreen(QWidget):

    finished = Signal(dict)  # forwards the same payload it was started with

    def __init__(self, parent=None):
        super().__init__(parent)
        self._payload = {}
        self._progress = 0

        self.timer = QTimer(self)
        self.timer.setInterval(160)  # ms per tick -> full run ~ a few seconds
        self.timer.timeout.connect(self._tick)

        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignCenter)
        root.setSpacing(24)

        self.ring = ScanRing()
        root.addWidget(self.ring, alignment=Qt.AlignCenter)

        self.percent_label = QLabel("0%")
        self.percent_label.setAlignment(Qt.AlignCenter)
        self.percent_label.setStyleSheet(
            f"font-size: {Fonts.H1}px; font-weight: 800; color: {Colors.TEXT_PRIMARY};"
        )
        root.addWidget(self.percent_label)

        self.status_label = QLabel(STATUS_STEPS[0][1])
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(
            f"font-size: {Fonts.BODY}px; color: {Colors.TEXT_SECONDARY};"
        )
        root.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(420)
        self.progress_bar.setTextVisible(False)
        root.addWidget(self.progress_bar, alignment=Qt.AlignCenter)

        hint = QLabel("This is a simulated preview - no files are actually being analyzed yet.")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(f"font-size: {Fonts.SMALL}px; color: {Colors.TEXT_MUTED};")
        root.addWidget(hint)

    def start(self, payload: dict):
        """Kick off the fake processing animation."""
        self._payload = payload
        self._progress = 0
        self.percent_label.setText("0%")
        self.status_label.setText(STATUS_STEPS[0][1])
        self.progress_bar.setValue(0)
        self.ring.start()
        self.timer.start()

    def _tick(self):
        self._progress = min(100, self._progress + 4)
        self.progress_bar.setValue(self._progress)
        self.percent_label.setText(f"{self._progress}%")

        current_status = STATUS_STEPS[0][1]
        for threshold, text in STATUS_STEPS:
            if self._progress >= threshold:
                current_status = text
        self.status_label.setText(current_status)

        if self._progress >= 100:
            self.timer.stop()
            self.ring.stop()
            self.finished.emit(self._payload)
