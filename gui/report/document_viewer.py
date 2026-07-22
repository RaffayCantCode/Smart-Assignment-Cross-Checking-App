from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QScrollArea, QWidget, QVBoxLayout
from .paragraph_widget import ParagraphWidget
from backend.reporting.model import ReportDocument

class DocumentViewer(QScrollArea):
    scrolled = Signal(int)

    def __init__(self, document: ReportDocument, parent=None):
        super().__init__(parent)
        self.document = document
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        self.setObjectName("DocumentViewer")
        
        self.container = QWidget()
        self.container.setObjectName("DocumentViewerContainer")
        self.container.setStyleSheet("#DocumentViewerContainer { background: transparent; }")
        
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(12)
        self.layout.setAlignment(Qt.AlignTop)
        
        self.setWidget(self.container)
        
        self.paragraph_widgets: dict[int, ParagraphWidget] = {}
        self._populate()
        
        self.verticalScrollBar().valueChanged.connect(self.scrolled.emit)

    def _populate(self):
        for p in self.document.paragraphs:
            pw = ParagraphWidget(p)
            self.layout.addWidget(pw)
            self.paragraph_widgets[p.index] = pw

    def set_font_size(self, size: int):
        for pw in self.paragraph_widgets.values():
            pw.set_font_size(size)

    def search(self, query: str):
        for pw in self.paragraph_widgets.values():
            pw.highlight_search(query)

    def scroll_to_paragraph(self, index: int):
        if index in self.paragraph_widgets:
            pw = self.paragraph_widgets[index]
            self.ensureWidgetVisible(pw, 50, 50)
