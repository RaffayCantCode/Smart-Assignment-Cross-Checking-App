"""
gui/loading.py

Simulated "AI processing" screen.
A QTimer ticks a progress value up and swaps status states.
The visual uses a DualRing with a soft glow and a checklist of stages.
"""

from PySide6.QtCore import Qt, QTimer, Property, QPropertyAnimation, Signal, QEasingCurve, QThread, QRectF, QByteArray
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QSizePolicy, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QFrame
)
from PySide6.QtGui import QPainter, QPen, QColor, QBrush
from PySide6.QtSvg import QSvgRenderer

from styles.theme import Colors, Fonts, Spacing, Icons, IconSize, render_icon, Anim
from backend.assignment_analyzer import AssignmentAnalyzer
from backend.engines.base import EngineConfig
from gui.settings_manager import get_analysis_config

# Minimum milliseconds to display each stage so the user can read it
_STEP_DISPLAY_MS = 1200

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
    stages_updated = Signal(list)
    analysis_finished = Signal(dict)

    def __init__(self, payload: dict, parent=None):
        super().__init__(parent)
        self.payload = payload

    def run(self):
        try:
            # Emit immediately so the UI never sits silent before first progress
            self.progress_updated.emit(2, "Preparing assignments...")
            cfg = get_analysis_config()
            engine_config = EngineConfig(
                similarity_threshold=cfg["similarity_threshold"],
                sentence_threshold=cfg["sentence_threshold"],
                enable_sentence_matching=cfg["enable_sentence_matching"],
                max_paragraphs=cfg["max_paragraphs"],
                batch_size=cfg["batch_size"],
                ignore_quotations=cfg["ignore_quotations"],
                ignore_references=cfg["ignore_references"],
                ignore_bibliography=cfg["ignore_bibliography"],
                ignore_formatting=cfg["ignore_formatting"],
                max_threads=cfg["max_threads"],
                enable_cache=cfg["enable_cache"],
            )
            self.progress_updated.emit(4, "Initializing analysis engine...")
            analyzer = AssignmentAnalyzer(
                progress_callback=self.progress_updated.emit,
                stages_callback=self.stages_updated.emit,
                config=engine_config,
            )
            
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

        # Pre-parse the SVG once; we'll render it directly in paintEvent
        svg_src = Icons.LAYERS.replace("{color}", Colors.ACCENT)
        self._svg_renderer = QSvgRenderer(QByteArray(svg_src.encode('utf-8')))

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

        # Center icon – rendered directly from SVG for crisp vector quality
        icon_size = 36
        icon_x = (self.width()  - icon_size) / 2
        icon_y = (self.height() - icon_size) / 2
        icon_rect = QRectF(icon_x, icon_y, icon_size, icon_size)
        self._svg_renderer.render(painter, icon_rect)


