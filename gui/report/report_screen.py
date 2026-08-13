"""
gui/report/report_screen.py

Detailed Report page.  Layout (all rows fixed except the workspace):

  ┌─ _Toolbar  (Back · Search · Prev/Next · Zoom · Export) ────────┐
  ├─ ReportHeader  (Score arc · Doc names · Timestamp · Risk) ──────┤
  ├─ _StatsBar  (Similarity · Total · Exact · Partial · Semantic) ──┤
  ├──────────────────────────────┬──────────────────────────────────┤
  │  Document A (_DocPanel)      │  Document B (_DocPanel)          │
  │  DocumentViewer (scrollable) │  DocumentViewer (scrollable)     │
  │                              │                 ┌────────────────┤
  │                              │                 │ _ReportSidebar │
  │                              │                 │  MatchSidebar  │
  │                              │                 │  AI Analysis   │
  │                              │                 │  Recommendations│
  └──────────────────────────────┴─────────────────┴────────────────┘

The top three rows never scroll.  The three-panel QSplitter fills the
remaining window height so the document viewers get their own scroll
areas — eliminating the nested-scrollbar anti-pattern noted in the
review.  The sidebar receives AI Analysis and Recommendations so they
stay visible alongside the documents.

Hover-sync is wired here:
    left_viewer.span_hovered  → right_viewer.set_peer_span_highlight
    right_viewer.span_hovered → left_viewer.set_peer_span_highlight

Sidebar active state is kept in sync with Prev/Next toolbar buttons
via _jump_to_match calling self.sidebar.set_active(idx).
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QSplitter, QFrame, QFileDialog,
)

from styles.theme import Colors, Fonts, Spacing, Radius
from backend.reporting.model import ReportModel
from backend.reporting import ReportBuilder
from backend.reporting.exporter import (
    export_report,
    build_report_filename,
    build_save_file_filter,
    resolve_export_extension,
)
from backend.domain.comparison import ComparisonResult
from gui.settings_manager import get_export_config
from .document_viewer import DocumentViewer
from .report_header import ReportHeader
from .match_sidebar import MatchSidebar


# ---------------------------------------------------------------------------
# AI text helpers  (UI-facing; mirrors exporter logic without file I/O)
# ---------------------------------------------------------------------------

def _build_ai_summary(model: ReportModel) -> str:
    s = model.statistics
    if s.similarity_percent >= 70:
        text = (
            f"The assignments share a highly significant amount of semantic "
            f"meaning ({s.similarity_percent}% similarity). {s.total_matches} "
            f"highly similar paragraphs were found, indicating potential copying "
            f"or heavy collaboration."
        )
    elif s.similarity_percent >= 40:
        text = (
            f"There is moderate overlap in the concepts discussed "
            f"({s.similarity_percent}% similarity). {s.total_matches} paragraphs "
            f"show structural or semantic similarities."
        )
    else:
        text = (
            f"The assignments appear to be largely independent "
            f"({s.similarity_percent}% similarity). {s.total_matches} brief "
            f"section(s) showed minor similarities."
        )
    if s.ocr_used:
        text += " OCR was used for scanned content during extraction."
    return text


def _build_recommendations(model: ReportModel) -> str:
    s = model.statistics
    if s.similarity_percent >= 70:
        return (
            f"Similarity is critically elevated ({s.similarity_percent}%). "
            f"Immediate manual review of all {s.total_matches} matched paragraphs "
            f"is strongly recommended. Consider flagging this submission for "
            f"academic integrity review."
        )
    return (
        f"Similarity is elevated ({s.similarity_percent}%). Manual review of "
        f"the {s.total_matches} matched paragraphs is recommended."
    )


# ---------------------------------------------------------------------------
# Internal widgets
# ---------------------------------------------------------------------------

class _StatsBar(QFrame):
    def __init__(self, model: ReportModel, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setStyleSheet(f"""
            #Card {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: {Radius.MD}px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.SM, Spacing.LG, Spacing.SM)
        layout.setSpacing(Spacing.XL)

        s = model.statistics

        def stat_item(label: str, value: str, color: str = Colors.TEXT_PRIMARY):
            item = QVBoxLayout()
            item.setSpacing(0)
            val = QLabel(value)
            val.setStyleSheet(
                f"font-size: {Fonts.SIZE_H3}px; font-weight: 700; "
                f"color: {color}; background: transparent;"
            )
            lbl = QLabel(label)
            lbl.setStyleSheet(
                f"font-size: {Fonts.SIZE_SMALL}px; "
                f"color: {Colors.TEXT_MUTED}; background: transparent;"
            )
            item.addWidget(val)
            item.addWidget(lbl)
            return item

        similarity_color = (
            Colors.SUCCESS if s.similarity_percent < 40
            else Colors.WARNING if s.similarity_percent < 70
            else Colors.DANGER
        )

        layout.addLayout(stat_item("Similarity", f"{s.similarity_percent}%", similarity_color))
        layout.addLayout(stat_item("Total Matches", str(s.total_matches)))
        layout.addLayout(stat_item("Exact", str(s.exact_matches), Colors.SUCCESS))
        layout.addLayout(stat_item("Partial", str(s.partial_matches), Colors.WARNING))
        layout.addLayout(stat_item("Semantic", str(s.semantic_matches), Colors.ACCENT_HOVER))
        layout.addLayout(stat_item("Unique", str(s.unique_paragraphs), Colors.TEXT_MUTED))

        if s.ocr_used:
            conf_text = f"{s.avg_ocr_confidence:.0%}" if s.avg_ocr_confidence > 0 else "N/A"
            layout.addLayout(stat_item("OCR Used", conf_text, Colors.ACCENT))

        layout.addStretch()


