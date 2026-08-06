"""
gui/upload.py

Assignment upload screen. Its layout depends on which mode was chosen
on the home screen:

    one_to_one  -> two side-by-side UploadCards
    one_to_many -> one "Teacher Answer Sheet" card (the main reference) +
                   a dynamic list of student comparison cards.

The one-to-many list starts with a minimum of `MIN_COMPARISON_SLOTS`
students and can grow up to `MAX_COMPARISON_SLOTS` via an "Add Student"
button. Every student slot has a "Remove" button so the teacher can reduce
the number of students (but never below the minimum).

The "Start Cross Checking" button only enables once the main answer sheet
is uploaded, and emits `start_requested` with the collected file paths.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QGridLayout, QFrame
)

from styles.theme import Colors, Fonts, Spacing, Icons, IconSize, render_icon
from gui.comparison import UploadCard

MIN_COMPARISON_SLOTS = 4
MAX_COMPARISON_SLOTS = 50


class StudentSlot(QWidget):
    """A single comparison student: a small header row (remove button + label)
    together with its UploadCard. Exposes `removed` so the screen can drop it
    from the active list when the teacher deletes a student."""

    removed = Signal(object)  # emits self

    def __init__(self, index: int, parent=None):
        super().__init__(parent)
        self.index = index
        self.card = None
        self.title_label = None
        self.remove_btn = None
        self._rebuild()

    # ------------------------------------------------------------------
    def _rebuild(self):
        while self.layout():
            item = self.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(Spacing.XS)

        head = QHBoxLayout()
        head.setSpacing(Spacing.XS)

        self.title_label = QLabel(f"Student {self.index}")
        self.title_label.setStyleSheet(
            f"font-size: {Fonts.SIZE_SMALL}px; font-weight: 700; "
            f"letter-spacing: 1px; color: {Colors.TEXT_SECONDARY}; background: transparent;"
        )
        head.addWidget(self.title_label)
        head.addStretch()

        self.remove_btn = QPushButton("  Remove")
        self.remove_btn.setObjectName("GhostButton")
        self.remove_btn.setCursor(Qt.PointingHandCursor)
        self.remove_btn.setIcon(render_icon(Icons.MINUS, Colors.TEXT_SECONDARY, IconSize.SM))
        self.remove_btn.clicked.connect(lambda: self.removed.emit(self.index))
        head.addWidget(self.remove_btn)

        lay.addLayout(head)

        self.card = UploadCard(f"student_{self.index}", f"Student {self.index} Assignment")
        lay.addWidget(self.card)

    # ------------------------------------------------------------------
    def sync(self, index: int, removable: bool):
        """Re-number this slot and set whether it can currently be removed."""
        self.index = index
        self.card.slot_id = f"student_{index}"
        self.title_label.setText(f"Student {index}")
        self.card.set_title(f"Student {index} Assignment")
        self.remove_btn.setEnabled(removable)
        self.remove_btn.setVisible(True)


class UploadScreen(QWidget):

    start_requested = Signal(dict)   # {"mode": str, "files": {...}}
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mode = "one_to_one"
        self.upload_cards = {}  # slot_id -> UploadCard (rebuild on changes)
        self.main_card = None
        self._student_slots = []  # list[StudentSlot]

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(Spacing.XXXL, Spacing.XXL, Spacing.XXXL, Spacing.XXL)
        self.root.setSpacing(Spacing.LG)
        self.root.setAlignment(Qt.AlignTop)

        # -- top bar: back ----------------------------------------------------
        top_bar = QHBoxLayout()
        self.back_button = QPushButton("  Back")
        self.back_button.setObjectName("GhostButton")
        self.back_button.setIcon(render_icon(Icons.ARROW_LEFT, Colors.TEXT_SECONDARY, IconSize.SM))
        self.back_button.setCursor(Qt.PointingHandCursor)
        self.back_button.clicked.connect(self.back_requested.emit)
        top_bar.addWidget(self.back_button)
        top_bar.addStretch()
        self.root.addLayout(top_bar)

        self.title_label = QLabel("Upload Assignments")
        self.title_label.setStyleSheet(f"font-size: {Fonts.SIZE_H2}px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
        self.root.addWidget(self.title_label)

        self.subtitle_label = QLabel("")
        self.subtitle_label.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_SECONDARY};")
        self.subtitle_label.setWordWrap(True)
        self.root.addWidget(self.subtitle_label)

        self.root.addSpacing(Spacing.SM)

        # -- scrollable body ---------------------------------------------------
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.body_container = QWidget()
        self.body_layout = QVBoxLayout(self.body_container)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(Spacing.LG)
        self.body_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.body_container)
        self.root.addWidget(self.scroll, stretch=1)

        # -- bottom action bar ---------------------------------------------------
        bottom_area = QVBoxLayout()

        divider = QFrame()
        divider.setObjectName("Divider")
        bottom_area.addWidget(divider)
        bottom_area.addSpacing(Spacing.MD)

        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        self.start_button = QPushButton("Start Cross Checking")
        self.start_button.setObjectName("PrimaryButton")
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.setMinimumWidth(240)
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self._on_start)
        bottom_row.addWidget(self.start_button)

        bottom_area.addLayout(bottom_row)
        self.root.addLayout(bottom_area)

    # -----------------------------------------------------------------------
    def configure_for_mode(self, mode: str):
        """Rebuild the upload area for the given mode. Called on navigation."""
        self.mode = mode
        self.upload_cards.clear()
        self._student_slots.clear()
        self.main_card = None
        self._clear_body()

        if mode == "one_to_one":
            self.title_label.setText("One-to-One Cross Checking")
            self.subtitle_label.setText(
                "Compare one student's assignment with another student's assignment. "
                "(Supported formats: .pdf, .docx)"
            )

            row = QHBoxLayout()
            row.setSpacing(Spacing.LG)
            card_a = UploadCard("student_1", "Student 1 Assignment")
            card_b = UploadCard("student_2", "Student 2 Assignment")
            for card in (card_a, card_b):
                card.file_selected.connect(self._on_file_changed)
                card.file_cleared.connect(self._on_file_changed)
                self.upload_cards[card.slot_id] = card
                row.addWidget(card)
            self.body_layout.addLayout(row)

        else:  # one_to_many
            self._build_one_to_many()

        self._update_start_button()

    def _build_one_to_many(self):
        self.title_label.setText("One-to-Many Cross Checking")
        self.subtitle_label.setText(
            "Upload your answer sheet as the main reference, then add the student "
            "assignments to compare against it (4 to " + str(MAX_COMPARISON_SLOTS) + " students). "
            "Supported formats: .pdf, .docx"
        )

        # -- Main answer sheet ---------------------------------------------------
        main_label = QLabel("Assignment Answer Sheet")
        main_label.setObjectName("SectionLabel")
        self.body_layout.addWidget(main_label)

        self.main_card = UploadCard("main", "Student Assignment / Answer Sheet")
        self.main_card.file_selected.connect(self._on_file_changed)
        self.main_card.file_cleared.connect(self._on_file_changed)
        self.upload_cards["main"] = self.main_card

        main_row = QHBoxLayout()
        main_row.addWidget(self.main_card)
        main_row.addStretch()
        self.body_layout.addLayout(main_row)

        self.body_layout.addSpacing(Spacing.SM)

        # -- Comparison students header -----------------------------------------
        cmp_header = QHBoxLayout()
        cmp_label = QLabel()
        cmp_label.setObjectName("SectionLabel")
        cmp_label.setText("Student Assignments")
        cmp_header.addWidget(cmp_label)
        cmp_header.addStretch()

        self.counter_label = QLabel()
        self.counter_label.setStyleSheet(
            f"font-size: {Fonts.SIZE_SMALL}px; color: {Colors.TEXT_MUTED}; background: transparent;"
        )
        cmp_header.addWidget(self.counter_label)
        self.body_layout.addLayout(cmp_header)

        # -- Grid of student slots ------------------------------------------------
        grid_container = QWidget()
        self.student_grid = QGridLayout(grid_container)
        self.student_grid.setContentsMargins(0, 0, 0, 0)
        self.student_grid.setSpacing(Spacing.LG)
        self.body_layout.addWidget(grid_container)

        # -- Add Student button ---------------------------------------------------
        add_row = QHBoxLayout()
        add_row.addStretch()
        self.add_button = QPushButton("  Add Student")
        self.add_button.setObjectName("SecondaryButton")
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.add_button.setIcon(render_icon(Icons.PLUS, Colors.TEXT_PRIMARY, IconSize.SM))
        self.add_button.clicked.connect(self._add_student)
        add_row.addWidget(self.add_button)
        add_row.addStretch()
        self.body_layout.addLayout(add_row)

        # -- Seed the minimum number of students ---------------------------------
        for _ in range(MIN_COMPARISON_SLOTS):
            self._add_student()

        self._sync_students()

    def _add_student(self):
        if len(self._student_slots) >= MAX_COMPARISON_SLOTS:
            return
        slot = StudentSlot(len(self._student_slots) + 1, self)
        slot.card.file_selected.connect(self._on_file_changed)
        slot.card.file_cleared.connect(self._on_file_changed)
        slot.removed.connect(self._remove_student)
        self._student_slots.append(slot)
        self._sync_students()
        self._update_start_button()

    def _remove_student(self, slot: int):
        # Only allow deletions while above the minimum count.
        if slot not in [s.index for s in self._student_slots]:
            return
        if len(self._student_slots) <= MIN_COMPARISON_SLOTS:
            return
        target = next((s for s in self._student_slots if s.index == slot), None)
        if target is None:
            return
        self._student_slots.remove(target)
        target.deleteLater()
        self._sync_students()
        self._update_start_button()

    def _sync_students(self):
        """Renumber slots, rebuild the upload_cards map, and refresh the grid."""
        # Rebuild upload_cards from the current ordering.
        self.upload_cards = {"main": self.main_card} if self.main_card else {}
        for slot in self._student_slots:
            slot.sync(
                index=self._student_slots.index(slot) + 1,
                removable=len(self._student_slots) > MIN_COMPARISON_SLOTS,
            )
            self.upload_cards[slot.card.slot_id] = slot.card

        # Clear the grid layout (children are kept; only their grid position changes)
        while self.student_grid.count():
            item = self.student_grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        for i, slot in enumerate(self._student_slots):
            self.student_grid.addWidget(slot, i // 2, i % 2)

        self.counter_label.setText(f"{len(self._student_slots)} of {MAX_COMPARISON_SLOTS} students")
        self.add_button.setEnabled(len(self._student_slots) < MAX_COMPARISON_SLOTS)

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
        ready_count = sum(1 for c in self.upload_cards.values() if c.has_file())

        if self.mode == "one_to_one":
            total_req = 2
            ready = (ready_count == total_req)
        else:
            main_ready = self.main_card is not None and self.main_card.has_file()
            comparison_ready = ready_count - (1 if main_ready else 0)
            ready = bool(main_ready and comparison_ready >= 1)

        self.start_button.setEnabled(ready)

        # Update text to reflect status
        if ready:
            self.start_button.setText(f"Start Cross Checking ({ready_count} files)")
        else:
            self.start_button.setText("Start Cross Checking")

    def _on_start(self):
        files = {slot_id: card.file_path for slot_id, card in self.upload_cards.items() if card.has_file()}
        self.start_requested.emit({"mode": self.mode, "files": files})

    def reset(self):
        """Clear all uploaded files and reset the start button, keeping the
        current mode layout intact. Called when 'Run Another Check' is pressed
        so the teacher can upload fresh documents for a new comparison."""
        for card in self.upload_cards.values():
            card.clear()
        self._update_start_button()