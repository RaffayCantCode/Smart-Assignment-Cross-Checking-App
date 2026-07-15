"""
gui/settings.py

Placeholder settings screen. Not part of the core flow yet, but kept
here (per the requested project structure) so future preferences -
theme toggle, default sensitivity thresholds, export format, etc. -
have an obvious home instead of getting bolted onto another screen.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame

from styles.theme import Colors, Fonts


class SettingsScreen(QWidget):

    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(64, 40, 64, 40)
        root.setSpacing(20)
        root.setAlignment(Qt.AlignTop)

        top_bar = QHBoxLayout()
        back_button = QPushButton("←  Back")
        back_button.setObjectName("SecondaryButton")
        back_button.setCursor(Qt.PointingHandCursor)
        back_button.clicked.connect(self.back_requested.emit)
        top_bar.addWidget(back_button)
        top_bar.addStretch()
        root.addLayout(top_bar)

        title = QLabel("Settings")
        title.setStyleSheet(
            f"font-size: {Fonts.H2}px; font-weight: 700; color: {Colors.TEXT_PRIMARY};"
        )
        root.addWidget(title)

        placeholder_card = QFrame()
        placeholder_card.setObjectName("Card")
        card_layout = QVBoxLayout(placeholder_card)
        card_layout.setContentsMargins(28, 24, 28, 24)

        note = QLabel(
            "Settings such as similarity sensitivity, report export format, and "
            "account preferences will live here once the backend is connected."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"font-size: {Fonts.BODY}px; color: {Colors.TEXT_SECONDARY};")
        card_layout.addWidget(note)

        root.addWidget(placeholder_card)
        root.addStretch()
