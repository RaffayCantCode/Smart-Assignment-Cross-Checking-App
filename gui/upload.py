"""
gui/upload.py

Assignment upload screen. Its layout depends on which mode was chosen
on the home screen:

    one_to_one  -> two side-by-side UploadCards
    one_to_many -> one "Main Assignment" card + N comparison cards

The "Start Cross Checking" button only enables once the minimum
required files are present, and emits `start_requested` with the
collected (fake) file paths so main.py can hand off to the loading
screen.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QGridLayout, QSizePolicy
)

from styles.theme import Colors, Fonts
from gui.comparison import UploadCard

MAX_COMPARISON_SLOTS = 4


class UploadScreen(QWidget):

    start_requested = Signal(dict)   # {"mode": str, "files": {...}}
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mode = "one_to_one"
        self.upload_cards = {}  # slot_id -> UploadCard

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(64, 40, 64, 40)
        self.root.setSpacing(20)
        self.root.setAlignment(Qt.AlignTop)

        # -- top bar: back + title --------------------------------------------
        top_bar = QHBoxLayout()
        self.back_button = QPushButton("←  Back")
        self.back_button.setObjectName("SecondaryButton")
        self.back_button.setCursor(Qt.PointingHandCursor)
        self.back_button.clicked.connect(self.back_requested.emit)
        top_bar.addWidget(self.back_button)
        top_bar.addStretch()
        self.root.addLayout(top_bar)

        self.title_label = QLabel("Upload Assignments")
        self.title_label.setStyleSheet(
            f"font-size: {Fonts.H2}px; font-weight: 700; color: {Colors.TEXT_PRIMARY};"
        )
        self.root.addWidget(self.title_label)

        self.subtitle_label = QLabel("")
        self.subtitle_label.setStyleSheet(
            f"font-size: {Fonts.BODY}px; color: {Colors.TEXT_SECONDARY};"
        )
        self.root.addWidget(self.subtitle_label)

        # -- scrollable body (holds whichever layout the mode needs) -----------
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.body_container = QWidget()
        self.body_layout = QVBoxLayout(self.body_container)
        self.body_layout.setContentsMargins(0, 10, 0, 10)
        self.body_layout.setSpacing(24)
        self.body_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.body_container)
        self.root.addWidget(self.scroll, stretch=1)

        # -- start button --------------------------------------------------------
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        self.start_button = QPushButton("Start Cross Checking")
        self.start_button.setObjectName("PrimaryButton")
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.setMinimumWidth(240)
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self._on_start)
        bottom_row.addWidget(self.start_button)
        bottom_row.addStretch()
        self.root.addLayout(bottom_row)

    # -----------------------------------------------------------------------
    def configure_for_mode(self, mode: str):
        """Rebuild the upload area for the given mode. Called on navigation."""
        self.mode = mode
        self.upload_cards.clear()
        self._clear_body()

        if mode == "one_to_one":
            self.title_label.setText("One-to-One Cross Checking")
            self.subtitle_label.setText(
                "Compare one student's assignment with another student's assignment."
            )
            row = QHBoxLayout()
            row.setSpacing(20)
            card_a = UploadCard("student_1", "Student 1 Assignment")
            card_b = UploadCard("student_2", "Student 2 Assignment")
            for card in (card_a, card_b):
                card.file_selected.connect(self._on_file_changed)
                card.file_cleared.connect(self._on_file_changed)
                self.upload_cards[card.slot_id] = card
                row.addWidget(card)
            self.body_layout.addLayout(row)

        else:  # one_to_many
            self.title_label.setText("One-to-Many Cross Checking")
            self.subtitle_label.setText(
                "Compare one assignment against multiple student assignments."
            )

            main_label = QLabel("MAIN ASSIGNMENT")
            main_label.setStyleSheet(
                f"font-size: {Fonts.SMALL}px; font-weight: 700; letter-spacing: 1px; "
                f"color: {Colors.TEXT_MUTED};"
            )
            self.body_layout.addWidget(main_label)

            main_card = UploadCard("main", "Main Assignment")
            main_card.file_selected.connect(self._on_file_changed)
            main_card.file_cleared.connect(self._on_file_changed)
            self.upload_cards["main"] = main_card
            main_row = QHBoxLayout()
            main_row.addWidget(main_card)
            main_row.addStretch()
            self.body_layout.addLayout(main_row)

            comparison_label = QLabel("COMPARISON ASSIGNMENTS")
            comparison_label.setStyleSheet(
                f"font-size: {Fonts.SMALL}px; font-weight: 700; letter-spacing: 1px; "
                f"color: {Colors.TEXT_MUTED};"
            )
            self.body_layout.addWidget(comparison_label)

            grid = QGridLayout()
            grid.setSpacing(20)
            for i in range(MAX_COMPARISON_SLOTS):
                slot_id = f"student_{i + 1}"
                card = UploadCard(slot_id, f"Student {i + 1} Assignment")
                card.file_selected.connect(self._on_file_changed)
                card.file_cleared.connect(self._on_file_changed)
                self.upload_cards[slot_id] = card
                grid.addWidget(card, i // 2, i % 2)
            self.body_layout.addLayout(grid)

        self._update_start_button()

    def _clear_body(self):
        while self.body_layout.count():
            item = self.body_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    # -----------------------------------------------------------------------
    def _on_file_changed(self, *_):
        self._update_start_button()

    def _update_start_button(self):
        if self.mode == "one_to_one":
            ready = all(card.has_file() for card in self.upload_cards.values())
        else:
            main_ready = self.upload_cards.get("main") and self.upload_cards["main"].has_file()
            comparison_ready = sum(
                1 for slot_id, card in self.upload_cards.items()
                if slot_id != "main" and card.has_file()
            ) >= 1
            ready = bool(main_ready and comparison_ready)
        self.start_button.setEnabled(ready)

    def _on_start(self):
        files = {slot_id: card.file_path for slot_id, card in self.upload_cards.items() if card.has_file()}
        self.start_requested.emit({"mode": self.mode, "files": files})
