"""
gui/report/match_sidebar.py

Scrollable sidebar that lists every ReportMatch as a clickable card.

Public API:
  MatchSidebar.match_selected  Signal(int)  — emitted on card click
  MatchSidebar.set_active(index)            — sync highlight from
                                              Prev/Next toolbar navigation

Each _MatchCard has a clear active state (solid Accent left-border +
background shift) and a hover state for the inactive case — addressing
the sidebar visual hierarchy note from the review.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QScrollArea,
)

from styles.theme import Colors, Fonts, Spacing, Radius
from backend.reporting.model import ReportModel, ReportMatch
from .match_colors import get_match_color


_TYPE_COLORS: dict[str, str] = {}


class _MatchCard(QFrame):
    """A single match entry in the sidebar list."""

    clicked = Signal(int)  # emits list index

    def __init__(self, match: ReportMatch, index: int, parent=None):
        super().__init__(parent)
        self.setObjectName("MatchCard")
        self.setCursor(Qt.PointingHandCursor)
        self._index = index
        self._active = False

        color = get_match_color(match.match_id)
        score_pct = min(100, round(match.score * 100))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        layout.setSpacing(2)

        # Row 1: colour swatch + Match ID + type badge
        top = QHBoxLayout()
        swatch = QFrame()
        swatch.setFixedSize(10, 10)
        swatch.setStyleSheet(
            f"background-color: {color}; border-radius: 2px; border: none;"
        )
        top.addWidget(swatch)

        id_lbl = QLabel(f"Match #{match.match_id}")
        id_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_SMALL}px; font-weight: 700; "
            f"color: {Colors.TEXT_PRIMARY}; background: transparent;"
        )
        top.addWidget(id_lbl)
        top.addStretch()

        badge = QLabel(match.type.value.upper())
        badge.setStyleSheet(
            f"font-size: {Fonts.SIZE_SMALL - 1}px; font-weight: 700; "
            f"color: {Colors.TEXT_SECONDARY}; background: {Colors.BG_SURFACE}; "
            f"border-radius: {Radius.SM}px; padding: 1px 6px;"
        )
        top.addWidget(badge)
        layout.addLayout(top)

        # Row 2: Similarity percentage
        score_lbl = QLabel(f"{score_pct}% similarity")
        score_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_SMALL}px; color: {color}; background: transparent;"
        )
        layout.addWidget(score_lbl)

        # Row 3: Document locations
        loc_a = QLabel(f"Doc A: {match.left_paragraph_id}")
        loc_a.setStyleSheet(
            f"font-size: {Fonts.SIZE_SMALL}px; "
            f"color: {Colors.TEXT_MUTED}; background: transparent;"
        )
        layout.addWidget(loc_a)

        loc_b = QLabel(f"Doc B: {match.right_paragraph_id}")
        loc_b.setStyleSheet(
            f"font-size: {Fonts.SIZE_SMALL}px; "
            f"color: {Colors.TEXT_MUTED}; background: transparent;"
        )
        layout.addWidget(loc_b)

        self._apply_style()

    def set_active(self, active: bool):
        if self._active != active:
            self._active = active
            self._apply_style()

    def _apply_style(self):
        # Active: solid Accent left border + soft Accent background tint
        # Inactive: transparent left border with a hover shift on mouse-over
        if self._active:
            self.setStyleSheet(f"""
                #MatchCard {{
                    background-color: {Colors.ACCENT_SOFT};
                    border: 1px solid {Colors.ACCENT};
                    border-left: 3px solid {Colors.ACCENT};
                    border-radius: {Radius.MD}px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                #MatchCard {{
                    background-color: {Colors.BG_SURFACE_ALT};
                    border: 1px solid {Colors.BORDER};
                    border-left: 3px solid transparent;
                    border-radius: {Radius.MD}px;
                }}
                #MatchCard:hover {{
                    background-color: {Colors.BG_HOVER};
                    border-color: {Colors.BORDER_LIGHT};
                }}
            """)

    def mousePressEvent(self, event):
        self.clicked.emit(self._index)
        super().mousePressEvent(event)


class MatchSidebar(QWidget):
    """
    Scrollable list of _MatchCard widgets.

    Emits match_selected(index) when the user clicks a card.
    Call set_active(index) to update the highlighted card from
    external navigation without re-emitting the signal.
    """

    match_selected = Signal(int)

    def __init__(self, model: ReportModel, parent=None):
        super().__init__(parent)
        self._cards: list[_MatchCard] = []
        self._active_idx = -1

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Section header label (styled by global #SectionLabel QSS)
        header_lbl = QLabel("MATCHES")
        header_lbl.setObjectName("SectionLabel")
        header_lbl.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.XS)
        outer.addWidget(header_lbl)

        # Scrollable card list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self._list = QVBoxLayout(content)
        self._list.setContentsMargins(Spacing.XS, Spacing.XS, Spacing.XS, Spacing.XS)
        self._list.setSpacing(Spacing.XS)
        self._list.setAlignment(Qt.AlignTop)

        for i, match in enumerate(model.matches):
            card = _MatchCard(match, i)
            card.clicked.connect(self._on_card_clicked)
            self._list.addWidget(card)
            self._cards.append(card)

        if not model.matches:
            empty_lbl = QLabel("No matches found.")
            empty_lbl.setStyleSheet(
                f"font-size: {Fonts.SIZE_SMALL}px; "
                f"color: {Colors.TEXT_MUTED}; background: transparent;"
            )
            empty_lbl.setAlignment(Qt.AlignCenter)
            self._list.addWidget(empty_lbl)

        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

    def _on_card_clicked(self, index: int):
        self.set_active(index)
        self.match_selected.emit(index)

    def set_active(self, index: int):
        """Highlight the card at `index`, deactivating the previous one."""
        if 0 <= self._active_idx < len(self._cards):
            self._cards[self._active_idx].set_active(False)
        self._active_idx = index
        if 0 <= index < len(self._cards):
            self._cards[index].set_active(True)
