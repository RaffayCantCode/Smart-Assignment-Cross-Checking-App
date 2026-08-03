"""
gui/report/document_viewer.py

Scrollable viewer that renders the complete contents of one document
using one ParagraphWidget per paragraph.

Public signals
--------------
  span_hovered(match_id, active)  — forwarded from the active ParagraphWidget
  span_clicked(match_id)          — forwarded from the clicked ParagraphWidget

Public methods
--------------
  set_active_match(match_id | None)
      Persist the active selection in the matching paragraph widget(s) and
      clear the previous active state.

  scroll_to_match_id(match_id)
      Center the paragraph containing the match and trigger a brief flash.
      Used by navigation events (sidebar, toolbar, keyboard).

  set_peer_span_highlight(match_id, active)
      Activate or deactivate the peer-hover highlight.  When activating,
      center the paragraph in the viewport without flashing (the
      ParagraphWidget handles the pulse animation internally).

  set_font_size(size) / search(query)
      Delegated to all paragraph widgets.

Scroll centering
----------------
  _center_widget_in_viewport(widget) positions the scroll bar so the
  widget is vertically centered in the viewport.  If the widget is already
  within the comfortable middle 60 % of the visible area the scroll
  position is left unchanged to avoid disorienting micro-scrolls.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QScrollArea, QWidget, QVBoxLayout

from .paragraph_widget import ParagraphWidget
from backend.reporting.model import ReportDocument
from styles.theme import Spacing


class DocumentViewer(QScrollArea):
    # Forwarded from whatever ParagraphWidget the mouse is over
    span_hovered = Signal(int, bool)
    # NEW: forwarded from whatever ParagraphWidget was clicked
    span_clicked = Signal(int)

    def __init__(self, document: ReportDocument, parent=None):
        super().__init__(parent)
        self.document = document
        self._active_match_id: int | None = None  # tracks current selection

        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        self.setObjectName("DocumentViewer")

        self.container = QWidget()
        self.container.setObjectName("DocumentViewerContainer")
        self.container.setStyleSheet(
            "#DocumentViewerContainer { background: transparent; }"
        )

        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(Spacing.MD)
        self.layout.setAlignment(Qt.AlignTop)

        self.setWidget(self.container)

        self.paragraph_widgets: dict[str, ParagraphWidget] = {}
        self._populate()

    def _populate(self):
        for p in self.document.paragraphs:
            pw = ParagraphWidget(p)
            pw.span_hovered.connect(self.span_hovered.emit)
            pw.span_clicked.connect(self.span_clicked.emit)  # NEW
            self.layout.addWidget(pw)
            self.paragraph_widgets[p.paragraph_id] = pw

    # ------------------------------------------------------------------
    # Viewport centering
    # ------------------------------------------------------------------

    def _center_widget_in_viewport(self, widget: QWidget):
        """
        Scroll so that `widget` is vertically centered in the viewport.

        If the widget's center is already within the comfortable middle
        60 % of the currently visible area, the scroll position is not
        changed to avoid disorienting micro-scrolls.

        Falls back to showing the widget's top edge when the widget is
        taller than the viewport.
        """
        widget_y = widget.pos().y()       # position within the scroll container
        widget_h = widget.height()
        viewport_h = self.viewport().height()
        vbar = self.verticalScrollBar()
        current_scroll = vbar.value()

        # Comfort-zone check: is the widget's centre already visible
        # in the middle 60 % of the viewport?
        widget_center = widget_y + widget_h // 2
        comfort_top    = current_scroll + viewport_h * 0.20
        comfort_bottom = current_scroll + viewport_h * 0.80

        if comfort_top <= widget_center <= comfort_bottom:
            return  # already comfortably visible — no scrolling needed

        if widget_h >= viewport_h:
            # Widget taller than viewport: align to top
            target = widget_y
        else:
            # Center the widget
            target = widget_y + widget_h // 2 - viewport_h // 2

        target = max(0, min(target, vbar.maximum()))
        vbar.setValue(target)

    # ------------------------------------------------------------------
    # Navigation scroll (with flash)
    # ------------------------------------------------------------------

    def scroll_to_match_id(self, match_id: int):
        """
        Navigate to a match: center it in the viewport and trigger a
        brief flash.  Called by sidebar clicks, toolbar Prev/Next, and
        keyboard navigation.
        """
        for pw in self.paragraph_widgets.values():
            if pw.has_match_id(match_id):
                self._center_widget_in_viewport(pw)
                pw.flash_match(match_id)
                return

    # ------------------------------------------------------------------
    # Legacy scroll helpers (kept for API compatibility)
    # ------------------------------------------------------------------

    def scroll_to_paragraph(self, paragraph_id: str):
        if paragraph_id in self.paragraph_widgets:
            pw = self.paragraph_widgets[paragraph_id]
            self._center_widget_in_viewport(pw)

    def scroll_to_index(self, index: int):
        for pw in self.paragraph_widgets.values():
            if pw.paragraph.index == index:
                self._center_widget_in_viewport(pw)
                pw.flash()
                return

    # ------------------------------------------------------------------
    # Active match state
    # ------------------------------------------------------------------

    def set_active_match(self, match_id: int | None):
        """
        Persistently highlight `match_id` as the selected match across
        all paragraph widgets.

        1. Clears the active state from the previous selection widget.
        2. Applies the active state to the new selection widget.

        Passing None clears without setting a new active match.
        """
        if self._active_match_id == match_id:
            return

        # Clear previous active widget
        if self._active_match_id is not None:
            for pw in self.paragraph_widgets.values():
                if pw.has_match_id(self._active_match_id):
                    pw.set_active_match(None)

        self._active_match_id = match_id

        # Activate new widget
        if match_id is not None:
            for pw in self.paragraph_widgets.values():
                if pw.has_match_id(match_id):
                    pw.set_active_match(match_id)

    # ------------------------------------------------------------------
    # Peer hover sync (called from the opposite DocumentViewer)
    # ------------------------------------------------------------------

    def set_peer_span_highlight(self, match_id: int, active: bool):
        """
        Highlight or unhighlight the peer span when the user hovers in
        the opposite document.

        When activating:
        - The ParagraphWidget is told to start its pulse animation.
        - The viewport is centered on the paragraph (no additional flash;
          the pulse itself provides the visual cue).

        When deactivating:
        - The ParagraphWidget clears the peer highlight and stops the timer.
        - No scrolling occurs on deactivation.
        """
        for pw in self.paragraph_widgets.values():
            if pw.has_match_id(match_id):
                pw.set_peer_match_highlight(match_id, active)

        if active:
            # Center without flash — pulse animation is handled by ParagraphWidget
            for pw in self.paragraph_widgets.values():
                if pw.has_match_id(match_id):
                    self._center_widget_in_viewport(pw)
                    break

    # ------------------------------------------------------------------
    # Delegated to all paragraph widgets
    # ------------------------------------------------------------------

    def set_font_size(self, size: int):
        for pw in self.paragraph_widgets.values():
            pw.set_font_size(size)

    def search(self, query: str):
        for pw in self.paragraph_widgets.values():
            pw.highlight_search(query)
