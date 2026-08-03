# Implementation Tasks

## Phase 1: Redesign (Complete)
- [x] Create `gui/report/report_header.py` — New header card widget
- [x] Create `gui/report/match_sidebar.py` — New sidebar match list widget
- [x] Modify `gui/report/paragraph_widget.py` — Hover signal, peer-highlight state, flash animation
- [x] Modify `gui/report/document_viewer.py` — Forward hover signals, peer_highlight method, flash on scroll
- [x] Modify `gui/report/report_screen.py` — New fixed-top layout, workspace splitter, sidebar with AI/Recs
- [x] Modify `gui/report/__init__.py` — Export new public classes
- [x] Prevent splitter panel collapse (set minimum widths + setCollapsible=False)
- [x] Make delayed flash animation safe (parent QTimer to widget)

## Phase 2: PDF Export (Complete)
- [x] Add `"PDF"` option to `export_fmt_combo` in `gui/settings.py` so users can choose it as default
- [x] Create modular `backend/reporting/pdf_exporter.py` with print HTML stylesheet and post-processing page numbering
- [x] Route `"pdf"` format inside `export_report` in `backend/reporting/exporter.py`
- [x] Update "Generate Report" dialog in `gui/results.py` to default to PDF and suggest correct naming format
- [x] Update export button dialog in `gui/report/report_screen.py` to match the results dialog and support PDF
