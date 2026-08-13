"""
gui/results.py

The results dashboard. For One-to-One it shows a single comparison summary;
for One-to-Many it shows the aggregate summary plus one action card per
comparison, each reusing the existing detailed-report/export pipeline.
"""

from PySide6.QtCore import Qt, Signal, Property, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QScrollArea, QGridLayout, QFileDialog
)
from PySide6.QtGui import QPainter, QPen, QColor, QFont

from styles.theme import Colors, Fonts, Spacing, Radius, Anim, Icons, IconSize, render_icon
from backend.reporting import ReportBuilder
from backend.reporting.exporter import (
    export_report,
    build_report_filename,
    build_save_file_filter,
    resolve_export_extension,
)
from gui.settings_manager import get_export_config
from gui.result_utils import derive_student_identity



class ScoreRingWidget(QWidget):
    """Custom painted radial progress ring for the similarity score."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(220, 220)
        self._value = 0
        self._target = 0
        self._color = QColor(Colors.ACCENT)
        
        self.anim = QPropertyAnimation(self, b"value")
        self.anim.setDuration(800)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)

    def getValue(self):
        return self._value

    def setValue(self, v):
        self._value = v
        self.update()

    value = Property(float, getValue, setValue)

    def set_score(self, target: int, color_hex: str):
        self._target = target
        self._color = QColor(color_hex)
        self.anim.stop()
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(float(target))
        self.anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect().adjusted(16, 16, -16, -16)

        # Background track
        pen_bg = QPen(QColor(Colors.BORDER))
        pen_bg.setWidth(12)
        pen_bg.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_bg)
        painter.drawArc(rect, 0, 360 * 16)
        
        # Foreground progress arc
        pen_fg = QPen(self._color)
        pen_fg.setWidth(12)
        pen_fg.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_fg)
        
        # 0 degrees is 3 o'clock in Qt. We want to start at top (90 deg, or 90*16).
        # Progress goes clockwise, which means negative angles.
        span_angle = int(-self._value * 3.6 * 16)
        painter.drawArc(rect, 90 * 16, span_angle)

        # Center text
        painter.setPen(QColor(Colors.TEXT_PRIMARY))
        font = QFont(Fonts.FAMILY, Fonts.SIZE_DISPLAY, QFont.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, f"{int(self._value)}%")


class InfoCard(QFrame):
    """A clean metric card with icon, label, and value."""
    def __init__(self, icon_svg: str, title: str, value: str, parent=None):
        super().__init__(parent)
        self.setObjectName("CardHoverable")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(render_icon(icon_svg, Colors.ACCENT, IconSize.LG))
        layout.addWidget(icon_lbl, alignment=Qt.AlignTop)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        value_label = QLabel(value)
        value_label.setStyleSheet(f"font-size: {Fonts.SIZE_H2}px; font-weight: 700; color: {Colors.TEXT_PRIMARY}; background: transparent;")
        text_layout.addWidget(value_label)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_MUTED}; background: transparent;")
        text_layout.addWidget(title_label)
        
        layout.addLayout(text_layout)
        layout.addStretch()


def _risk_color_for_score(score: int) -> str:
    """Shared risk colouring so multi rows match the top-level risk badge."""
    if score >= 70:
        return Colors.DANGER
    if score >= 40:
        return Colors.WARNING
    return Colors.SUCCESS


class ComparisonRowCard(QFrame):
    """One selectable comparison in a One-to-Many result list.

    Actions (Detailed Report / Generate Report) re-emit the pair's raw
    ComparisonResult so the existing single-comparison pipeline is reused.
    """
    detailed_requested = Signal(object)
    export_requested = Signal(object)

    def __init__(self, title, similarity_pct, confidence, matches, error,
                 error_message="", raw_result=None, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.raw_result = raw_result

        lay = QHBoxLayout(self)
        lay.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        lay.setSpacing(Spacing.LG)

        # Identity
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        name_lbl = QLabel(title)
        name_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_BODY_LG}px; font-weight: 600; "
            f"color: {Colors.TEXT_PRIMARY}; background: transparent;"
        )
        text_col.addWidget(name_lbl)
        if error:
            err_lbl = QLabel(f"FAILED — {error_message}")
            err_lbl.setWordWrap(True)
            err_lbl.setStyleSheet(
                f"font-size: {Fonts.SIZE_SMALL}px; color: {Colors.DANGER}; "
                f"background: transparent;"
            )
            text_col.addWidget(err_lbl)
        lay.addLayout(text_col)
        lay.addStretch()

        # Metrics
        if error:
            sim_val, conf_val, match_val = "--", "--", "--"
        else:
            sim_val, conf_val, match_val = f"{similarity_pct}%", confidence, str(matches)
        metrics = QHBoxLayout()
        metrics.setSpacing(Spacing.XL)
        metrics.addLayout(self._metric("Similarity", sim_val, _risk_color_for_score(similarity_pct)))
        metrics.addLayout(self._metric("Confidence", conf_val, Colors.ACCENT))
        metrics.addLayout(self._metric("Matches", match_val, Colors.TEXT_SECONDARY))
        lay.addLayout(metrics)

        # Actions
        actions = QHBoxLayout()
        actions.setSpacing(Spacing.SM)
        det_btn = QPushButton("Detailed Report")
        det_btn.setObjectName("SecondaryButton")
        det_btn.setCursor(Qt.PointingHandCursor)
        gen_btn = QPushButton("Generate Report")
        gen_btn.setObjectName("PrimaryButton")
        gen_btn.setCursor(Qt.PointingHandCursor)
        if error:
            det_btn.setEnabled(False)
            gen_btn.setEnabled(False)
        det_btn.clicked.connect(lambda: self.detailed_requested.emit(self.raw_result))
        gen_btn.clicked.connect(lambda: self.export_requested.emit(self.raw_result))
        actions.addWidget(det_btn)
        actions.addWidget(gen_btn)
        lay.addLayout(actions)

    @staticmethod
    def _metric(label, value, color):
        col = QVBoxLayout()
        col.setSpacing(0)
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_H2}px; font-weight: 700; "
            f"color: {color}; background: transparent;"
        )
        col.addWidget(val_lbl)
        cap_lbl = QLabel(label)
        cap_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_SMALL}px; color: {Colors.TEXT_MUTED}; "
            f"background: transparent;"
        )
        col.addWidget(cap_lbl)
        return col


class ResultsScreen(QWidget):

    restart_requested = Signal()
    new_check_requested = Signal()
    back_requested = Signal()
    report_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_raw_result = None
        self._last_result_dict = None
        self._is_summary_mode = False
        # Keep strong refs to all active animations so Qt doesn't GC them
        self._active_anims: list = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)

        self.root = QVBoxLayout(container)
        self.root.setContentsMargins(Spacing.XXXL, Spacing.XXL, Spacing.XXXL, Spacing.XXL)
        self.root.setSpacing(Spacing.XL)
        self.root.setAlignment(Qt.AlignTop)

        # -- top bar ---------------------------------------------------------
        top_bar = QHBoxLayout()
        top_bar.setSpacing(Spacing.MD)

        self.back_btn = QPushButton("Back to Dashboard")
        self.back_btn.setObjectName("GhostButton")
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.setIcon(render_icon(Icons.ARROW_LEFT, Colors.TEXT_PRIMARY, IconSize.SM))
        self.back_btn.setVisible(False)
        self.back_btn.clicked.connect(self.back_requested.emit)
        top_bar.addWidget(self.back_btn)

        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        self.title_label = QLabel("Cross-Checking Results")
        self.title_label.setStyleSheet(
            f"font-size: {Fonts.SIZE_H2}px; font-weight: 600; color: {Colors.TEXT_PRIMARY};"
        )
        title_block.addWidget(self.title_label)
        self.subtitle_label = QLabel("")
        self.subtitle_label.setVisible(False)
        self.subtitle_label.setStyleSheet(
            f"font-size: {Fonts.SIZE_SMALL}px; color: {Colors.TEXT_MUTED};"
        )
        title_block.addWidget(self.subtitle_label)
        top_bar.addLayout(title_block)
        top_bar.addStretch()

        self.new_check_button = QPushButton("New Check")
        self.new_check_button.setObjectName("SecondaryButton")
        self.new_check_button.setCursor(Qt.PointingHandCursor)
        self.new_check_button.clicked.connect(self.new_check_requested.emit)
        top_bar.addWidget(self.new_check_button)
        self.root.addLayout(top_bar)

        # -- hero score section ------------------------------------------------
        hero_layout = QVBoxLayout()
        hero_layout.setAlignment(Qt.AlignCenter)
        hero_layout.setSpacing(Spacing.MD)

        self.score_ring = ScoreRingWidget()
        hero_layout.addWidget(self.score_ring, alignment=Qt.AlignCenter)

        self.risk_badge = QLabel()
        self.risk_badge.setAlignment(Qt.AlignCenter)
        self.risk_badge.setContentsMargins(Spacing.LG, Spacing.XS, Spacing.LG, Spacing.XS)
        hero_layout.addWidget(self.risk_badge, alignment=Qt.AlignCenter)

        self.root.addLayout(hero_layout)

        # -- info cards grid -----------------------------------------------------
        self.info_grid = QGridLayout()
        self.info_grid.setSpacing(Spacing.LG)
        self.root.addLayout(self.info_grid)

        # -- One-to-Many comparison list ---------------------------------------
        self.multi_header = QLabel("Comparison Results")
        self.multi_header.setStyleSheet(
            f"font-size: {Fonts.SIZE_H3}px; font-weight: 600; color: {Colors.TEXT_PRIMARY};"
        )
        self.multi_header.setVisible(False)
        self.root.addWidget(self.multi_header)

        self.multi_container = QWidget()
        self.multi_container.setVisible(False)
        self.multi_list = QVBoxLayout(self.multi_container)
        self.multi_list.setContentsMargins(0, 0, 0, 0)
        self.multi_list.setSpacing(Spacing.MD)
        self.multi_list.setAlignment(Qt.AlignTop)
        self.root.addWidget(self.multi_container)

        # -- AI summary card ---------------------------------------------------
        self.summary_card = QFrame()
        self.summary_card.setObjectName("Card")
        # Custom left border for summary
        self.summary_card.setStyleSheet(f"""
            #Card {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BORDER};
                border-left: 3px solid {Colors.ACCENT};
                border-radius: {Radius.LG}px;
            }}
        """)
        summary_layout = QVBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        summary_layout.setSpacing(Spacing.SM)

        summary_header = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(render_icon(Icons.LAYERS, Colors.ACCENT, IconSize.SM))
        summary_header.addWidget(icon)
        
        summary_title = QLabel("AI SUMMARY")
        summary_title.setStyleSheet(f"font-size: {Fonts.SIZE_SMALL}px; font-weight: 700; letter-spacing: 1px; color: {Colors.ACCENT};")
        summary_header.addWidget(summary_title)
        summary_header.addStretch()
        summary_layout.addLayout(summary_header)

        self.summary_text = QLabel("")
        self.summary_text.setWordWrap(True)
        self.summary_text.setStyleSheet(f"font-size: {Fonts.SIZE_BODY_LG}px; color: {Colors.TEXT_PRIMARY};")
        summary_layout.addWidget(self.summary_text)

        self.root.addWidget(self.summary_card)
        
        self.root.addSpacing(Spacing.LG)

        # -- report actions --------------------------------------------------
        report_actions_row = QHBoxLayout()
        
        self.generate_report_btn = QPushButton("Generate Report")
        self.generate_report_btn.setObjectName("PrimaryButton")
        self.generate_report_btn.setIcon(render_icon(Icons.FILE, "#FFFFFF", IconSize.SM))
        self.generate_report_btn.setCursor(Qt.PointingHandCursor)
        self.generate_report_btn.clicked.connect(self.generate_report)
        report_actions_row.addWidget(self.generate_report_btn)
        
        self.detailed_report_btn = QPushButton("Detailed Report")
        self.detailed_report_btn.setObjectName("SecondaryButton")
        self.detailed_report_btn.setIcon(render_icon(Icons.FILE, Colors.TEXT_PRIMARY, IconSize.SM))
        self.detailed_report_btn.setCursor(Qt.PointingHandCursor)
        self.detailed_report_btn.clicked.connect(self.detailed_report)
        report_actions_row.addWidget(self.detailed_report_btn)
        
        report_actions_row.addStretch()
        
        self.root.addLayout(report_actions_row)
        self.root.addSpacing(Spacing.LG)

        # -- bottom actions --------------------------------------------------
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        self.restart_button = QPushButton("Run Another Check")
        self.restart_button.setObjectName("SecondaryButton")
        self.restart_button.setCursor(Qt.PointingHandCursor)
        self.restart_button.setMinimumWidth(220)
        self.restart_button.clicked.connect(self.restart_requested.emit)
        bottom_row.addWidget(self.restart_button)
        bottom_row.addStretch()
        self.root.addLayout(bottom_row)

    def generate_report(self):
        if self._last_raw_result:
            self._export_raw(self._last_raw_result, include_right=self._is_summary_mode)

    def _export_raw(self, raw_result, include_right=False):
        model = ReportBuilder.build(raw_result)
        export_cfg = get_export_config()
        default_fmt = export_cfg.get("export_format", "pdf")
        assignment_name = model.left_document.title or "Assignment"
        if include_right and model.right_document and model.right_document.title:
            assignment_name = f"{assignment_name} vs {model.right_document.title}"
        suggested_name = build_report_filename(assignment_name, default_fmt)

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Generate Report", suggested_name,
            build_save_file_filter(default_fmt)
        )

        if not file_path:
            return  # Exit cleanly if user cancels dialog

        file_path, ext = resolve_export_extension(file_path, selected_filter, default_fmt)

        out_file = export_report(model, file_path, ext, options=export_cfg)
        from gui.notifications import notify_report_exported
        notify_report_exported(out_file)

    def detailed_report(self):
        if self._last_raw_result:
            self.report_requested.emit(self._last_raw_result)

    def _on_pair_detailed(self, raw_result):
        if raw_result:
            self.report_requested.emit(raw_result)

    def _on_pair_export(self, raw_result):
        if raw_result:
            self._export_raw(raw_result, include_right=True)

    def _clear_multi_list(self):
        while self.multi_list.count():
            item = self.multi_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _build_multi_rows(self, result: dict):
        pairs = result.get("pairs", [])
        if not pairs:
            self.multi_header.setVisible(False)
            self.multi_container.setVisible(False)
            return

        reference_name = ""
        first_raw = pairs[0].get("raw_result")
        if first_raw and getattr(first_raw, "doc_a", None):
            reference_name = first_raw.doc_a.file_name
        self.multi_header.setText(
            f"Comparison Results" + (f" — Reference: {reference_name}" if reference_name else "")
        )
        self.multi_header.setVisible(True)

        self._clear_multi_list()
        for idx, pair in enumerate(pairs):
            raw = pair.get("raw_result")
            error = bool(pair.get("error"))
            title = f"Submission {idx + 1}"
            if raw and getattr(raw, "doc_b", None):
                title = raw.doc_b.file_name
            row = ComparisonRowCard(
                title=title,
                similarity_pct=int(pair.get("score", 0)),
                confidence=pair.get("confidence_score", "0%"),
                matches=pair.get("similar_paragraphs", 0),
                error=error,
                error_message=pair.get("summary", "Analysis failed"),
                raw_result=raw,
            )
            row.detailed_requested.connect(self._on_pair_detailed)
            row.export_requested.connect(self._on_pair_export)
            self.multi_list.addWidget(row)
        self.multi_container.setVisible(True)


    def display_results(self, result: dict, dashboard_summary: bool = False):
        self._last_raw_result = result.get("raw_result")
        self._last_result_dict = result
        self._is_summary_mode = dashboard_summary
        # Kill any running animations from a previous run
        for anim in self._active_anims:
            anim.stop()
        self._active_anims.clear()

        is_error = result.get("error", False)
        is_multi = bool(result.get("pairs"))
        self._clear_multi_list()
        
        # Set risk badge
        self.risk_badge.setText(result.get("risk_level", "Unknown"))
        risk_color = result.get("risk_color", Colors.BORDER)
        
        self.risk_badge.setStyleSheet(f"""
            background-color: #20{risk_color[1:]}; 
            color: {risk_color};
            border: 1px solid #40{risk_color[1:]};
            border-radius: {Radius.PILL}px;
            font-size: {Fonts.SIZE_BODY}px;
            font-weight: 600;
        """)

        self.summary_text.setText(result.get("summary", ""))

        # Dashboard summary mode: refit the top bar + bottom actions to the
        # per-assignment context (Back to Dashboard, labelled title/subtitle).
        self.back_btn.setVisible(dashboard_summary)
        self.new_check_button.setVisible(not dashboard_summary)
        self.restart_button.setVisible(not dashboard_summary)
        self.title_label.setText(
            "Assignment Summary" if dashboard_summary else "Cross-Checking Results"
        )
        fresh = dashboard_summary and not is_error
        self.subtitle_label.setVisible(fresh)
        if fresh:
            raw = result.get("raw_result")
            student = getattr(raw, "doc_b", None) or getattr(raw, "doc_a", None)
            name, sid = derive_student_identity(student)
            ref = getattr(getattr(raw, "doc_a", None), "file_name", None) or ""
            parts = []
            if name:
                parts.append(f"Student — {name}" + (f"  ·  {sid}" if sid else ""))
            if ref:
                parts.append(f"Reference — {ref}")
            self.subtitle_label.setText("  ·  ".join(parts) if parts else "")

        if is_multi:
            # One-to-Many: summary dashboard plus one identical action card per
            # comparison. Each row reuses the single-comparison report pipeline.
            if is_error:
                self.score_ring.setVisible(False)
            else:
                self.score_ring.setVisible(True)
                self.score_ring.set_score(result.get("score", 0), risk_color)
            self.generate_report_btn.setVisible(False)
            self.detailed_report_btn.setVisible(False)
            self._build_multi_rows(result)
            return

        self.multi_header.setVisible(False)
        self.multi_container.setVisible(False)

        if is_error:
            self.score_ring.setVisible(False)
            self.generate_report_btn.setVisible(False)
            self.detailed_report_btn.setVisible(False)
        else:
            self.score_ring.setVisible(True)
            self.generate_report_btn.setVisible(True)
            self.detailed_report_btn.setVisible(True)
            self.score_ring.set_score(result.get("score", 0), risk_color)

        # clear and rebuild info cards
        while self.info_grid.count():
            item = self.info_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if is_error:
            return

        cards_data = [
            (Icons.FILE,        "Matching Sections",  str(result.get("matching_sections", 0))),
            (Icons.LAYERS,      "Similar Paragraphs", str(result.get("similar_paragraphs", 0))),
            (Icons.CLOCK,       "Processing Time",    result.get("processing_time", "0s")),
            (Icons.CHECK,       "Confidence",         result.get("confidence_score", "0%")),
        ]

        for i, (icon_svg, title, value) in enumerate(cards_data):
            card = InfoCard(icon_svg, title, value)

            # Start collapsed – animating maximumHeight avoids any QSS interference.
            # The card is parented, styled and laid out normally; only its height
            # is temporarily clamped so it slides in from 0.
            card.setMaximumHeight(0)
            self.info_grid.addWidget(card, i // 2, i % 2)

            # Slide-reveal: 0 → 90px (cards are naturally ~72-80px tall)
            reveal = QPropertyAnimation(card, b"maximumHeight")
            reveal.setDuration(420)
            reveal.setStartValue(0)
            reveal.setEndValue(90)
            reveal.setEasingCurve(QEasingCurve.OutCubic)
            # After animation ends, free the height constraint
            reveal.finished.connect(lambda c=card: c.setMaximumHeight(16777215))

            self._active_anims.append(reveal)

            # Staggered start
            delay = 80 + i * 160
            QTimer.singleShot(delay, reveal.start)
