"""
gui/dashboard.py

One-to-Many Results Dashboard.

A triage screen for reviewing a whole batch of cross-checks at a glance.
The layout is deliberately calm and focused:

    ┌─────────────────────────────────────────────────┬──────────────┐
    │  title / new check                              │  SUMMARY     │
    │  search · filter pills · sort                   │  Total   n   │
    │  "Showing X of Y"      ◀ Page 1 of N ▶          │  Avg    24%  │
    │  ┌───────────────────────────────────────────┐  │  High    3   │
    │  │ 01  Alice High        88%  3   Very High │  │  Med     7   │
    │  │ ID 1111111 · alice.docx              [...│  │  Low    22   │
    │  ├───────────────────────────────────────────┤  └──────────────┘
    │  │ 02  ...                                    │
    │  └───────────────────────────────────────────┘
    └─────────────────────────────────────────────────┘

Summary metrics sit in a sticky column on the right; search, risk filters
and sorting sit at the top; every assignment is one compact row (with a
bold student number) in the main area. When there are many assignments
they are split into pages so the list never becomes overwhelming.

Clicking "View Report" first opens a per-assignment summary (the same
layout as the One-to-One results page) and only from there the side-by-side
detailed report, so the teacher gets exactly one new layer of information
at a time.

State (search text, active filter, sort order, current page) lives inside
this persistent widget — it is never rebuilt during navigation, so
returning from a report keeps the teacher exactly where they left off.
"""

import math
import os
import re
import statistics as _stats
from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QLineEdit, QComboBox, QScrollArea, QSizePolicy,
)

from styles.theme import Colors, Fonts, Spacing, Radius, Icons, IconSize, render_icon
from gui.result_utils import (
    risk_bucket, risk_label, risk_color,
    derive_student_identity, confidence_label,
    RISK_HIGH, RISK_MEDIUM, RISK_LOW,
)

_PAGE_SIZE = 10


# ---------------------------------------------------------------------------
# Shared widgets
# ---------------------------------------------------------------------------

class _ElidingLabel(QLabel):
    """A QLabel that ellipsises its text to the widget's current width."""

    def __init__(self, text: str = "", parent=None):
        super().__init__("", parent)
        self._full_text = text or ""
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setText(self._full_text)

    def setText(self, text):
        self._full_text = text if text is not None else ""
        w = self.width()
        if w > 0:
            text = self.fontMetrics().elidedText(self._full_text, Qt.ElideRight, w)
        super().setText(text)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        if w > 0:
            super().setText(self.fontMetrics().elidedText(self._full_text, Qt.ElideRight, w))


