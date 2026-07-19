"""
gui/home.py

The landing screen: app title, description, and the two mode-selection
cards (One-to-One / One-to-Many). Emits `mode_confirmed(mode_id)` when
the user picks a mode and hits Continue. Emits `settings_requested()`
when the settings icon is clicked.
"""

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGraphicsOpacityEffect
)
from PySide6.QtGui import QPainter, QColor, QBrush, QPen

from styles.theme import Colors, Fonts, Spacing, Icons, IconSize, render_icon, Anim
from gui.comparison import ModeCard

class LogoWidget(QWidget):
    """Simple decorative logo mark."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 48)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw a rotated square (diamond)
        painter.translate(24, 24)
        painter.rotate(45)
        
        # Outer
        painter.setBrush(QBrush(QColor(Colors.ACCENT_SOFT)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(-16, -16, 32, 32, 4, 4)
        
        # Inner
        painter.setBrush(QBrush(QColor(Colors.ACCENT)))
        painter.drawRoundedRect(-8, -8, 16, 16, 2, 2)


class HomeScreen(QWidget):

    mode_confirmed = Signal(str)  # "one_to_one" | "one_to_many"
    settings_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_mode = None

        root = QVBoxLayout(self)
        root.setContentsMargins(Spacing.XXXL, Spacing.XXXL, Spacing.XXXL, Spacing.XXXL)
        root.setSpacing(Spacing.XL)
        root.setAlignment(Qt.AlignTop)

        # -- top bar: settings ---------------------------------------------
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        
        self.settings_btn = QPushButton()
        self.settings_btn.setObjectName("IconButton")
        self.settings_btn.setIcon(render_icon(Icons.SETTINGS, Colors.TEXT_SECONDARY, IconSize.LG))
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.clicked.connect(self.settings_requested.emit)
        top_bar.addWidget(self.settings_btn)
        
        root.addLayout(top_bar)
        root.addSpacing(Spacing.XL)

        # -- header --------------------------------------------------------
        header = QVBoxLayout()
        header.setSpacing(Spacing.MD)
        header.setAlignment(Qt.AlignHCenter)

        logo = LogoWidget()
        header.addWidget(logo, alignment=Qt.AlignHCenter)

        title = QLabel("Smart Assignment Cross-Checking App")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"font-size: {Fonts.SIZE_H1}px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        header.addWidget(title)

        description = QLabel(
            "Compare student assignments, detect similarities, and generate detailed reports."
        )
        description.setAlignment(Qt.AlignCenter)
        description.setWordWrap(True)
        description.setStyleSheet(f"font-size: {Fonts.SIZE_BODY_LG}px; color: {Colors.TEXT_SECONDARY};")
        header.addWidget(description)

        root.addLayout(header)
        root.addSpacing(Spacing.XXL)

        # -- section label --------------------------------------------------
        section_label = QLabel("Select a mode")
        section_label.setObjectName("SectionLabel")
        root.addWidget(section_label)

        # -- mode cards -------------------------------------------------------
        cards_row = QHBoxLayout()
        cards_row.setSpacing(Spacing.LG)

        self.card_one_to_one = ModeCard(
            mode_id="one_to_one",
            title="One-to-One Cross Checking",
            description="Compare one student's assignment with another student's assignment.",
            icon_svg=Icons.ONE_TO_ONE,
        )
        self.card_one_to_many = ModeCard(
            mode_id="one_to_many",
            title="One-to-Many Cross Checking",
            description="Compare one assignment against multiple student assignments.",
            icon_svg=Icons.ONE_TO_MANY,
        )

        self.card_one_to_one.clicked.connect(self._on_card_clicked)
        self.card_one_to_many.clicked.connect(self._on_card_clicked)

        cards_row.addWidget(self.card_one_to_one)
        cards_row.addWidget(self.card_one_to_many)
        root.addLayout(cards_row)

        root.addStretch()

        # -- continue button -------------------------------------------------
        continue_row = QHBoxLayout()
        continue_row.addStretch()
        self.continue_button = QPushButton("Continue")
        self.continue_button.setObjectName("PrimaryButton")
        self.continue_button.setCursor(Qt.PointingHandCursor)
        self.continue_button.setEnabled(False)
        self.continue_button.setMinimumWidth(180)
        self.continue_button.clicked.connect(self._on_continue)
        continue_row.addWidget(self.continue_button)
        continue_row.addStretch()
        root.addLayout(continue_row)

    def _on_card_clicked(self, mode_id: str):
        if not self.selected_mode:
            # First time selection, enable button
            self.continue_button.setEnabled(True)

        self.selected_mode = mode_id
        self.card_one_to_one.set_selected(mode_id == "one_to_one")
        self.card_one_to_many.set_selected(mode_id == "one_to_many")

    def _on_continue(self):
        if self.selected_mode:
            self.mode_confirmed.emit(self.selected_mode)

    def reset(self):
        """Called when navigating back here from another screen."""
        self.selected_mode = None
        self.card_one_to_one.set_selected(False)
        self.card_one_to_many.set_selected(False)
        self.continue_button.setEnabled(False)
