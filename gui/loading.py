"""
gui/loading.py

Simulated "AI processing" screen.
A QTimer ticks a progress value up and swaps status states.
The visual uses a DualRing with a soft glow and a checklist of stages.
"""

from PySide6.QtCore import Qt, QTimer, Property, QPropertyAnimation, Signal, QEasingCurve, QThread
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, 
    QSizePolicy, QGraphicsDropShadowEffect, QFrame
)
from PySide6.QtGui import QPainter, QPen, QColor, QBrush

from styles.theme import Colors, Fonts, Spacing, Icons, IconSize, render_icon, Anim
from backend.assignment_analyzer import AssignmentAnalyzer


STATUS_STEPS = [
    (0, "Preparing assignments"),
    (20, "Reading documents"),
    (40, "Extracting text"),
    (60, "Analyzing content"),
    (80, "Comparing similarities"),
    (100, "Generating results"),
]

class AnalysisWorker(QThread):
    progress_updated = Signal(int, str)
    analysis_finished = Signal(dict)

    def __init__(self, payload: dict, parent=None):
        super().__init__(parent)
        self.payload = payload

    def run(self):
        try:
            analyzer = AssignmentAnalyzer(progress_callback=self.progress_updated.emit)
            
            mode = self.payload.get("mode", "one_to_one")
            files = self.payload.get("files", {})
            
            if mode == "one_to_one":
                file_path_1 = files.get("student_1")
                file_path_2 = files.get("student_2")
                if not file_path_1 or not file_path_2:
                    result = analyzer._error_result("Missing files for one-to-one comparison.")
                else:
                    result = analyzer.analyze_one_to_one(file_path_1, file_path_2)
            else:
                result = analyzer._error_result(f"Mode {mode} not yet supported by backend.")
                
            self.analysis_finished.emit(result)
        except Exception as e:
            import traceback
            err_msg = f"Worker thread crashed: {e}\n{traceback.format_exc()}"
            # Ensure it conforms to the expected result dictionary
            err_result = {
                "score": 0,
                "risk_level": "Error",
                "risk_color": "#E63946",
                "matching_sections": 0,
                "similar_paragraphs": 0,
                "processing_time": "0.0s",
                "confidence_score": "0%",
                "summary": err_msg,
                "error": True
            }
            self.analysis_finished.emit(err_result)


class DualRing(QWidget):
    """Dual rotating rings with a center icon and subtle glow."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 140)
        self._angle = 0
        
        self.anim = QPropertyAnimation(self, b"angle")
        self.anim.setStartValue(0)
        self.anim.setEndValue(360)
        self.anim.setDuration(Anim.RING)
        self.anim.setLoopCount(-1)

        # Center icon
        self.center_icon = render_icon(Icons.LAYERS, Colors.ACCENT, IconSize.XL)

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
        
        rect_outer = self.rect().adjusted(10, 10, -10, -10)
        rect_inner = self.rect().adjusted(24, 24, -24, -24)

        # Background track
        pen_bg = QPen(QColor(Colors.BORDER))
        pen_bg.setWidth(6)
        pen_bg.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_bg)
        painter.drawArc(rect_outer, 0, 360 * 16)
        
        # Outer ring
        pen_outer = QPen(QColor(Colors.ACCENT))
        pen_outer.setWidth(6)
        pen_outer.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_outer)
        start_angle_outer = int(-self._angle * 16)
        painter.drawArc(rect_outer, start_angle_outer, 120 * 16)
        
        # Inner ring (spins opposite direction)
        pen_inner = QPen(QColor(Colors.ACCENT_HOVER))
        pen_inner.setWidth(4)
        pen_inner.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_inner)
        start_angle_inner = int(self._angle * 16)
        painter.drawArc(rect_inner, start_angle_inner, 90 * 16)

        # Center icon
        icon_x = (self.width() - self.center_icon.width()) // 2
        icon_y = (self.height() - self.center_icon.height()) // 2
        painter.drawPixmap(icon_x, icon_y, self.center_icon)


class StageChecklist(QWidget):
    """Vertical checklist showing processing stages."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(Spacing.MD)
        self.layout.setAlignment(Qt.AlignCenter)
        
        self.rows = []
        for _, text in STATUS_STEPS:
            row = self._create_row(text)
            self.rows.append(row)
            self.layout.addLayout(row["layout"])
            
    def _create_row(self, text: str):
        layout = QHBoxLayout()
        layout.setSpacing(Spacing.MD)
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(render_icon(Icons.CLOCK, Colors.TEXT_MUTED, IconSize.MD))
        layout.addWidget(icon_lbl)
        
        text_lbl = QLabel(text)
        text_lbl.setStyleSheet(f"font-size: {Fonts.SIZE_BODY_LG}px; color: {Colors.TEXT_MUTED};")
        layout.addWidget(text_lbl)
        
        return {"layout": layout, "icon": icon_lbl, "text": text_lbl}
        
    def update_progress(self, current_stage_idx: int):
        for i, row in enumerate(self.rows):
            if i < current_stage_idx:
                # Completed
                row["icon"].setPixmap(render_icon(Icons.CHECK, Colors.SUCCESS, IconSize.MD))
                row["text"].setStyleSheet(f"font-size: {Fonts.SIZE_BODY_LG}px; color: {Colors.TEXT_SECONDARY};")
            elif i == current_stage_idx:
                # In progress
                row["icon"].setPixmap(render_icon(Icons.REFRESH, Colors.ACCENT, IconSize.MD))
                row["text"].setStyleSheet(f"font-size: {Fonts.SIZE_BODY_LG}px; font-weight: 500; color: {Colors.TEXT_PRIMARY};")
            else:
                # Pending
                row["icon"].setPixmap(render_icon(Icons.CLOCK, Colors.TEXT_MUTED, IconSize.MD))
                row["text"].setStyleSheet(f"font-size: {Fonts.SIZE_BODY_LG}px; color: {Colors.TEXT_MUTED};")


