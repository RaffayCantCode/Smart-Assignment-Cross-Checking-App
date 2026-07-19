"""
gui/results.py

The results dashboard. All values shown here are placeholder/fake data.
"""

import random

from PySide6.QtCore import Qt, Signal, Property, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QScrollArea, QGridLayout, QGraphicsOpacityEffect
)
from PySide6.QtGui import QPainter, QPen, QColor, QFont

from styles.theme import Colors, Fonts, Spacing, Radius, Anim, Icons, IconSize, render_icon


def _fake_result_for(payload: dict) -> dict:
    """Generate deterministic-looking fake analysis results."""
    random.seed(len(str(payload.get("files", {}))) or 1)
    score = random.randint(35, 96)

    if score >= 75:
        risk_level, risk_color = "High Similarity", Colors.HIGH_RISK
    elif score >= 45:
        risk_level, risk_color = "Moderate Similarity", Colors.MEDIUM_RISK
    else:
        risk_level, risk_color = "Low Similarity", Colors.LOW_RISK

    return {
        "score": score,
        "risk_level": risk_level,
        "risk_color": risk_color,
        "matching_sections": random.randint(3, 14),
        "similar_paragraphs": random.randint(2, 20),
        "processing_time": f"{random.uniform(1.2, 4.8):.1f}s",
        "confidence_score": f"{random.randint(80, 99)}%",
        "summary": (
            "Both assignments contain highly similar concepts and multiple matching "
            "sections. Manual review is recommended."
        ) if score >= 75 else (
            "Some overlapping phrasing and structure were detected, but overall the "
            "assignments appear largely independent."
        ),
    }


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


class ResultsScreen(QWidget):

    restart_requested = Signal()
    new_check_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

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
        title = QLabel("Cross-Checking Results")
        title.setStyleSheet(f"font-size: {Fonts.SIZE_H2}px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
        top_bar.addWidget(title)
        top_bar.addStretch()

        new_check_button = QPushButton("New Check")
        new_check_button.setObjectName("SecondaryButton")
        new_check_button.setCursor(Qt.PointingHandCursor)
        new_check_button.clicked.connect(self.new_check_requested.emit)
        top_bar.addWidget(new_check_button)
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
        self._info_cards = []

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
        restart_button = QPushButton("Run Another Check")
        restart_button.setObjectName("SecondaryButton")
        restart_button.setCursor(Qt.PointingHandCursor)
        restart_button.setMinimumWidth(220)
        restart_button.clicked.connect(self.restart_requested.emit)
        bottom_row.addWidget(restart_button)
        bottom_row.addStretch()
        self.root.addLayout(bottom_row)

    def generate_report(self):
        # Placeholder for report generation
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Generate Report", "Report generation will be implemented in a future update.")

    def detailed_report(self):
        # Placeholder for detailed report
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Detailed Report", "Detailed report view will be available in a future update.")


    def display_results(self, payload: dict):
        result = _fake_result_for(payload)

        # Set risk badge
        self.risk_badge.setText(result["risk_level"])
        self.risk_badge.setStyleSheet(f"""
            background-color: {result['risk_color']}20; /* 20 is low alpha hex */
            color: {result['risk_color']};
            border: 1px solid {result['risk_color']}40;
            border-radius: {Radius.PILL}px;
            font-size: {Fonts.SIZE_BODY}px;
            font-weight: 600;
        """)

        self.summary_text.setText(result["summary"])
        self.score_ring.set_score(result["score"], result["risk_color"])

        # clear and rebuild info cards
        self._info_cards.clear()
        while self.info_grid.count():
            item = self.info_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cards_data = [
            (Icons.FILE, "Matching Sections", str(result["matching_sections"])),
            (Icons.LAYERS, "Similar Paragraphs", str(result["similar_paragraphs"])),
            (Icons.CLOCK, "Processing Time", result["processing_time"]),
            (Icons.CHECK, "Confidence", result["confidence_score"]),
        ]
        
        for i, (icon_svg, title, value) in enumerate(cards_data):
            card = InfoCard(icon_svg, title, value)
            
            # Setup fade-in effect
            effect = QGraphicsOpacityEffect(card)
            effect.setOpacity(0.0)
            card.setGraphicsEffect(effect)
            
            anim = QPropertyAnimation(effect, b"opacity")
            anim.setDuration(400)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            
            # Staggered start
            QTimer.singleShot(i * 100, anim.start)
            
            self._info_cards.append((card, anim))
            self.info_grid.addWidget(card, i // 2, i % 2)