class StageRow(QWidget):
    """
    A single step row in the loading checklist.
    Uses text glyphs for state indicators (dash → dot → tick) so there is
    zero risk of QSS+QGraphicsEffect conflicts on the row widget itself.
    The indicator label gets a brief opacity fade when a step activates.
    """

    _PENDING_GLYPH = "–"      # en-dash
    _ACTIVE_GLYPH  = "●"      # filled circle
    _DONE_GLYPH    = "✓"      # check mark

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(300)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(Spacing.LG, Spacing.SM, Spacing.LG, Spacing.SM)
        lay.setSpacing(Spacing.MD)
        lay.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Indicator glyph (no QSS background → safe for QGraphicsOpacityEffect)
        self.indicator = QLabel(self._PENDING_GLYPH)
        self.indicator.setFixedWidth(20)
        self.indicator.setAlignment(Qt.AlignCenter)
        self.indicator.setStyleSheet(
            f"font-size: {Fonts.SIZE_BODY_LG}px; font-weight: 700; color: {Colors.TEXT_MUTED};"
        )
        lay.addWidget(self.indicator)

        self.text_lbl = QLabel(text)
        self.text_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_BODY_LG}px; color: {Colors.TEXT_MUTED};"
        )
        lay.addWidget(self.text_lbl)

        # Opacity effect on indicator label only — safe (no QSS bg on QLabel)
        self._ind_fx = QGraphicsOpacityEffect(self.indicator)
        self._ind_fx.setOpacity(1.0)
        self.indicator.setGraphicsEffect(self._ind_fx)
        self._ind_anim: QPropertyAnimation | None = None

    # ------------------------------------------------------------------
    def _fade_indicator(self, from_val: float = 0.0):
        """Fade the indicator glyph from `from_val` to 1.0."""
        if self._ind_anim:
            self._ind_anim.stop()
        self._ind_fx.setOpacity(from_val)
        self._ind_anim = QPropertyAnimation(self._ind_fx, b"opacity")
        self._ind_anim.setDuration(350)
        self._ind_anim.setStartValue(from_val)
        self._ind_anim.setEndValue(1.0)
        self._ind_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._ind_anim.start()

    def set_done(self):
        if self._ind_anim:
            self._ind_anim.stop()
        self._ind_fx.setOpacity(1.0)
        self.indicator.setText(self._DONE_GLYPH)
        self.indicator.setStyleSheet(
            f"font-size: {Fonts.SIZE_BODY_LG}px; font-weight: 700; color: {Colors.SUCCESS};"
        )
        self.text_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_BODY_LG}px; color: {Colors.TEXT_SECONDARY};"
        )

    def set_active(self):
        self.indicator.setText(self._ACTIVE_GLYPH)
        self.indicator.setStyleSheet(
            f"font-size: {Fonts.SIZE_BODY_LG}px; font-weight: 700; color: {Colors.ACCENT};"
        )
        self.text_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_BODY_LG}px; font-weight: 600; color: {Colors.TEXT_PRIMARY};"
        )
        self._fade_indicator(0.0)   # indicator pulses in

    def set_pending(self):
        if self._ind_anim:
            self._ind_anim.stop()
        self._ind_fx.setOpacity(1.0)
        self.indicator.setText(self._PENDING_GLYPH)
        self.indicator.setStyleSheet(
            f"font-size: {Fonts.SIZE_BODY_LG}px; font-weight: 700; color: {Colors.TEXT_MUTED};"
        )
        self.text_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_BODY_LG}px; color: {Colors.TEXT_MUTED};"
        )