class _Toolbar(QFrame):
    back_requested = Signal()
    search_changed = Signal(str)
    prev_requested = Signal()
    next_requested = Signal()
    zoom_changed = Signal(int)
    export_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: transparent;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, Spacing.SM)
        layout.setSpacing(Spacing.MD)

        self.btn_back = QPushButton("Back to Results")
        self.btn_back.setObjectName("SecondaryButton")
        self.btn_back.clicked.connect(self.back_requested.emit)
        layout.addWidget(self.btn_back)

        layout.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search paragraphs...")
        self.search_input.setFixedWidth(220)
        self.search_input.setStyleSheet(
            f"font-size: {Fonts.SIZE_BODY}px; "
            f"background-color: {Colors.BG_SURFACE_ALT}; "
            f"color: {Colors.TEXT_PRIMARY}; "
            f"border: 1px solid {Colors.BORDER}; "
            f"border-radius: {Radius.SM}px; "
            f"padding: 6px 12px;"
        )
        self.search_input.textChanged.connect(self.search_changed.emit)
        layout.addWidget(self.search_input)

        layout.addSpacing(Spacing.MD)

        self.btn_prev = QPushButton("◀ Prev")
        self.btn_prev.setObjectName("GhostButton")
        self.btn_prev.clicked.connect(self.prev_requested.emit)
        layout.addWidget(self.btn_prev)

        self.lbl_match_counter = QLabel("0 / 0")
        self.lbl_match_counter.setStyleSheet(
            f"font-size: {Fonts.SIZE_BODY}px; "
            f"font-weight: 600; "
            f"color: {Colors.TEXT_PRIMARY}; "
            f"min-width: 60px; "
            f"alignment: center;"
        )
        self.lbl_match_counter.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_match_counter)

        self.btn_next = QPushButton("Next ▶")
        self.btn_next.setObjectName("GhostButton")
        self.btn_next.clicked.connect(self.next_requested.emit)
        layout.addWidget(self.btn_next)

        layout.addSpacing(Spacing.MD)

        self.btn_zoom_out = QPushButton("A−")
        self.btn_zoom_out.setObjectName("GhostButton")
        self.btn_zoom_out.clicked.connect(lambda: self.zoom_changed.emit(-2))
        layout.addWidget(self.btn_zoom_out)

        self.lbl_zoom = QLabel("100%")
        self.lbl_zoom.setStyleSheet(
            f"font-size: {Fonts.SIZE_BODY}px; "
            f"color: {Colors.TEXT_MUTED}; "
            f"min-width: 40px; "
            f"alignment: center;"
        )
        self.lbl_zoom.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_zoom)

        self.btn_zoom_in = QPushButton("A+")
        self.btn_zoom_in.setObjectName("GhostButton")
        self.btn_zoom_in.clicked.connect(lambda: self.zoom_changed.emit(2))
        layout.addWidget(self.btn_zoom_in)

        layout.addSpacing(Spacing.MD)

        self.btn_export = QPushButton("Generate PDF Report")
        self.btn_export.setObjectName("PrimaryButton")
        self.btn_export.clicked.connect(self.export_requested.emit)
        layout.addWidget(self.btn_export)

    def set_match_counter(self, current: int, total: int):
        self.lbl_match_counter.setText(f"{current} / {total}")

    def set_zoom_text(self, pct: int):
        self.lbl_zoom.setText(f"{pct}%")


