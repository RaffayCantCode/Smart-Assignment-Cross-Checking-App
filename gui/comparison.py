"""
gui/comparison.py

Reusable, self-contained widgets used by more than one screen:

    ModeCard    - the big selectable "One-to-One" / "One-to-Many" cards
    UploadCard  - a drag-and-drop assignment upload slot

Keeping these here means when the backend team wires up real file parsing, 
there is exactly ONE place that emits "a file was provided" signals.
"""

from PySide6.QtCore import Qt, Signal, Property, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QSizePolicy, QWidget
)
from PySide6.QtGui import QColor, QPainter, QPen, QBrush

from styles.theme import Colors, Fonts, Radius, Anim, Icons, IconSize, render_icon


class ModeCard(QFrame):
    """A selectable card representing one cross-checking mode with smooth transitions."""

    clicked = Signal(str)

    def __init__(self, mode_id: str, title: str, description: str, icon_svg: str, parent=None):
        super().__init__(parent)
        self.mode_id = mode_id
        self._selected = False
        
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Custom properties for animation
        self._bg_color = QColor(Colors.BG_SURFACE)
        self._border_color = QColor(Colors.BORDER)
        
        self.bg_anim = QPropertyAnimation(self, b"bgColor")
        self.bg_anim.setDuration(Anim.SELECT)
        self.bg_anim.setEasingCurve(QEasingCurve.OutCubic)
        
        self.border_anim = QPropertyAnimation(self, b"borderColor")
        self.border_anim.setDuration(Anim.SELECT)
        self.border_anim.setEasingCurve(QEasingCurve.OutCubic)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # Header: Icon + Selection Indicator
        header = QHBoxLayout()
        
        self.icon_label = QLabel()
        self.icon_label.setPixmap(render_icon(icon_svg, Colors.ACCENT, IconSize.LG))
        header.addWidget(self.icon_label)
        header.addStretch()
        
        self.indicator = QWidget()
        self.indicator.setFixedSize(12, 12)
        self.indicator.setVisible(False)
        header.addWidget(self.indicator)
        
        layout.addLayout(header)
        layout.addSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: {Fonts.SIZE_H3}px; font-weight: 600; color: {Colors.TEXT_PRIMARY}; background: transparent;")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_SECONDARY}; background: transparent;")
        layout.addWidget(desc_label)
        layout.addStretch()

    # Properties for animation
    def get_bg_color(self):
        return self._bg_color

    def set_bg_color(self, color):
        self._bg_color = color
        self.update()

    bgColor = Property(QColor, get_bg_color, set_bg_color)

    def get_border_color(self):
        return self._border_color

    def set_border_color(self, color):
        self._border_color = color
        self.update()

    borderColor = Property(QColor, get_border_color, set_border_color)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        painter.setBrush(QBrush(self._bg_color))
        # Border
        pen = QPen(self._border_color)
        pen.setWidth(2 if self._selected else 1)
        painter.setPen(pen)
        
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(rect, Radius.LG, Radius.LG)
        
        # Draw indicator if selected
        if self._selected:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(Colors.ACCENT)))
            ind_rect = self.indicator.geometry()
            painter.drawEllipse(ind_rect.adjusted(2, 2, -2, -2))

    def set_selected(self, selected: bool):
        self._selected = selected
        self.indicator.setVisible(selected)
        
        self.bg_anim.stop()
        self.border_anim.stop()
        
        self.bg_anim.setEndValue(QColor(Colors.ACCENT_SOFT) if selected else QColor(Colors.BG_SURFACE))
        self.border_anim.setEndValue(QColor(Colors.ACCENT) if selected else QColor(Colors.BORDER))
        
        self.bg_anim.start()
        self.border_anim.start()

    def is_selected(self) -> bool:
        return self._selected

    def enterEvent(self, event):
        if not self._selected:
            self.bg_anim.stop()
            self.border_anim.stop()
            self.bg_anim.setEndValue(QColor(Colors.BG_HOVER))
            self.border_anim.setEndValue(QColor(Colors.BORDER_LIGHT))
            self.bg_anim.start()
            self.border_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self._selected:
            self.bg_anim.stop()
            self.border_anim.stop()
            self.bg_anim.setEndValue(QColor(Colors.BG_SURFACE))
            self.border_anim.setEndValue(QColor(Colors.BORDER))
            self.bg_anim.start()
            self.border_anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.mode_id)
        super().mousePressEvent(event)


