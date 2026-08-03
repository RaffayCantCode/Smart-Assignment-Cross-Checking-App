"""
gui/report/report_header.py

Fixed header card for the Detailed Report page.

Displays: document A vs B names, generation timestamp, a short
report ID, a compact similarity arc, and a colour-coded risk badge.
Kept as a separate module so ReportScreen can hot-swap it on
each load_report() call using the same swap-at-index pattern as
the existing _StatsBar.
"""

import uuid
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen, QColor, QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QWidget

from styles.theme import Colors, Fonts, Spacing, Radius
from backend.reporting.model import ReportModel


class _ScoreMini(QWidget):
    """
    Compact painted arc showing the similarity percentage.

    Uses the same QPainter approach as ScoreRingWidget in results.py
    for visual consistency, but at a smaller fixed size (68×68 px)
    appropriate for the header card.
    """

    def __init__(self, score: int, color: str, parent=None):
        super().__init__(parent)
        self._score = score
        self._color = QColor(color)
        self.setFixedSize(68, 68)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(8, 8, -8, -8)

        # Background track
        pen_bg = QPen(QColor(Colors.BORDER))
        pen_bg.setWidth(7)
        pen_bg.setCapStyle(Qt.RoundCap)
        p.setPen(pen_bg)
        p.drawArc(rect, 0, 360 * 16)

        # Foreground progress arc (starts at 12 o'clock, clockwise)
        pen_fg = QPen(self._color)
        pen_fg.setWidth(7)
        pen_fg.setCapStyle(Qt.RoundCap)
        p.setPen(pen_fg)
        p.drawArc(rect, 90 * 16, int(-self._score * 3.6 * 16))

        # Percentage label
        p.setPen(QColor(Colors.TEXT_PRIMARY))
        p.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SMALL, QFont.Bold))
        p.drawText(rect, Qt.AlignCenter, f"{self._score}%")


class ReportHeader(QFrame):
    """
    A card widget pinned to the top of the Detailed Report page.

    Shows: Document A vs B names · generation timestamp ·
    report ID · similarity arc · risk badge.

    Constructed fresh on each load_report() call so the data
    always reflects the currently loaded comparison.
    """

    def __init__(self, model: ReportModel, parent=None):
        super().__init__(parent)
        self.setObjectName("ReportHeaderCard")

        s = model.statistics
        score = s.similarity_percent

        if score < 40:
            risk_label, risk_color = "LOW RISK", Colors.LOW_RISK
        elif score < 70:
            risk_label, risk_color = "MEDIUM RISK", Colors.MEDIUM_RISK
        else:
            risk_label, risk_color = "HIGH RISK", Colors.HIGH_RISK

        report_id = uuid.uuid4().hex[:8].upper()
        timestamp = datetime.now().strftime("%d %b %Y  ·  %H:%M")

        self.setStyleSheet(f"""
            #ReportHeaderCard {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: {Radius.LG}px;
            }}
        """)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        outer.setSpacing(Spacing.LG)

        # Similarity arc
        outer.addWidget(_ScoreMini(score, risk_color), alignment=Qt.AlignVCenter)

        # Document titles + meta column
        meta = QVBoxLayout()
        meta.setSpacing(Spacing.XS)

        title_row = QHBoxLayout()
        title_row.setSpacing(Spacing.SM)
        for text, muted in [
            (model.left_document.title or "Document A", False),
            ("vs", True),
            (model.right_document.title or "Document B", False),
        ]:
            lbl = QLabel(text)
            if muted:
                lbl.setStyleSheet(
                    f"font-size: {Fonts.SIZE_BODY}px; "
                    f"color: {Colors.TEXT_MUTED}; background: transparent;"
                )
            else:
                lbl.setStyleSheet(
                    f"font-size: {Fonts.SIZE_H3}px; font-weight: 700; "
                    f"color: {Colors.TEXT_PRIMARY}; background: transparent;"
                )
            title_row.addWidget(lbl)
        title_row.addStretch()
        meta.addLayout(title_row)

        sub_row = QHBoxLayout()
        sub_row.setSpacing(Spacing.LG)
        for text in [f"Generated {timestamp}", f"Report ID: {report_id}"]:
            lbl = QLabel(text)
            lbl.setStyleSheet(
                f"font-size: {Fonts.SIZE_SMALL}px; "
                f"color: {Colors.TEXT_MUTED}; background: transparent;"
            )
            sub_row.addWidget(lbl)
        sub_row.addStretch()
        meta.addLayout(sub_row)

        outer.addLayout(meta, 1)

        # Risk badge — same pill style used in ResultsScreen
        badge = QLabel(risk_label)
        badge.setAlignment(Qt.AlignCenter)
        badge.setContentsMargins(Spacing.MD, Spacing.XS, Spacing.MD, Spacing.XS)
        badge.setStyleSheet(f"""
            background-color: #20{risk_color[1:]};
            color: {risk_color};
            border: 1px solid #40{risk_color[1:]};
            border-radius: {Radius.PILL}px;
            font-size: {Fonts.SIZE_SMALL}px;
            font-weight: 700;
            letter-spacing: 1px;
        """)
        outer.addWidget(badge, alignment=Qt.AlignVCenter)