class _FilterPill(QPushButton):
    """A checkable filter pill with an explicit checked (accent) style."""

    def __init__(self, text: str, key: str, parent=None):
        super().__init__(text, parent)
        self.key = key
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("PillButton")
        self.set_checked_style(False)

    def set_checked_style(self, checked: bool):
        if checked:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.ACCENT};
                    color: #FFFFFF;
                    border: 1px solid {Colors.ACCENT};
                    border-radius: {Radius.PILL}px;
                    padding: 6px 16px;
                    font-size: 12px;
                    font-weight: 600;
                }}
            """)
        else:
            self.setStyleSheet("")


def _style_sort_combo(combo: QComboBox) -> QComboBox:
    combo.setStyleSheet(f"""
        QComboBox {{
            font-size: {Fonts.SIZE_BODY}px;
            color: {Colors.TEXT_PRIMARY};
            background-color: {Colors.BG_SURFACE_ALT};
            border: 1px solid {Colors.BORDER};
            border-radius: {Radius.SM}px;
            padding: 7px 12px;
            min-width: 180px;
        }}
        QComboBox:hover {{ border-color: {Colors.ACCENT}; }}
        QComboBox::drop-down {{ border: none; width: 28px; }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {Colors.TEXT_MUTED};
            margin-right: 8px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {Colors.BG_SURFACE};
            color: {Colors.TEXT_PRIMARY};
            border: 1px solid {Colors.BORDER};
            border-radius: {Radius.SM}px;
            outline: 0;
            padding: 4px;
            selection-background-color: {Colors.ACCENT};
            selection-color: #FFFFFF;
        }}
    """)
    return combo


def _risk_badge(bucket, error: bool) -> QLabel:
    if error:
        text, color = "FAILED", Colors.BORDER
    else:
        text, color = risk_label(bucket).upper(), risk_color(bucket)
    badge = QLabel(text)
    badge.setAlignment(Qt.AlignCenter)
    badge.setStyleSheet(f"""
        background-color: #20{color[1:]};
        color: {color};
        border: 1px solid #48{color[1:]};
        border-radius: {Radius.PILL}px;
        font-size: {Fonts.SIZE_SMALL - 1}px;
        font-weight: 700;
        letter-spacing: 0.5px;
        padding: 3px 10px;
    """)
    return badge


# ---------------------------------------------------------------------------
# Per-assignment data
# ---------------------------------------------------------------------------

@dataclass
class _AssignmentEntry:
    raw: object
    idx: int                 # 0-based position in the batch (student order)
    score: int
    matches: int
    confidence_label: str
    student_name: str
    student_id: str
    assignment_name: str
    file_name: str
    mtime: float
    error: bool = False
    error_message: str = ""


def _build_entry(pair: dict, idx: int) -> _AssignmentEntry:
    raw = pair.get("raw_result")
    error = bool(pair.get("error"))
    score = int(pair.get("score", 0))
    matches = int(pair.get("similar_paragraphs", 0))

    err_msg = ""
    if error:
        if raw is not None and getattr(raw, "error_message", None):
            err_msg = raw.error_message
        else:
            err_msg = pair.get("summary", "")

    doc_b = getattr(raw, "doc_b", None) if raw is not None else None
    doc_a = getattr(raw, "doc_a", None) if raw is not None else None

    file_name = getattr(doc_b, "file_name", "") if doc_b is not None else ""
    name, sid = derive_student_identity(doc_b if doc_b is not None else doc_a)

    # Failed comparisons give us no student document. Try to recover the
    # offending file name from the error message so the row stays meaningful.
    if error and not file_name:
        m = re.search(r"'([^']+)'", err_msg)
        if m:
            file_name = os.path.basename(m.group(1))
        name = ""

    mtime = 0.0
    try:
        if doc_b is not None and doc_b.source is not None:
            mtime = float(doc_b.source.mtime)
    except Exception:
        mtime = 0.0

    student_name = name or file_name or f"Submission {idx + 1}"

    return _AssignmentEntry(
        raw=raw,
        idx=idx,
        score=score if not error else 0,
        matches=matches,
        confidence_label="N/A" if error else confidence_label(raw),
        student_name=student_name,
        student_id=sid,
        assignment_name=file_name or student_name,
        file_name=file_name,
        mtime=mtime,
        error=error,
        error_message=err_msg,
    )


# ---------------------------------------------------------------------------
# Assignment row
# ---------------------------------------------------------------------------

class ResultRow(QFrame):
    """One assignment rendered as a compact, table-like row.

    The bold student number on the left gives the teacher the batch order at
    a glance; the risk-coloured border + badge do the triage.
    """

    view_requested = Signal(object)

    def __init__(self, entry: _AssignmentEntry, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.setObjectName("ResultRow")
        self.setCursor(Qt.PointingHandCursor)

        bucket = None if entry.error else risk_bucket(entry.score)
        border = risk_color(bucket) if bucket else Colors.BORDER
        self.setStyleSheet(f"""
            #ResultRow {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {border}44;
                border-left: 3px solid {border};
                border-radius: {Radius.LG}px;
            }}
            #ResultRow:hover {{
                border: 1px solid {border}AA;
                border-left: 3px solid {border};
                background-color: {Colors.BG_HOVER};
            }}
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        lay.setSpacing(Spacing.MD)

        # Bold student number
        num_lbl = QLabel(f"{entry.idx + 1:02d}")
        num_lbl.setFixedWidth(44)
        num_lbl.setAlignment(Qt.AlignCenter)
        num_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_H3}px; font-weight: 800; "
            f"color: {border}; background: transparent;"
        )
        lay.addWidget(num_lbl)

        # Identity column
        identity = QVBoxLayout()
        identity.setSpacing(1)

        name_lbl = _ElidingLabel(entry.student_name or "Unnamed submission")
        name_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_BODY_LG}px; font-weight: 700; "
            f"color: {Colors.TEXT_PRIMARY}; background: transparent;"
        )
        identity.addWidget(name_lbl)

        sub_parts = []
        if entry.student_id:
            sub_parts.append(f"ID {entry.student_id}")
        if entry.assignment_name and entry.assignment_name != entry.student_name:
            sub_parts.append(entry.assignment_name)
        sub_lbl = _ElidingLabel(
            "  ·  ".join(sub_parts) or f"Submission — {entry.file_name}"
        )
        sub_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_SMALL}px; color: {Colors.TEXT_MUTED}; "
            f"background: transparent;"
        )
        identity.addWidget(sub_lbl)
        lay.addLayout(identity, 1)

        # Metrics
        metrics = QHBoxLayout()
        metrics.setSpacing(Spacing.LG)
        if entry.error:
            metrics.addLayout(_metric_col("Similarity", "—", Colors.TEXT_MUTED))
            metrics.addLayout(_metric_col("Paragraphs", "—", Colors.TEXT_MUTED))
            metrics.addLayout(_metric_col("Confidence", "—", Colors.TEXT_MUTED))
        else:
            metrics.addLayout(
                _metric_col("Similarity", f"{entry.score}%", risk_color(bucket))
            )
            metrics.addLayout(
                _metric_col("Paragraphs", str(entry.matches), Colors.TEXT_PRIMARY)
            )
            metrics.addLayout(
                _metric_col("Confidence", entry.confidence_label, Colors.ACCENT_HOVER)
            )
        lay.addLayout(metrics)

        lay.addWidget(_risk_badge(bucket, entry.error), alignment=Qt.AlignVCenter)

        view_btn = QPushButton("Unavailable" if entry.error else "View Report")
        view_btn.setObjectName("PrimaryButton")
        view_btn.setCursor(Qt.PointingHandCursor)
        view_btn.setEnabled(not entry.error)
        view_btn.setMinimumWidth(120)
        view_btn.setStyleSheet(
            f"QPushButton {{ padding: 8px 18px; font-size: {Fonts.SIZE_BODY}px; }}"
        )
        view_btn.clicked.connect(lambda: self.view_requested.emit(entry.raw))
        lay.addWidget(view_btn)

        if entry.error and entry.error_message:
            err = QLabel(entry.error_message)
            err.setWordWrap(True)
            err.setStyleSheet(
                f"font-size: {Fonts.SIZE_SMALL}px; color: {Colors.DANGER}; "
                f"background: transparent;"
            )
            lay.addWidget(err)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and not self.entry.error:
            self.view_requested.emit(self.entry.raw)
        super().mouseDoubleClickEvent(event)