class UploadCard(QFrame):
    """A clean, modern drag-and-drop capable upload slot."""

    file_selected = Signal(str, str)   # (slot_id, file_path)
    file_cleared = Signal(str)         # (slot_id)

    ACCEPTED_EXTENSIONS = (".pdf", ".docx", ".doc", ".txt")

    def __init__(self, slot_id: str, label: str, parent=None):
        super().__init__(parent)
        self.slot_id = slot_id
        self.file_path = None

        self.setAcceptDrops(True)
        self.setMinimumHeight(160)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(8)

        title = QLabel(label)
        title.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; font-weight: 500; color: {Colors.TEXT_PRIMARY};")
        outer.addWidget(title)

        self.drop_zone = QFrame()
        self.drop_zone.setObjectName("DropZone")
        
        zone_layout = QHBoxLayout(self.drop_zone)
        zone_layout.setContentsMargins(16, 16, 16, 16)
        zone_layout.setSpacing(12)

        # Icon
        self.icon_label = QLabel()
        self.icon_label.setPixmap(render_icon(Icons.UPLOAD, Colors.TEXT_MUTED, IconSize.LG))
        zone_layout.addWidget(self.icon_label)

        # Text area
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        self.status_label = QLabel("Drag & drop your file here")
        self.status_label.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_PRIMARY}; font-weight: 500; background: transparent;")
        text_layout.addWidget(self.status_label)
        
        self.hint_label = QLabel("or click to browse")
        self.hint_label.setStyleSheet(f"font-size: {Fonts.SIZE_SMALL}px; color: {Colors.TEXT_MUTED}; background: transparent;")
        text_layout.addWidget(self.hint_label)
        
        zone_layout.addLayout(text_layout)
        zone_layout.addStretch()

        # Action buttons
        self.browse_button = QPushButton("Browse")
        self.browse_button.setObjectName("SecondaryButton")
        self.browse_button.setCursor(Qt.PointingHandCursor)
        self.browse_button.clicked.connect(self._browse_file)
        zone_layout.addWidget(self.browse_button)

        self.clear_button = QPushButton("Remove")
        self.clear_button.setObjectName("GhostButton")
        self.clear_button.setCursor(Qt.PointingHandCursor)
        self.clear_button.setVisible(False)
        self.clear_button.clicked.connect(self.clear)
        zone_layout.addWidget(self.clear_button)

        outer.addWidget(self.drop_zone)

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
        if self.has_file():
            return
        border_col = Colors.ACCENT if hovering else Colors.BORDER
        bg_col = Colors.BG_HOVER if hovering else Colors.BG_SURFACE_ALT
        self.drop_zone.setStyleSheet(f"#DropZone {{ background-color: {bg_col}; border: 1px solid {border_col}; border-radius: {Radius.LG}px; }}")

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Assignment File", "",
            "Documents (*.pdf *.docx *.doc *.txt);;All Files (*)"
        )
        if path:
            self._apply_file(path)

    def _apply_file(self, path: str):
        filename = path.split("/")[-1].split("\\")[-1]
        self.file_path = path
        
        self.status_label.setText(filename)
        self.hint_label.setText("Ready for checking")
        self.icon_label.setPixmap(render_icon(Icons.FILE, Colors.SUCCESS, IconSize.LG))
        
        self.drop_zone.setStyleSheet(f"#DropZone {{ background-color: {Colors.BG_SURFACE_ALT}; border: 1px solid {Colors.SUCCESS}; border-radius: {Radius.LG}px; }}")
        
        self.browse_button.setVisible(False)
        self.clear_button.setVisible(True)
        
        self.file_selected.emit(self.slot_id, path)

    def clear(self):
        self.file_path = None
        self.status_label.setText("Drag & drop your file here")
        self.hint_label.setText("or click to browse")
        self.icon_label.setPixmap(render_icon(Icons.UPLOAD, Colors.TEXT_MUTED, IconSize.LG))
        
        self.drop_zone.setStyleSheet(f"#DropZone {{ background-color: {Colors.BG_SURFACE_ALT}; border: 1px solid {Colors.BORDER}; border-radius: {Radius.LG}px; }}")
        
        self.browse_button.setVisible(True)
        self.clear_button.setVisible(False)
        self.file_cleared.emit(self.slot_id)

    def has_file(self) -> bool:
        return self.file_path is not None