class StageChecklist(QWidget):
    """Vertical checklist showing processing stages."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(Spacing.XS)
        self._lay.setAlignment(Qt.AlignCenter)

        self.rows: list[StageRow] = []
        self.set_stages([text for _, text in STATUS_STEPS])

    def set_stages(self, stages: list[str]):
        for row in self.rows:
            row.deleteLater()
        self.rows.clear()

        for text in stages:
            row = StageRow(text, self)
            self.rows.append(row)
            self._lay.addWidget(row)

    def update_progress(self, current_stage_idx: int):
        for i, row in enumerate(self.rows):
            if i < current_stage_idx:
                row.set_done()
            elif i == current_stage_idx:
                row.set_active()
            else:
                row.set_pending()


class LoadingScreen(QWidget):

    finished = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._payload = {}
        self._progress = 0
        self._worker = None

        # Step sequencer state
        self._next_step: tuple | None = None   # single armed step (coalesced - never backlogged)
        self._current_displayed_idx = 0
        self._step_timer = QTimer(self)
        self._step_timer.setSingleShot(True)
        self._step_timer.timeout.connect(self._advance_step)
        self._pending_result = None            # hold final result until queue drains

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

        # -- Live status message ----------------------------------------------
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setMaximumWidth(500)
        self.status_label.setStyleSheet(
            f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_MUTED};"
        )
        root.addWidget(self.status_label, alignment=Qt.AlignCenter)

        # -- Elapsed-time ticker -----------------------------------------------
        # Ticks every second while the worker runs. Gives continuous visual
        # proof the UI is alive during long phases (model load, OCR).
        self.elapsed_label = QLabel("0s")
        self.elapsed_label.setAlignment(Qt.AlignCenter)
        self.elapsed_label.setStyleSheet(
            f"font-size: {Fonts.SIZE_SMALL}px; color: {Colors.TEXT_MUTED};"
        )
        root.addWidget(self.elapsed_label, alignment=Qt.AlignCenter)

        self._elapsed_seconds = 0
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._tick_elapsed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, payload: dict):
        self._payload = payload
        self._progress = 0
        self._current_displayed_idx = 0
        self._next_step = None
        self._pending_result = None
        self._step_timer.stop()

        self.current_stages = [text for _, text in STATUS_STEPS]
        self.percent_label.setText("0%")
        self.progress_bar.setValue(0)
        self.status_label.setText("")
        self.elapsed_label.setText("0s")
        self._elapsed_seconds = 0
        self._elapsed_timer.start()
        self.checklist.set_stages(self.current_stages)
        self.checklist.update_progress(0)
        
        self.ring.start()
        
        # Start real background worker
        self._worker = AnalysisWorker(payload)
        self._worker.progress_updated.connect(self._on_progress_update)
        self._worker.stages_updated.connect(self._on_stages_updated)
        self._worker.analysis_finished.connect(self._on_analysis_finished)
        self._worker.start()

    # ------------------------------------------------------------------
    # Step sequencer helpers
    # ------------------------------------------------------------------

    def _tick_elapsed(self):
        self._elapsed_seconds += 1
        self.elapsed_label.setText(f"{self._elapsed_seconds}s")

    def _enqueue_step(self, target_idx: int, target_pct: int, message: str):
        """Arm the latest step state. Rapid updates replace (coalesce) the armed
        step instead of building a backlog, so the UI never replays stale
        progress and always converges on the current state quickly."""
        self._next_step = (target_idx, target_pct, message)
        # Fire immediately for the first step if the timer is idle
        if not self._step_timer.isActive():
            self._step_timer.start(0)

    def _advance_step(self):
        """Called by _step_timer – display the armed step (if any)."""
        if self._next_step is None:
            # No pending work – if we were holding a final result, emit it now
            if self._pending_result is not None:
                self._emit_finished()
            return

        target_idx, target_pct, message = self._next_step
        self._next_step = None

        # Update live status text so the user always sees what's happening
        if message:
            self.status_label.setText(message)

        # Update progress bar and label
        self.progress_bar.setValue(target_pct)
        self.percent_label.setText(f"{target_pct}%")

        # Only advance the checklist when the stage index actually changes
        if target_idx != self._current_displayed_idx:
            self._current_displayed_idx = target_idx
            self.checklist.update_progress(target_idx)

        # Keep going while a new step is armed or we're holding a final result
        if self._next_step is not None or self._pending_result is not None:
            self._step_timer.start(_STEP_DISPLAY_MS)

    # ------------------------------------------------------------------
    # Worker signal handlers
    # ------------------------------------------------------------------

    def _on_stages_updated(self, stages: list[str]):
        self.current_stages = stages
        self.checklist.set_stages(stages)
        self._current_displayed_idx = 0

    def _on_progress_update(self, percent: int, message: str):
        if percent == -1 and message == "OCR_ACTIVE":
            ocr_stages = [
                "Preparing assignments",
                "Opening PDF",
                "Detecting Text Layer",
                "Converting Pages",
                "Running OCR",
                "Cleaning OCR Output",
                "Comparing similarities",
                "Generating results"
            ]
            self._on_stages_updated(ocr_stages)
            return

        # Determine which checklist stage this maps to
        target_idx = self._current_displayed_idx
        found = False
        for i, stage_text in enumerate(self.current_stages):
            if stage_text.lower() in message.lower():
                target_idx = i
                found = True
                break

        if not found and self.current_stages == [text for _, text in STATUS_STEPS]:
            for i, (threshold, _) in enumerate(STATUS_STEPS):
                if percent >= threshold:
                    target_idx = i

        self._enqueue_step(target_idx, percent, message)

    def _on_analysis_finished(self, result: dict):
        if not result.get("error"):
            from gui.notifications import notify_analysis_complete
            notify_analysis_complete(result.get("score", 0))

        # Don't emit finished immediately – let the step queue drain first
        # so every stage is visible for at least _STEP_DISPLAY_MS
        self._pending_result = result
        # Enqueue the "100% / all done" step
        self._enqueue_step(len(self.current_stages), 100, "Finished")
        # Make sure the timer is running so it will eventually call _emit_finished
        if not self._step_timer.isActive():
            self._step_timer.start(_STEP_DISPLAY_MS)

    def _emit_finished(self):
        self._elapsed_timer.stop()
        self.ring.stop()
        self.progress_bar.setValue(100)
        self.percent_label.setText("100%")
        self.checklist.update_progress(len(self.current_stages))
        result = self._pending_result
        self._pending_result = None
        self.finished.emit(result)