def _metric_col(label: str, value: str, color: str) -> QVBoxLayout:
    col = QVBoxLayout()
    col.setSpacing(0)
    val = QLabel(value)
    val.setStyleSheet(
        f"font-size: {Fonts.SIZE_H3}px; font-weight: 700; "
        f"color: {color}; background: transparent;"
    )
    col.addWidget(val)
    cap = QLabel(label)
    cap.setStyleSheet(
        f"font-size: {Fonts.SIZE_SMALL}px; color: {Colors.TEXT_MUTED}; "
        f"background: transparent;"
    )
    col.addWidget(cap)
    return col


# ---------------------------------------------------------------------------
# Summary sidebar (right column)
# ---------------------------------------------------------------------------

class _SummarySidebar(QFrame):
    """Sticky right-hand column holding the batch's summary metrics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SummarySidebar")
        self.setFixedWidth(240)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setStyleSheet(f"""
            #SummarySidebar {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: {Radius.LG}px;
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        root.setSpacing(Spacing.SM)
        root.setAlignment(Qt.AlignTop)

        cap = QLabel("SUMMARY")
        cap.setObjectName("SectionLabel")
        root.addWidget(cap)

        self._stats: dict[str, _StatItem] = {}
        self._add_item("total", Icons.USERS, "Assignments Compared", Colors.TEXT_PRIMARY)
        self._add_item("avg", Icons.LAYERS, "Average Similarity", Colors.ACCENT)
        self._add_item("high", Icons.TRIANGLE_ALERT, "High Risk", Colors.DANGER)
        self._add_item("medium", Icons.INFO, "Medium Risk", Colors.WARNING)
        self._add_item("low", Icons.CHECK, "Low Risk", Colors.SUCCESS)

        root.addStretch()

    def _add_item(self, key: str, icon_svg: str, label: str, color: str):
        item = _StatItem(icon_svg, label, color)
        self._stats[key] = item
        self.layout().insertWidget(1 + len(self._stats) - 1, item)

    def set_values(self, total: int, avg: int, high: int, medium: int, low: int):
        self._stats["total"].set_value(str(total))
        self._stats["avg"].set_value(f"{avg}%")
        self._stats["high"].set_value(str(high))
        self._stats["medium"].set_value(str(medium))
        self._stats["low"].set_value(str(low))