class LoadingScreen(QWidget):

    finished = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._payload = {}
        self._progress = 0
        self._worker = None

        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignCenter)
        root.setSpacing(Spacing.XXXL)

        # -- Top visual ----------------------------------------------------
        top_area = QVBoxLayout()
        top_area.setAlignment(Qt.AlignCenter)
        top_area.setSpacing(Spacing.MD)
        
        self.ring = DualRing()
        top_area.addWidget(self.ring, alignment=Qt.AlignCenter)

        self.percent_label = QLabel("0%")
        self.percent_label.setAlignment(Qt.AlignCenter)
        self.percent_label.setStyleSheet(
            f"font-size: {Fonts.SIZE_DISPLAY}px; font-weight: 700; color: {Colors.TEXT_PRIMARY};"
        )
        top_area.addWidget(self.percent_label)
        
        root.addLayout(top_area)
        
        # -- Progress bar ---------------------------------------------------
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(400)
        self.progress_bar.setTextVisible(False)
        root.addWidget(self.progress_bar, alignment=Qt.AlignCenter)

        # -- Checklist -------------------------------------------------------
        self.checklist = StageChecklist()
        root.addWidget(self.checklist, alignment=Qt.AlignCenter)

    def start(self, payload: dict):
        self._payload = payload
        self._progress = 0
        self.percent_label.setText("0%")
        self.progress_bar.setValue(0)
        self.checklist.update_progress(0)
        
        self.ring.start()
        
        # Start real background worker
        self._worker = AnalysisWorker(payload)
        self._worker.progress_updated.connect(self._on_progress_update)
        self._worker.analysis_finished.connect(self._on_analysis_finished)
        self._worker.start()

    def _on_progress_update(self, percent: int, message: str):
        self._progress = percent
        self.progress_bar.setValue(self._progress)
        self.percent_label.setText(f"{self._progress}%")

        # Find current stage index based on threshold
        current_idx = 0
        for i, (threshold, text) in enumerate(STATUS_STEPS):
            if self._progress >= threshold:
                current_idx = i

        self.checklist.update_progress(current_idx)

    def _on_analysis_finished(self, result: dict):
        self.ring.stop()
        self.progress_bar.setValue(100)
        self.percent_label.setText("100%")
        self.checklist.update_progress(len(STATUS_STEPS))
        self.finished.emit(result)

