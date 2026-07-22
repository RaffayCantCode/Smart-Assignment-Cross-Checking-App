from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QSplitter, QCheckBox
)
from styles.theme import Colors, Fonts, Spacing
from backend.reporting.model import ReportModel
from .document_viewer import DocumentViewer

class ReportScreen(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.report_model = None
        self.current_match_idx = -1
        self.current_zoom = Fonts.SIZE_BODY
        
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
        self.root.setSpacing(Spacing.LG)
        
        self._build_toolbar()
        self._build_stats_bar()
        self._build_viewer()
        
    def _build_toolbar(self):
        tb = QHBoxLayout()
        tb.setSpacing(Spacing.MD)
        
        self.btn_back = QPushButton("Back to Results")
        self.btn_back.setObjectName("SecondaryButton")
        self.btn_back.clicked.connect(self.back_requested.emit)
        tb.addWidget(self.btn_back)
        
        tb.addStretch()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search...")
        self.search_input.setFixedWidth(200)
        self.search_input.textChanged.connect(self._on_search)
        tb.addWidget(self.search_input)
        
        self.btn_prev = QPushButton("Previous")
        self.btn_prev.setObjectName("IconButton")
        self.btn_prev.clicked.connect(self._prev_match)
        tb.addWidget(self.btn_prev)
        
        self.lbl_match_counter = QLabel("Match 0 / 0")
        self.lbl_match_counter.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-weight: bold;")
        tb.addWidget(self.lbl_match_counter)
        
        self.btn_next = QPushButton("Next")
        self.btn_next.setObjectName("IconButton")
        self.btn_next.clicked.connect(self._next_match)
        tb.addWidget(self.btn_next)
        
        tb.addSpacing(Spacing.LG)
        
        self.chk_sync = QCheckBox("Sync Scroll")
        self.chk_sync.setChecked(True)
        tb.addWidget(self.chk_sync)
        
        tb.addSpacing(Spacing.LG)
        
        self.btn_zoom_out = QPushButton("A-")
        self.btn_zoom_out.clicked.connect(lambda: self._set_zoom(-2))
        tb.addWidget(self.btn_zoom_out)
        
        self.lbl_zoom = QLabel("100%")
        tb.addWidget(self.lbl_zoom)
        
        self.btn_zoom_in = QPushButton("A+")
        self.btn_zoom_in.clicked.connect(lambda: self._set_zoom(2))
        tb.addWidget(self.btn_zoom_in)
        
        tb.addSpacing(Spacing.LG)
        
        self.btn_export = QPushButton("Export Report")
        self.btn_export.setObjectName("PrimaryButton")
        tb.addWidget(self.btn_export)
        
        self.root.addLayout(tb)

    def _build_stats_bar(self):
        sb = QHBoxLayout()
        sb.setSpacing(Spacing.MD)
        self.lbl_stats = QLabel("")
        self.lbl_stats.setStyleSheet(f"font-size: {Fonts.SIZE_BODY_LG}px; font-weight: bold; color: {Colors.TEXT_PRIMARY};")
        sb.addWidget(self.lbl_stats)
        
        sb.addStretch()
        
        def make_legend_item(text, color):
            lbl = QLabel(f"■ {text}")
            lbl.setStyleSheet(f"color: {color}; font-weight: bold;")
            return lbl
            
        sb.addWidget(make_legend_item("Exact", "#22C55E"))
        sb.addWidget(make_legend_item("Partial", "#F59E0B"))
        sb.addWidget(make_legend_item("Semantic", "#6366F1"))
        
        self.root.addLayout(sb)

    def _build_viewer(self):
        self.splitter = QSplitter(Qt.Horizontal)
        self.root.addWidget(self.splitter, 1)

    def load_report(self, model: ReportModel):
        self.report_model = model
        self.current_match_idx = -1
        self.current_zoom = Fonts.SIZE_BODY
        self.lbl_zoom.setText("100%")
        
        s = model.statistics
        ocr_text = "✓" if s.ocr_used else "✗"
        stats_text = f"Similarity {s.similarity_percent}%  |  Matches {s.total_matches}  |  Exact {s.exact_matches}  |  Partial {s.partial_matches}  |  Semantic {s.semantic_matches}  |  OCR Used {ocr_text}"
        self.lbl_stats.setText(stats_text)
        
        self._update_match_counter()
        
        for i in reversed(range(self.splitter.count())): 
            widget = self.splitter.widget(i)
            widget.deleteLater()
            
        self.left_viewer = DocumentViewer(model.left_document)
        self.right_viewer = DocumentViewer(model.right_document)
        
        self.splitter.addWidget(self.left_viewer)
        self.splitter.addWidget(self.right_viewer)
        
        self.left_viewer.scrolled.connect(self._on_left_scrolled)
        self.right_viewer.scrolled.connect(self._on_right_scrolled)
        self._is_syncing = False

    def _on_left_scrolled(self, value):
        if self.chk_sync.isChecked() and not self._is_syncing:
            self._is_syncing = True
            left_max = self.left_viewer.verticalScrollBar().maximum()
            if left_max > 0:
                ratio = value / left_max
                right_max = self.right_viewer.verticalScrollBar().maximum()
                self.right_viewer.verticalScrollBar().setValue(int(right_max * ratio))
            self._is_syncing = False

    def _on_right_scrolled(self, value):
        if self.chk_sync.isChecked() and not self._is_syncing:
            self._is_syncing = True
            right_max = self.right_viewer.verticalScrollBar().maximum()
            if right_max > 0:
                ratio = value / right_max
                left_max = self.left_viewer.verticalScrollBar().maximum()
                self.left_viewer.verticalScrollBar().setValue(int(left_max * ratio))
            self._is_syncing = False

    def _update_match_counter(self):
        if not self.report_model or not self.report_model.matches:
            self.lbl_match_counter.setText("Match 0 / 0")
            return
        self.lbl_match_counter.setText(f"Match {self.current_match_idx + 1} / {len(self.report_model.matches)}")

    def _next_match(self):
        if not self.report_model or not self.report_model.matches:
            return
        self.current_match_idx = (self.current_match_idx + 1) % len(self.report_model.matches)
        self._jump_to_match()

    def _prev_match(self):
        if not self.report_model or not self.report_model.matches:
            return
        if self.current_match_idx == -1:
            self.current_match_idx = len(self.report_model.matches) - 1
        else:
            self.current_match_idx = (self.current_match_idx - 1) % len(self.report_model.matches)
        self._jump_to_match()

    def _jump_to_match(self):
        self._update_match_counter()
        match = self.report_model.matches[self.current_match_idx]
        
        was_sync = self.chk_sync.isChecked()
        self.chk_sync.setChecked(False)
        
        self.left_viewer.scroll_to_paragraph(match.left_paragraph_index)
        self.right_viewer.scroll_to_paragraph(match.right_paragraph_index)
        
        self.chk_sync.setChecked(was_sync)

    def _on_search(self, query):
        if hasattr(self, 'left_viewer'):
            self.left_viewer.search(query)
        if hasattr(self, 'right_viewer'):
            self.right_viewer.search(query)

    def _set_zoom(self, delta: int):
        new_size = self.current_zoom + delta
        if 10 <= new_size <= 32:
            self.current_zoom = new_size
            pct = int((new_size / Fonts.SIZE_BODY) * 100)
            self.lbl_zoom.setText(f"{pct}%")
            if hasattr(self, 'left_viewer'):
                self.left_viewer.set_font_size(new_size)
            if hasattr(self, 'right_viewer'):
                self.right_viewer.set_font_size(new_size)