class _StatItem(QFrame):
    """One compact metric line inside the summary sidebar."""

    def __init__(self, icon_svg: str, label: str, color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("StatItem")
        self.setStyleSheet(f"""
            #StatItem {{
                background-color: {Colors.BG_SURFACE_ALT};
                border-radius: {Radius.MD}px;
            }}
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        lay.setSpacing(Spacing.MD)

        icon = QLabel()
        icon.setPixmap(render_icon(icon_svg, color, IconSize.MD))
        lay.addWidget(icon, alignment=Qt.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        self.value_label = QLabel("—")
        self.value_label.setStyleSheet(
            f"font-size: {Fonts.SIZE_H2}px; font-weight: 700; "
            f"color: {color}; background: transparent;"
        )
        text_col.addWidget(self.value_label)

        cap = QLabel(label)
        cap.setStyleSheet(
            f"font-size: {Fonts.SIZE_SMALL}px; color: {Colors.TEXT_MUTED}; "
            f"background: transparent;"
        )
        text_col.addWidget(cap)

        lay.addLayout(text_col)
        lay.addStretch()

    def set_value(self, text: str):
        self.value_label.setText(text)


# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------

class _EmptyState(QFrame):
    reset_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setStyleSheet(f"""
            #Card {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: {Radius.LG}px;
            }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(Spacing.XXL, Spacing.XL, Spacing.XXL, Spacing.XL)
        lay.setSpacing(Spacing.MD)
        lay.setAlignment(Qt.AlignCenter)

        icon = QLabel()
        icon.setPixmap(render_icon(Icons.SEARCH, Colors.TEXT_MUTED, IconSize.XL))
        lay.addWidget(icon, alignment=Qt.AlignCenter)

        title = QLabel("No assignments match your current search or filter.")
        title.setAlignment(Qt.AlignCenter)
        title.setWordWrap(True)
        title.setStyleSheet(
            f"font-size: {Fonts.SIZE_BODY_LG}px; font-weight: 600; "
            f"color: {Colors.TEXT_PRIMARY}; background: transparent;"
        )
        lay.addWidget(title)

        hint = QLabel("Try a broader search or clear the current filters to see every result.")
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)
        hint.setStyleSheet(
            f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_MUTED}; "
            f"background: transparent;"
        )
        lay.addWidget(hint)

        reset_btn = QPushButton("Reset Filters")
        reset_btn.setObjectName("PrimaryButton")
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.setMinimumWidth(140)
        reset_btn.clicked.connect(self.reset_clicked.emit)
        lay.addWidget(reset_btn, alignment=Qt.AlignCenter)


# ---------------------------------------------------------------------------
# Main screen
# ---------------------------------------------------------------------------

