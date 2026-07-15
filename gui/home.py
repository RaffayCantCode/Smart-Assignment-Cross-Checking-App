"""
gui/home.py

The landing screen: app title, description, and the two mode-selection
cards (One-to-One / One-to-Many). Emits `mode_confirmed(mode_id)` when
the user picks a mode and hits Continue.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy

from styles.theme import Colors, Fonts
from gui.comparison import ModeCard


class HomeScreen(QWidget):

    mode_confirmed = Signal(str)  # "one_to_one" | "one_to_many"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_mode = None

        root = QVBoxLayout(self)
        root.setContentsMargins(64, 56, 64, 56)
        root.setSpacing(28)
        root.setAlignment(Qt.AlignTop)

        # -- header --------------------------------------------------------
        header = QVBoxLayout()
        header.setSpacing(10)
        header.setAlignment(Qt.AlignHCenter)

        title = QLabel("Smart Assignment Cross-Checking App")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            f"font-size: {Fonts.H1}px; font-weight: 800; color: {Colors.TEXT_PRIMARY};"
        )
        header.addWidget(title)

        subtitle = QLabel("AI-powered assignment similarity detection and comparison system")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(
            f"font-size: {Fonts.H3}px; font-weight: 500; color: {Colors.ACCENT};"
        )
        header.addWidget(subtitle)

        description = QLabel(
            "Compare student assignments, detect similarities, and generate detailed reports."
        )
        description.setAlignment(Qt.AlignCenter)
        description.setWordWrap(True)
        description.setStyleSheet(
            f"font-size: {Fonts.BODY}px; color: {Colors.TEXT_SECONDARY};"
        )
        header.addWidget(description)

        root.addLayout(header)
        root.addSpacing(12)

        # -- section label --------------------------------------------------
        section_label = QLabel("SELECT A MODE")
        section_label.setStyleSheet(
            f"font-size: {Fonts.SMALL}px; font-weight: 700; letter-spacing: 2px; "
            f"color: {Colors.TEXT_MUTED};"
        )
        root.addWidget(section_label)

        # -- mode cards -------------------------------------------------------
        cards_row = QHBoxLayout()
        cards_row.setSpacing(20)

        self.card_one_to_one = ModeCard(
            mode_id="one_to_one",
            title="One-to-One Cross Checking",
            description="Compare one student's assignment with another student's assignment.",
            icon_text="⇄",
        )
        self.card_one_to_many = ModeCard(
            mode_id="one_to_many",
            title="One-to-Many Cross Checking",
            description="Compare one assignment against multiple student assignments.",
            icon_text="⊞",
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
        self.selected_mode = mode_id
        self.card_one_to_one.set_selected(mode_id == "one_to_one")
        self.card_one_to_many.set_selected(mode_id == "one_to_many")
        self.continue_button.setEnabled(True)

    def _on_continue(self):
        if self.selected_mode:
            self.mode_confirmed.emit(self.selected_mode)

    def reset(self):
        """Called when navigating back here from another screen."""
        self.selected_mode = None
        self.card_one_to_one.set_selected(False)
        self.card_one_to_many.set_selected(False)
        self.continue_button.setEnabled(False)
