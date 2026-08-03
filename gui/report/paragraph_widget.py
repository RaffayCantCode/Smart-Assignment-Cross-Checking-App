"""
gui/report/paragraph_widget.py

Renders one full paragraph of a document with inline per-match span
highlights.  The widget supports three distinct interactive states that
can coexist without conflict:

  normal      — soft tint over a matched span (always visible)
  peer-hover  — medium background + underline when the user hovers the
                corresponding span in the opposite document; accompanied
                by a brief bright pulse so the eye is drawn to it
  active      — strong persistent background + underline for the
                currently selected match; remains until another match
                is selected

Performance note
----------------
State transitions driven by hover events (peer-hover, pulse) use
`_update_span_formats_only()`, which touches only the character formats
of the affected spans without rebuilding the QTextDocument.  Full
rebuilds (`_render_text`) are reserved for one-shot events: initial
render, search query changes, and the brief navigation flash.

Public signals
--------------
  span_hovered(match_id, active)  — mouse entered/left a highlighted span
  span_clicked(match_id)          — user clicked a highlighted span

Public methods
--------------
  set_active_match(match_id | None)         — persist active selection
  set_peer_match_highlight(match_id, active) — peer hover state
  flash_match(match_id)                     — brief navigation flash
  highlight_search(query)                   — search overlay
  set_font_size(size)
"""

import re

from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import (
    QTextCharFormat, QTextCursor, QColor, QFont,
)
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTextEdit, QSizePolicy,
)

from backend.reporting.model import ReportParagraph
from styles.theme import Colors, Fonts, Spacing
from .match_colors import get_match_color, get_match_bg

# Custom property key stored on every span's QTextCharFormat so we can
# recover the match_id from a cursor position during hover/click.
_MATCH_ID_FORMAT = QTextCharFormat.UserProperty + 1

_SEARCH_BG = Colors.ACCENT_SOFT
_SEARCH_FG = Colors.ACCENT