class OneToManyDashboardScreen(QWidget):

    new_check_requested = Signal()
    restart_requested = Signal()
    report_requested = Signal(object)   # ComparisonResult (raw) → per-assignment summary

    SORT_OPTIONS = [
        ("Highest Similarity",    "sim_desc"),
        ("Lowest Similarity",     "sim_asc"),
        ("Alphabetical (Student)", "name_asc"),
        ("Alphabetical (Assignment)", "assignment_asc"),
        ("Newest Upload",         "mtime_desc"),
        ("Oldest Upload",         "mtime_asc"),
    ]

    _SORTERS = {
        "sim_desc":      lambda e: (-e.score, e.student_name.lower()),
        "sim_asc":       lambda e: (e.score, e.student_name.lower()),
        "name_asc":      lambda e: (e.student_name.lower(), -e.score),
        "assignment_asc": lambda e: (e.assignment_name.lower(), -e.score),
        "mtime_desc":    lambda e: (-e.mtime, e.file_name.lower()),
        "mtime_asc":     lambda e: (e.mtime, e.file_name.lower()),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: list[_AssignmentEntry] = []
        self._visible: list[_AssignmentEntry] = []
        self._search_text = ""
        self._filter = "all"
        self._sort_key = "sim_desc"
        self._page = 1
        self._page_size = _PAGE_SIZE

        outer = QVBoxLayout(self)
        outer.setContentsMargins(Spacing.XXXL, Spacing.XXL, Spacing.XXXL, Spacing.XL)
        outer.setSpacing(Spacing.MD)

        # Top bar: title + New Check
        top = QHBoxLayout()
        top.setSpacing(Spacing.MD)
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("One-to-Many Results")
        title.setStyleSheet(
            f"font-size: {Fonts.SIZE_H2}px; font-weight: 600; "
            f"color: {Colors.TEXT_PRIMARY};"
        )
        title_col.addWidget(title)
        subtitle = QLabel("Review every compared assignment at a glance")
        subtitle.setStyleSheet(
            f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_MUTED};"
        )
        title_col.addWidget(subtitle)
        top.addLayout(title_col)
        top.addStretch()

        new_btn = QPushButton("New Check")
        new_btn.setObjectName("SecondaryButton")
        new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.clicked.connect(self.new_check_requested.emit)
        top.addWidget(new_btn)
        outer.addLayout(top)

        # Controls: search + filter pills + sort (full width, at the top)
        controls = QHBoxLayout()
        controls.setSpacing(Spacing.MD)

        search_wrap = QFrame()
        search_wrap.setMinimumWidth(280)
        search_wrap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        search_wrap.setStyleSheet(
            f"background-color: {Colors.BG_SURFACE_ALT}; "
            f"border: 1px solid {Colors.BORDER}; "
            f"border-radius: {Radius.SM}px;"
        )
        sw = QHBoxLayout(search_wrap)
        sw.setContentsMargins(Spacing.SM + 2, 4, Spacing.SM, 4)
        sw.setSpacing(Spacing.SM)
        s_icon = QLabel()
        s_icon.setPixmap(render_icon(Icons.SEARCH, Colors.TEXT_MUTED, IconSize.SM))
        sw.addWidget(s_icon)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search by student name, ID, or assignment..."
        )
        self.search_input.setStyleSheet(
            f"QLineEdit {{ background: transparent; border: none; "
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_BODY}px; }}"
        )
        self.search_input.textChanged.connect(self._on_search_changed)
        sw.addWidget(self.search_input, 1)
        controls.addWidget(search_wrap, 1)

        self._pills: dict[str, _FilterPill] = {}
        for key, label in [("all", "All"), ("high", "High Risk"),
                           ("medium", "Medium Risk"), ("low", "Low Risk")]:
            pill = _FilterPill(label, key)
            pill.clicked.connect(lambda _=False, k=key: self._set_filter(k))
            self._pills[key] = pill
            controls.addWidget(pill)

        controls.addSpacing(Spacing.MD)

        self.sort_combo = QComboBox()
        _style_sort_combo(self.sort_combo)
        for label, _ in self.SORT_OPTIONS:
            self.sort_combo.addItem(label)
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        controls.addWidget(self.sort_combo)

        outer.addLayout(controls)

        # Main split: assignment list (left) | summary (right)
        split = QHBoxLayout()
        split.setSpacing(Spacing.XL)

        side_panel = QVBoxLayout()
        side_panel.setSpacing(Spacing.MD)

        # Results header: count + pagination
        header_row = QHBoxLayout()
        header_row.setSpacing(Spacing.MD)
        self._count_label = QLabel("")
        self._count_label.setStyleSheet(
            f"font-size: {Fonts.SIZE_SMALL}px; color: {Colors.TEXT_MUTED};"
        )
        header_row.addWidget(self._count_label)
        header_row.addStretch()

        self._prev_btn = QPushButton("◀ Prev")
        self._prev_btn.setObjectName("GhostButton")
        self._prev_btn.setCursor(Qt.PointingHandCursor)
        self._prev_btn.clicked.connect(self._prev_page)
        header_row.addWidget(self._prev_btn)

        self._page_label = QLabel("Page 1 of 1")
        self._page_label.setAlignment(Qt.AlignCenter)
        self._page_label.setMinimumWidth(76)
        self._page_label.setStyleSheet(
            f"font-size: {Fonts.SIZE_SMALL}px; font-weight: 600; "
            f"color: {Colors.TEXT_SECONDARY};"
        )
        header_row.addWidget(self._page_label)

        self._next_btn = QPushButton("Next ▶")
        self._next_btn.setObjectName("GhostButton")
        self._next_btn.setCursor(Qt.PointingHandCursor)
        self._next_btn.clicked.connect(self._next_page)
        header_row.addWidget(self._next_btn)

        side_panel.addLayout(header_row)

        # Scrollable row list + empty state
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        list_content = QWidget()
        list_content.setStyleSheet("background: transparent;")
        lc = QVBoxLayout(list_content)
        lc.setContentsMargins(0, 0, 0, 0)
        lc.setSpacing(Spacing.SM)

        self._rows_host = QWidget()
        self._rows_host.setStyleSheet("background: transparent;")
        self._rows_layout = QVBoxLayout(self._rows_host)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(Spacing.SM)
        self._rows_layout.setAlignment(Qt.AlignTop)
        lc.addWidget(self._rows_host)

        self._empty = _EmptyState()
        self._empty.reset_clicked.connect(self.reset_filters)
        self._empty.setVisible(False)
        lc.addWidget(self._empty)

        lc.addStretch()
        self._scroll.setWidget(list_content)

        side_panel.addWidget(self._scroll, 1)
        split.addLayout(side_panel, 1)

        # Right-hand summary column
        self.summary_sidebar = _SummarySidebar()
        split.addWidget(self.summary_sidebar)

        outer.addLayout(split, 1)

        self.reset_filters()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def display_results(self, result: dict):
        pairs = result.get("pairs", [])
        self._entries = [_build_entry(p, i) for i, p in enumerate(pairs)]
        self._update_summary()
        # Baseline state for a fresh batch.
        self.reset_filters()

    def reset_filters(self):
        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)
        self._search_text = ""
        self._set_filter("all")
        self.sort_combo.blockSignals(True)
        self.sort_combo.setCurrentIndex(0)
        self.sort_combo.blockSignals(False)
        self._sort_key = self.SORT_OPTIONS[0][1]
        self._page = 1
        self._apply_filters()

    # ------------------------------------------------------------------
    # Summary sidebar
    # ------------------------------------------------------------------

    def _update_summary(self):
        valid = [e for e in self._entries if not e.error]
        high = sum(1 for e in valid if risk_bucket(e.score) == RISK_HIGH)
        medium = sum(1 for e in valid if risk_bucket(e.score) == RISK_MEDIUM)
        low = sum(1 for e in valid if risk_bucket(e.score) == RISK_LOW)
        avg = int(_stats.mean((e.score for e in valid))) if valid else 0
        self.summary_sidebar.set_values(len(self._entries), avg, high, medium, low)

    # ------------------------------------------------------------------
    # Search / filter / sort
    # ------------------------------------------------------------------

    def _on_search_changed(self, text: str):
        self._search_text = text
        self._apply_filters()

    def _set_filter(self, key: str):
        self._filter = key
        for k, pill in self._pills.items():
            pill.setChecked(k == key)
            pill.set_checked_style(k == key)
        self._apply_filters()

    def _on_sort_changed(self, index: int):
        if 0 <= index < len(self.SORT_OPTIONS):
            self._sort_key = self.SORT_OPTIONS[index][1]
            self._apply_filters()

    def _apply_filters(self):
        needle = self._search_text.strip().lower()
        filtered = []

        for e in self._entries:
            if self._filter != "all":
                if e.error or risk_bucket(e.score) != self._filter:
                    continue
            if needle:
                hay = (
                    f"{e.student_name} {e.student_id} "
                    f"{e.assignment_name} {e.file_name}"
                ).lower()
                if needle not in hay:
                    continue
            filtered.append(e)

        sorter = self._SORTERS.get(self._sort_key, self._SORTERS["sim_desc"])
        filtered.sort(key=lambda e: (e.error, sorter(e)))

        self._visible = filtered
        self._page = 1
        self._render_page()

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    def _total_pages(self) -> int:
        return max(1, math.ceil(len(self._visible) / self._page_size))

    def _render_page(self):
        total = len(self._visible)
        total_pages = self._total_pages()
        self._page = max(1, min(self._page, total_pages))

        start = (self._page - 1) * self._page_size
        page_entries = self._visible[start:start + self._page_size]

        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        for entry in page_entries:
            row = ResultRow(entry)
            row.view_requested.connect(self._on_card_view_requested)
            self._rows_layout.addWidget(row)

        self._prev_btn.setEnabled(self._page > 1)
        self._next_btn.setEnabled(self._page < total_pages)
        self._page_label.setText(f"Page {self._page} of {total_pages}")
        self._count_label.setText(
            f"Showing {len(page_entries)} of {total} assignments"
        )
        self._empty.setVisible(total == 0)

    def _prev_page(self):
        if self._page > 1:
            self._page -= 1
            self._render_page()

    def _next_page(self):
        if self._page < self._total_pages():
            self._page += 1
            self._render_page()

    # ------------------------------------------------------------------
    # Report navigation
    # ------------------------------------------------------------------

    def _on_card_view_requested(self, raw):
        if raw is None:
            return
        self.report_requested.emit(raw)