"""
gui/comparison.py

Reusable, self-contained widgets used by more than one screen:

    ModeCard    - the big selectable "One-to-One" / "One-to-Many" cards
    UploadCard  - a drag-and-drop assignment upload slot

Keeping these here (instead of copy-pasting into home.py / upload.py)
means when the backend team wires up real file parsing, there is
exactly ONE place that emits "a file was provided" signals.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QSizePolicy, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QColor

from styles.theme import Colors, Fonts


def _shadow(blur=30, color=QColor(124, 92, 255, 90), y_offset=0):
    effect = QGraphicsDropShadowEffect()
    effect.setBlurRadius(blur)
    effect.setOffset(0, y_offset)
    effect.setColor(color)
    return effect


class ModeCard(QFrame):
    """A large selectable card representing one cross-checking mode."""

    clicked = Signal(str)  # emits the mode_id when clicked

    def __init__(self, mode_id: str, title: str, description: str, icon_text: str = "◆", parent=None):
        super().__init__(parent)
        self.mode_id = mode_id
        self._selected = False

        self.setObjectName("Card")
        self.setProperty("selected", "false")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        icon_label = QLabel(icon_text)
        icon_label.setStyleSheet(
            f"font-size: 30px; color: {Colors.ACCENT}; background: transparent;"
        )
        layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"font-size: {Fonts.H3}px; font-weight: 700; background: transparent;"
        )
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(
            f"font-size: {Fonts.BODY}px; color: {Colors.TEXT_SECONDARY}; background: transparent;"
        )
        layout.addWidget(desc_label)
        layout.addStretch()

        self._badge = QLabel("SELECTED")
        self._badge.setStyleSheet(
            f"font-size: 10px; font-weight: 700; letter-spacing: 1px; "
            f"color: {Colors.ACCENT}; background: transparent;"
        )
        self._badge.setVisible(False)
        layout.addWidget(self._badge)

    def set_selected(self, selected: bool):
        self._selected = selected
        self.setProperty("selected", "true" if selected else "false")
        self._badge.setVisible(selected)
        self.setGraphicsEffect(_shadow() if selected else None)
        self.style().unpolish(self)
        self.style().polish(self)

    def is_selected(self) -> bool:
        return self._selected

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.mode_id)
        super().mousePressEvent(event)


class UploadCard(QFrame):
    """
    A drag-and-drop capable upload slot.

    No real file reading happens here - we only capture the file path
    the OS hands us and display the filename. Backend integration can
    later hook into `file_selected` to actually parse the document.
    """

    file_selected = Signal(str, str)   # (slot_id, file_path)
    file_cleared = Signal(str)         # (slot_id)

    ACCEPTED_EXTENSIONS = (".pdf", ".docx", ".doc", ".txt")

    def __init__(self, slot_id: str, label: str, parent=None):
        super().__init__(parent)
        self.slot_id = slot_id
        self.file_path = None

        self.setAcceptDrops(True)
        self.setObjectName("Card")
        self.setMinimumHeight(230)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(12)

        title = QLabel(label)
        title.setStyleSheet(
            f"font-size: {Fonts.BODY + 1}px; font-weight: 600; background: transparent;"
        )
        outer.addWidget(title)

        self.drop_zone = QFrame()
        self.drop_zone.setObjectName("DropZone")
        self.drop_zone.setProperty("hover", "false")
        self.drop_zone.setProperty("filled", "false")
        self.drop_zone.setMinimumHeight(150)

        zone_layout = QVBoxLayout(self.drop_zone)
        zone_layout.setAlignment(Qt.AlignCenter)
        zone_layout.setSpacing(8)

        self.icon_label = QLabel("📄")
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 34px; background: transparent;")
        zone_layout.addWidget(self.icon_label)

        self.status_label = QLabel("No assignment uploaded")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            f"font-size: {Fonts.SMALL + 1}px; color: {Colors.TEXT_MUTED}; background: transparent;"
        )
        zone_layout.addWidget(self.status_label)

        hint_label = QLabel("Drag & drop a file here")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet(
            f"font-size: {Fonts.SMALL}px; color: {Colors.TEXT_MUTED}; background: transparent;"
        )
        zone_layout.addWidget(hint_label)

        outer.addWidget(self.drop_zone)

        button_row = QHBoxLayout()
        button_row.addStretch()
        self.browse_button = QPushButton("Browse File")
        self.browse_button.setObjectName("PillButton")
        self.browse_button.setCursor(Qt.PointingHandCursor)
        self.browse_button.clicked.connect(self._browse_file)
        button_row.addWidget(self.browse_button)

        self.clear_button = QPushButton("Remove")
        self.clear_button.setObjectName("PillButton")
        self.clear_button.setCursor(Qt.PointingHandCursor)
        self.clear_button.setVisible(False)
        self.clear_button.clicked.connect(self.clear)
        button_row.addWidget(self.clear_button)
        button_row.addStretch()
        outer.addLayout(button_row)

    # -- drag & drop -----------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_hover(True)

    def dragLeaveEvent(self, event):
        self._set_hover(False)

    def dropEvent(self, event):
        self._set_hover(False)
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self._apply_file(path)

    def _set_hover(self, hovering: bool):
        self.drop_zone.setProperty("hover", "true" if hovering else "false")
        self.drop_zone.style().unpolish(self.drop_zone)
        self.drop_zone.style().polish(self.drop_zone)

    # -- browse ------------------------------------------------------------
    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Assignment File", "",
            "Documents (*.pdf *.docx *.doc *.txt);;All Files (*)"
        )
        if path:
            self._apply_file(path)

    # -- shared -------------------------------------------------------------
    def _apply_file(self, path: str):
        filename = path.split("/")[-1].split("\\")[-1]
        self.file_path = path
        self.status_label.setText(filename)
        self.status_label.setStyleSheet(
            f"font-size: {Fonts.SMALL + 1}px; color: {Colors.TEXT_PRIMARY}; "
            f"font-weight: 600; background: transparent;"
        )
        self.icon_label.setText("✅")
        self.drop_zone.setProperty("filled", "true")
        self.drop_zone.style().unpolish(self.drop_zone)
        self.drop_zone.style().polish(self.drop_zone)
        self.clear_button.setVisible(True)
        self.file_selected.emit(self.slot_id, path)

    def clear(self):
        self.file_path = None
        self.status_label.setText("No assignment uploaded")
        self.status_label.setStyleSheet(
            f"font-size: {Fonts.SMALL + 1}px; color: {Colors.TEXT_MUTED}; background: transparent;"
        )
        self.icon_label.setText("📄")
        self.drop_zone.setProperty("filled", "false")
        self.drop_zone.style().unpolish(self.drop_zone)
        self.drop_zone.style().polish(self.drop_zone)
        self.clear_button.setVisible(False)
        self.file_cleared.emit(self.slot_id)

    def has_file(self) -> bool:
        return self.file_path is not None