class ParagraphWidget(QFrame):
    """Renders one full paragraph with inline per-match span highlights."""

    # Emitted when the mouse enters/leaves a highlighted span in this widget.
    # The peer DocumentViewer is wired to this to sync the opposite panel.
    span_hovered = Signal(int, bool)

    # NEW: emitted when the user clicks a highlighted span.
    # ReportScreen wires this to _on_span_clicked which navigates to the match.
    span_clicked = Signal(int)

    def __init__(self, paragraph: ReportParagraph, parent=None):
        super().__init__(parent)
        self.paragraph = paragraph
        self._search_query = ""

        # --- Interactive state fields ---
        # flash: temporary bright highlight triggered on navigation jump
        self._flash_match_id: int | None = None
        # peer: span in this widget is the hover-target from the opposite doc
        self._peer_match_id: int | None = None
        # hovered: span the local mouse is currently over (for span_hovered emit)
        self._hovered_match_id: int | None = None
        # active: persistent selection; cleared only when another match is chosen
        self._active_match_id: int | None = None
        # pulse: drives the 2-step peer-arrive animation (0=off, 1=bright)
        self._pulse_step: int = 0

        # flash timer — clears navigation flash after 450 ms
        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.timeout.connect(self._end_flash)

        # pulse timer — settles peer highlight from bright → normal after 220 ms
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setSingleShot(True)
        self._pulse_timer.timeout.connect(self._end_pulse)

        self.setObjectName("ParagraphWidget")
        self.setMouseTracking(True)

        # --- Layout ---
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFrameShape(QFrame.NoFrame)
        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.text_edit.setStyleSheet(
            f"QTextEdit {{ "
            f"background: transparent; "
            f"color: {Colors.TEXT_PRIMARY}; "
            f"border: none; "
            f"padding: 0px {Spacing.MD}px; "
            f"}}"
        )
        self.text_edit.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_BODY))
        self.text_edit.setMouseTracking(True)
        self.text_edit.viewport().setMouseTracking(True)
        self.text_edit.viewport().installEventFilter(self)
        self.root_layout.addWidget(self.text_edit)

        self.root_layout.addSpacing(Spacing.XS)
        self._apply_frame_styles()
        self._render_text()

    # ------------------------------------------------------------------
    # Event filter — hover tracking + span click detection
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event):
        if obj is self.text_edit.viewport():
            et = event.type()
            if et == event.Type.MouseMove:
                self._update_hover_from_pos(event.position().toPoint())
            elif et == event.Type.MouseButtonPress:
                # Left-click on a highlighted span navigates to that match.
                if event.button() == Qt.LeftButton:
                    self._on_viewport_click(event.position().toPoint())
            elif et in (event.Type.Leave, event.Type.HoverLeave):
                self._clear_hover()
        return super().eventFilter(obj, event)

    def _on_viewport_click(self, pos):
        """Emit span_clicked if the cursor is over a highlighted span."""
        match_id = self._match_id_at_pos(pos)
        if match_id:
            self.span_clicked.emit(match_id)

    def _update_hover_from_pos(self, pos):
        match_id = self._match_id_at_pos(pos)
        if match_id == self._hovered_match_id:
            return
        if self._hovered_match_id:
            self.span_hovered.emit(self._hovered_match_id, False)
        self._hovered_match_id = match_id
        if match_id:
            self.span_hovered.emit(match_id, True)

    def _clear_hover(self):
        if self._hovered_match_id:
            self.span_hovered.emit(self._hovered_match_id, False)
            self._hovered_match_id = None

    def _match_id_at_pos(self, pos) -> int | None:
        """Return the match_id of the highlighted span under the cursor, or None."""
        cursor = self.text_edit.cursorForPosition(pos)
        match_id = cursor.charFormat().property(_MATCH_ID_FORMAT)
        if match_id is None:
            return None
        try:
            value = int(match_id)
        except (TypeError, ValueError):
            return None
        return value if value > 0 else None

    def has_match_id(self, match_id: int) -> bool:
        return any(s.match_id == match_id for s in self.paragraph.spans)

    # ------------------------------------------------------------------
    # Frame background styling (widget-level, not character-level)
    # ------------------------------------------------------------------

    def _apply_frame_styles(self):
        """
        Update the widget's background and left-border based on state.

        Priority (highest → lowest): active > flash > peer > none.
        Active uses the match's own colour; flash uses the accent colour;
        peer uses the match colour at a lower opacity.
        """
        if self._active_match_id and self.has_match_id(self._active_match_id):
            color = get_match_color(self._active_match_id)
            bg = "transparent"
            left = f"border-left: 3px solid {color};"
        elif self._flash_match_id:
            bg = f"#28{Colors.ACCENT[1:]}"
            left = f"border-left: 2px solid {Colors.ACCENT};"
        elif self._peer_match_id:
            color = get_match_color(self._peer_match_id)
            bg = f"#18{color[1:]}"
            left = f"border-left: 2px solid {color};"
        else:
            bg = "transparent"
            left = ""

        self.setStyleSheet(f"""
            ParagraphWidget {{
                background-color: {bg};
                border: none;
                {left}
                border-radius: 0px;
                margin: 0px;
            }}
        """)


    # ------------------------------------------------------------------
    # Span character formatting
    # ------------------------------------------------------------------

    def _span_format(
        self,
        match_id: int,
        *,
        peer: bool = False,
        flash: bool = False,
        active: bool = False,
        pulse: bool = False,
    ) -> QTextCharFormat:
        """
        Build the QTextCharFormat for a highlighted span.

        Priority (highest → lowest): flash/pulse > active > peer > normal.

        flash/pulse  — solid match colour, bold; used for navigation jump
                       and peer-hover arrival animation
        active       — strong semi-transparent background, bold, underline;
                       persists until another match is selected
        peer         — medium semi-transparent background, bold, underline;
                       shown while hovering in the opposite document
        normal       — soft tint; always visible on matched spans
        """
        fmt = QTextCharFormat()
        color = get_match_color(match_id)

        if flash or pulse:
            # Brightest state: draw immediate attention
            fmt.setBackground(QColor(color))
            fmt.setFontWeight(QFont.Bold)
        elif active:
            # Persistent selection: clearly stronger than normal, subtler than flash
            fmt.setBackground(QColor(get_match_bg(match_id, "BB")))
            fmt.setFontWeight(QFont.Bold)
            fmt.setUnderlineStyle(QTextCharFormat.SingleUnderline)
            fmt.setUnderlineColor(QColor(color))
        elif peer:
            # Peer hover (settled after pulse): medium intensity
            fmt.setBackground(QColor(get_match_bg(match_id, "88")))
            fmt.setFontWeight(QFont.Bold)
            fmt.setUnderlineStyle(QTextCharFormat.SingleUnderline)
            fmt.setUnderlineColor(QColor(color))
        else:
            # Normal highlighted span: always-on soft tint
            fmt.setBackground(QColor(get_match_bg(match_id, "55")))
            fmt.setFontUnderline(False)

        # Stamp the match_id into the format so _match_id_at_pos can recover it
        fmt.setProperty(_MATCH_ID_FORMAT, match_id)
        return fmt

    def _plain_format(self) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(Colors.TEXT_PRIMARY))
        return fmt

    # ------------------------------------------------------------------
    # Document rendering
    # ------------------------------------------------------------------

    def _render_text(self):
        """
        Full document rebuild.

        Called only for: initial render, search query changes, flash
        start/end.  Hover-driven state changes use _update_span_formats_only()
        to avoid the cost of rebuilding the entire QTextDocument.
        """
        text = self.paragraph.text
        doc = self.text_edit.document()
        doc.clear()
        cursor = QTextCursor(doc)

        if self.paragraph.spans:
            sorted_spans = sorted(self.paragraph.spans, key=lambda s: s.char_start)
            pos = 0
            for span in sorted_spans:
                if span.char_start > pos:
                    cursor.setCharFormat(self._plain_format())
                    cursor.insertText(text[pos:span.char_start])

                is_flash  = self._flash_match_id == span.match_id
                is_peer   = self._peer_match_id  == span.match_id
                is_active = self._active_match_id == span.match_id
                is_pulse  = (self._pulse_step == 1 and is_peer)

                cursor.setCharFormat(
                    self._span_format(
                        span.match_id,
                        peer=is_peer,
                        flash=is_flash,
                        active=is_active,
                        pulse=is_pulse,
                    )
                )
                cursor.insertText(text[span.char_start:span.char_end])
                pos = span.char_end

            if pos < len(text):
                cursor.setCharFormat(self._plain_format())
                cursor.insertText(text[pos:])
        else:
            cursor.setCharFormat(self._plain_format())
            cursor.insertText(text)

        if self._search_query:
            self._apply_search_highlight()

        self._adjust_text_height()

    def _update_span_formats_only(self):
        """
        Localized in-place update of span character formats.

        Iterates only over the paragraph's spans and sets their
        QTextCharFormat directly via positioned QTextCursors.
        The rest of the document text is untouched.

        Cost: O(number of spans), not O(length of text).
        Called by: set_active_match, set_peer_match_highlight, pulse animation.
        """
        if not self.paragraph.spans:
            return

        doc = self.text_edit.document()
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()

        for span in self.paragraph.spans:
            is_flash  = self._flash_match_id == span.match_id
            is_peer   = self._peer_match_id  == span.match_id
            is_active = self._active_match_id == span.match_id
            is_pulse  = (self._pulse_step == 1 and is_peer)

            fmt = self._span_format(
                span.match_id,
                peer=is_peer,
                flash=is_flash,
                active=is_active,
                pulse=is_pulse,
            )
            c = QTextCursor(doc)
            c.setPosition(span.char_start)
            c.setPosition(span.char_end, QTextCursor.KeepAnchor)
            c.setCharFormat(fmt)

        cursor.endEditBlock()

    def _apply_search_highlight(self):
        if not self._search_query:
            return
        doc = self.text_edit.document()
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()
        plain = self.paragraph.text
        pattern = re.compile(re.escape(self._search_query), re.IGNORECASE)
        search_fmt = QTextCharFormat()
        search_fmt.setBackground(QColor(_SEARCH_BG))
        search_fmt.setForeground(QColor(_SEARCH_FG))

        for match in pattern.finditer(plain):
            c = QTextCursor(doc)
            c.setPosition(match.start())
            c.setPosition(match.end(), QTextCursor.KeepAnchor)
            c.mergeCharFormat(search_fmt)
        cursor.endEditBlock()

    def _adjust_text_height(self):
        doc = self.text_edit.document()
        width = max(self.text_edit.viewport().width(), 200)
        doc.setTextWidth(width)
        height = int(doc.size().height()) + 8
        self.text_edit.setFixedHeight(height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adjust_text_height()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_font_size(self, size: int):
        font = self.text_edit.font()
        font.setPointSize(size)
        self.text_edit.setFont(font)
        self._adjust_text_height()

    def highlight_search(self, query: str):
        self._search_query = query or ""
        self._render_text()

    def set_peer_match_highlight(self, match_id: int, active: bool):
        """
        Called from the peer DocumentViewer when the user hovers/leaves
        a corresponding span in the opposite document.

        Uses _update_span_formats_only (not _render_text) for O(spans) cost.
        Activating triggers _start_pulse() for the arrival animation.
        """
        new_id = match_id if active else None
        if self._peer_match_id == new_id:
            return
        self._peer_match_id = new_id
        if active:
            self._start_pulse()
        else:
            self._pulse_step = 0
            self._pulse_timer.stop()
            self._update_span_formats_only()
        self._apply_frame_styles()

    def set_active_match(self, match_id: int | None):
        """
        Persistently mark `match_id` as the active (selected) match.

        Passing None clears the active state.
        Uses _update_span_formats_only — does not rebuild the document.
        """
        if self._active_match_id == match_id:
            return
        self._active_match_id = match_id
        self._update_span_formats_only()
        self._apply_frame_styles()

    def flash_match(self, match_id: int):
        """
        Briefly highlight `match_id` at full intensity as a navigation
        attention cue.  After 450 ms the flash fades and the span returns
        to whatever state it was in (active, peer, or normal).

        Triggers a full _render_text because this is a one-shot event
        and search overlays must be preserved.
        """
        self._flash_match_id = match_id
        self._render_text()
        self._apply_frame_styles()
        self._flash_timer.start(450)

    def flash(self):
        """Flash all match spans in this paragraph (legacy navigation helper)."""
        if self.paragraph.spans:
            self.flash_match(self.paragraph.spans[0].match_id)

    def _end_flash(self):
        self._flash_match_id = None
        # Rebuild so the document reflects the settled state (active, peer, or normal)
        self._render_text()
        self._apply_frame_styles()

    # --- Peer-hover pulse animation ---

    def _start_pulse(self):
        """
        Bright arrival pulse when a peer span becomes highlighted.

        Step 1 (immediate): set pulse_step=1 → span renders at full colour.
        Step 2 (after 220 ms): _end_pulse → settle to normal peer format.
        """
        self._pulse_step = 1
        self._update_span_formats_only()
        self._pulse_timer.start(220)

    def _end_pulse(self):
        """Settle peer highlight from bright-pulse to normal peer format."""
        self._pulse_step = 0
        self._update_span_formats_only()

    def sizeHint(self) -> QSize:
        return QSize(self.width(), self.text_edit.height() + Spacing.MD)