class _DocPanel(QWidget):
    """
    One column of the document split-view.

    A fixed 36 px header strip (side label + document title) sits above
    a DocumentViewer that fills all remaining height.  Exposes `viewer`
    so ReportScreen can wire scroll-sync and hover-sync signals without
    reaching into the panel's internal layout.
    """

    def __init__(self, document, label: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Fixed header strip
        header = QFrame()
        header.setObjectName("DocPanelHeader")
        header.setFixedHeight(36)
        header.setStyleSheet(f"""
            #DocPanelHeader {{
                background-color: {Colors.BG_SURFACE};
                border: none;
                border-bottom: 1px solid {Colors.BORDER};
            }}
        """)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(Spacing.MD, 0, Spacing.MD, 0)

        side_lbl = QLabel(label)
        side_lbl.setObjectName("SectionLabel")
        hl.addWidget(side_lbl)

        hl.addStretch()

        title_lbl = QLabel(document.title or "—")
        title_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_SMALL}px; "
            f"color: {Colors.TEXT_SECONDARY}; background: transparent;"
        )
        title_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        hl.addWidget(title_lbl)

        layout.addWidget(header)

        self.viewer = DocumentViewer(document)
        layout.addWidget(self.viewer, 1)


class _SidebarSection(QFrame):
    """
    A compact titled text block for the sidebar's AI Analysis and
    Recommendations panels.  A coloured left border distinguishes
    each section type without relying on heavy card backgrounds.
    """

    def __init__(self, title: str, text: str, accent_color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("SidebarSection")
        self.setStyleSheet(f"""
            #SidebarSection {{
                background-color: {Colors.BG_SURFACE_ALT};
                border: none;
                border-top: 1px solid {Colors.BORDER};
                border-left: 3px solid {accent_color};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        layout.setSpacing(Spacing.XS)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("SectionLabel")
        layout.addWidget(title_lbl)

        text_lbl = QLabel(text)
        text_lbl.setWordWrap(True)
        text_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_SMALL}px; "
            f"color: {Colors.TEXT_SECONDARY}; background: transparent;"
        )
        layout.addWidget(text_lbl)


class _ReportSidebar(QWidget):
    """
    Right-hand sidebar: match list (scrollable) + AI Analysis +
    Recommendations (conditional on similarity >= 40 %).

    Moving AI/Recs here keeps them always visible alongside the
    documents — addressing review point 1 (layout orchestration).
    """

    match_selected = Signal(int)

    def __init__(self, model: ReportModel, parent=None):
        super().__init__(parent)
        self.setObjectName("ReportSidebar")
        self.setMinimumWidth(220)
        self.setStyleSheet(
            f"#ReportSidebar {{ background-color: {Colors.BG_SURFACE}; }}"
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Match list — takes all available vertical space
        self.match_sidebar = MatchSidebar(model)
        self.match_sidebar.match_selected.connect(self.match_selected.emit)
        outer.addWidget(self.match_sidebar, 1)

        # AI analysis panel — always shown
        outer.addWidget(
            _SidebarSection("AI ANALYSIS", _build_ai_summary(model), Colors.ACCENT)
        )

        # Recommendations panel — only when similarity warrants it
        if model.statistics.similarity_percent >= 40:
            outer.addWidget(
                _SidebarSection(
                    "RECOMMENDATIONS",
                    _build_recommendations(model),
                    Colors.WARNING,
                )
            )

    def set_active(self, index: int):
        """Delegate active-card update to the inner MatchSidebar."""
        self.match_sidebar.set_active(index)


# ---------------------------------------------------------------------------
# Main screen
# ---------------------------------------------------------------------------

class ReportScreen(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._report_model: ReportModel = None
        self._current_match_idx = -1
        self._current_zoom = Fonts.SIZE_BODY
        self._search_results = ()

        root = QVBoxLayout(self)
        root.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
        root.setSpacing(Spacing.MD)

        # Toolbar — always pinned at the top, never scrolls out of view
        self.toolbar = _Toolbar()
        root.addWidget(self.toolbar)

        # Report header placeholder.  Replaced by a real ReportHeader
        # on each load_report() using the swap-at-index pattern.
        self._report_header_widget: QFrame = QFrame()
        self._report_header_widget.setVisible(False)
        root.addWidget(self._report_header_widget)

        # Stats bar placeholder — same swap pattern as the original code
        self.stats_bar: QFrame = QFrame()
        self.stats_bar.setVisible(False)
        root.addWidget(self.stats_bar)

        # Workspace splitter: Doc A | Doc B | Sidebar
        # stretch=1 → fills every pixel of remaining window height.
        # Each panel owns its own scroll area; no outer scroll is needed.
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setStyleSheet(
            f"QSplitter::handle {{ background-color: {Colors.BORDER}; width: 1px; }}"
        )
        root.addWidget(self.splitter, 1)

        # Thin status bar at the very bottom
        self.status_bar = QLabel("")
        self.status_bar.setStyleSheet(
            f"font-size: {Fonts.SIZE_SMALL}px; "
            f"color: {Colors.TEXT_MUTED}; "
            f"padding: {Spacing.XS}px 0;"
        )
        root.addWidget(self.status_bar)

        self._connect_toolbar()

    # ------------------------------------------------------------------
    # Wiring
    # ------------------------------------------------------------------

    def _connect_toolbar(self):
        self.toolbar.back_requested.connect(self.back_requested.emit)
        self.toolbar.search_changed.connect(self._on_search)
        self.toolbar.prev_requested.connect(self._prev_match)
        self.toolbar.next_requested.connect(self._next_match)
        self.toolbar.zoom_changed.connect(self._on_zoom)
        self.toolbar.export_requested.connect(self._on_export)

    # ------------------------------------------------------------------
    # Public load API  (interface unchanged from original)
    # ------------------------------------------------------------------

    def load_comparison(self, result: ComparisonResult):
        model = ReportBuilder.build(result)
        self.load_report(model)

    def load_report(self, model: ReportModel):
        self._report_model = model
        self._current_match_idx = -1
        self._current_zoom = Fonts.SIZE_BODY
        self._search_results = ()

        self.toolbar.set_match_counter(0, len(model.matches))
        self.toolbar.set_zoom_text(100)

        # Rebuild fixed-top header sections
        self._rebuild_report_header(model)
        self._rebuild_stats_bar(model)

        # Clear previous workspace panels.  The panels must be detached from
        # the splitter *synchronously* before re-adding, otherwise the deferred
        # deleteLater() leaves stale panels inside the splitter and the two
        # document panes end up mis-laid-out (Document B pushed off) on
        # repeat loads of the same report.
        while self.splitter.count():
            w = self.splitter.widget(0)
            w.setParent(None)
            w.deleteLater()

        # Document panels — expose .viewer for signal wiring below
        left_panel = _DocPanel(model.left_document, "DOCUMENT A")
        right_panel = _DocPanel(model.right_document, "DOCUMENT B")
        self.left_viewer = left_panel.viewer
        self.right_viewer = right_panel.viewer

        # Sidebar — match list + AI + recommendations
        self.sidebar = _ReportSidebar(model)
        self.sidebar.match_selected.connect(self._on_sidebar_match)

        # Prevent panels from collapsing completely and set minimum sizes for usability
        left_panel.setMinimumWidth(300)
        right_panel.setMinimumWidth(300)
        self.sidebar.setMinimumWidth(240)

        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(right_panel)
        self.splitter.addWidget(self.sidebar)

        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        self.splitter.setCollapsible(2, False)

        # Equal-weight document panes (1:1:0) guarantee Document A and B are
        # always laid out side by side and share the available width evenly,
        # regardless of document length or window size.  The sidebar keeps
        # its natural width and never steals space from the documents.
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)

        # Initial proportions: 40 % / 40 % / 20 %
        self.splitter.setSizes([400, 400, 240])

        # Span-level cross-document hover sync
        self.left_viewer.span_hovered.connect(self.right_viewer.set_peer_span_highlight)
        self.right_viewer.span_hovered.connect(self.left_viewer.set_peer_span_highlight)

        # Span click → match navigation (same path as sidebar / toolbar)
        self.left_viewer.span_clicked.connect(self._on_span_clicked)
        self.right_viewer.span_clicked.connect(self._on_span_clicked)

        self.toolbar.search_input.clear()
        self.status_bar.setText(
            f"Loaded "
            f"{len(model.left_document.paragraphs) + len(model.right_document.paragraphs)} "
            f"paragraphs | {len(model.matches)} matches"
        )

    # ------------------------------------------------------------------
    # Header rebuilds  (swap-at-index pattern from original _StatsBar)
    # ------------------------------------------------------------------

    def _rebuild_report_header(self, model: ReportModel):
        old = self._report_header_widget
        new_header = ReportHeader(model)
        parent_layout = self.layout()
        idx = parent_layout.indexOf(old)
        parent_layout.insertWidget(idx, new_header)
        old.deleteLater()
        self._report_header_widget = new_header

    def _rebuild_stats_bar(self, model: ReportModel):
        old = self.stats_bar
        self.stats_bar = _StatsBar(model)
        self.stats_bar.setVisible(True)
        parent_layout = self.layout()
        if old:
            idx = parent_layout.indexOf(old)
            parent_layout.insertWidget(idx, self.stats_bar)
            old.deleteLater()
        else:
            parent_layout.insertWidget(2, self.stats_bar)

    # ------------------------------------------------------------------
    # Match navigation
    # ------------------------------------------------------------------

    def _next_match(self):
        if not self._report_model or not self._report_model.matches:
            return
        total = len(self._report_model.matches)
        self._current_match_idx = (self._current_match_idx + 1) % total
        self._jump_to_match()

    def _prev_match(self):
        if not self._report_model or not self._report_model.matches:
            return
        total = len(self._report_model.matches)
        if self._current_match_idx <= 0:
            self._current_match_idx = total - 1
        else:
            self._current_match_idx = (self._current_match_idx - 1) % total
        self._jump_to_match()

    def _jump_to_match(self):
        """
        Unified navigation core — called by every navigation trigger:
        sidebar click, toolbar Prev/Next, span click, and any future
        keyboard shortcut.

        Sets the persistent active match state on both viewers, then
        centers and flashes the match.  Toolbar counter and sidebar
        active card are kept in sync.
        """
        if not self._report_model or not self._report_model.matches:
            return
        idx = self._current_match_idx
        match = self._report_model.matches[idx]
        match_id = match.match_id

        self.toolbar.set_match_counter(idx + 1, len(self._report_model.matches))

        # Persist the active selection in both document viewers
        self.left_viewer.set_active_match(match_id)
        self.right_viewer.set_active_match(match_id)

        # Center each viewer on the match and trigger a brief attention flash
        self.left_viewer.scroll_to_match_id(match_id)
        self.right_viewer.scroll_to_match_id(match_id)

        # Keep the sidebar card highlight in sync with toolbar navigation
        if hasattr(self, 'sidebar'):
            self.sidebar.set_active(idx)

    def _on_sidebar_match(self, index: int):
        """Called when the user clicks a match card in the sidebar."""
        self._current_match_idx = index
        self._jump_to_match()

    def _on_span_clicked(self, match_id: int):
        """
        Called when the user clicks a highlighted span in either viewer.

        Looks up the corresponding match index so that the toolbar counter
        and sidebar active card stay in sync, then delegates to the single
        shared _jump_to_match() path.
        """
        if not self._report_model:
            return
        for i, m in enumerate(self._report_model.matches):
            if m.match_id == match_id:
                self._current_match_idx = i
                self._jump_to_match()
                return

    # ------------------------------------------------------------------
    # Search, zoom, export  (unchanged from original)
    # ------------------------------------------------------------------

    def _on_search(self, query: str):
        if not self._report_model:
            return
        self._search_results = self._report_model.search(query)

        if hasattr(self, 'left_viewer'):
            self.left_viewer.search(query)
        if hasattr(self, 'right_viewer'):
            self.right_viewer.search(query)

        count = len(self._search_results)
        if query:
            self.status_bar.setText(f"Search: {count} result{'s' if count != 1 else ''} found")
        else:
            self.status_bar.setText("")

    def _on_zoom(self, delta: int):
        new_size = self._current_zoom + delta
        if 10 <= new_size <= 32:
            self._current_zoom = new_size
            pct = int((new_size / Fonts.SIZE_BODY) * 100)
            self.toolbar.set_zoom_text(pct)
            if hasattr(self, 'left_viewer'):
                self.left_viewer.set_font_size(new_size)
            if hasattr(self, 'right_viewer'):
                self.right_viewer.set_font_size(new_size)

    def _on_export(self):
        if not self._report_model:
            return
        export_cfg = get_export_config()
        default_fmt = export_cfg.get("export_format", "pdf")
        assignment_name = self._report_model.left_document.title or "Assignment"
        if self._report_model.right_document and self._report_model.right_document.title:
            assignment_name = (
                f"{assignment_name} vs {self._report_model.right_document.title}"
            )
        suggested_name = build_report_filename(assignment_name, default_fmt)

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Generate Report", suggested_name,
            build_save_file_filter(default_fmt)
        )

        if not file_path:
            return  # Exit cleanly if user cancels dialog

        file_path, ext = resolve_export_extension(file_path, selected_filter, default_fmt)

        out_file = export_report(self._report_model, file_path, ext, options=export_cfg)
        from gui.notifications import notify_report_exported
        notify_report_exported(out_file)
