"""
backend/reporting/pdf_exporter.py

Modular PDF Exporter for the Detailed Report page.

Uses QTextDocument with QPdfWriter to render a styled print HTML template,
then post-processes it using PyMuPDF (fitz) to draw running headers, running
footers, page numbers, and thin separation rules on each page.
This ensures page numbers and header titles are formatted and aligned
correctly on A4 pages.
"""

import os
import sys
import uuid
import tempfile
from datetime import datetime
from typing import Optional

from PySide6.QtGui import QGuiApplication, QTextDocument, QPdfWriter, QPageSize, QPageLayout
from PySide6.QtCore import QMarginsF

from backend.reporting.model import ReportModel, ReportParagraph, MatchType


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


_MATCH_BG_COLORS = {
    MatchType.EXACT: "#dcfce7",    # light green
    MatchType.PARTIAL: "#fef3c7",  # light yellow
    MatchType.SEMANTIC: "#e0e7ff", # light indigo
}

_MATCH_BORDER_COLORS = {
    MatchType.EXACT: "#22c55e",
    MatchType.PARTIAL: "#f59e0b",
    MatchType.SEMANTIC: "#6366f1",
}


def _build_paragraph_html(paragraph: ReportParagraph) -> str:
    """Builds inline span highlights for the PDF comparison table."""
    text = paragraph.text
    if not paragraph.spans:
        return _escape_html(text).replace("\n", "<br>")

    segments = []
    sorted_spans = sorted(paragraph.spans, key=lambda s: s.char_start)
    pos = 0
    for span in sorted_spans:
        if span.char_start > pos:
            segments.append(_escape_html(text[pos:span.char_start]))

        raw_span = text[span.char_start:span.char_end]
        escaped_span = _escape_html(raw_span)
        bg = _MATCH_BG_COLORS.get(span.match_type, "#f1f5f9")
        border = _MATCH_BORDER_COLORS.get(span.match_type, "#cbd5e1")
        # Bold and underline the matched parts so it is clear even in grayscale printing
        segments.append(
            f'<span style="background-color: {bg}; border-bottom: 2px solid {border}; font-weight: bold;">'
            f'{escaped_span}</span>'
        )
        pos = span.char_end

    if pos < len(text):
        segments.append(_escape_html(text[pos:]))

    return "".join(segments).replace("\n", "<br>")


def _ai_summary(model: ReportModel) -> str:
    s = model.statistics
    if s.similarity_percent >= 70:
        summary = (
            f"The assignments share a highly significant amount of semantic meaning "
            f"({s.similarity_percent}% similarity). {s.total_matches} highly similar "
            f"paragraphs were found, indicating potential copying or heavy collaboration."
        )
    elif s.similarity_percent >= 40:
        summary = (
            f"There is moderate overlap in the concepts discussed ({s.similarity_percent}% "
            f"similarity). {s.total_matches} paragraphs show structural or semantic similarities."
        )
    else:
        summary = (
            f"The assignments appear to be largely independent ({s.similarity_percent}% "
            f"similarity). {s.total_matches} brief section(s) showed minor similarities."
        )
    if s.ocr_used:
        summary += " OCR was used for scanned content during extraction."
    return summary


def _build_pdf_html(model: ReportModel, report_id: str, timestamp: str) -> str:
    s = model.statistics
    score = s.similarity_percent

    if score < 40:
        risk_label, risk_color = "LOW RISK", "#16a34a"  # green
    elif score < 70:
        risk_label, risk_color = "MEDIUM RISK", "#d97706"  # amber
    else:
        risk_label, risk_color = "HIGH RISK", "#dc2626"  # red

    # Build matches rows
    match_rows = []
    match_details = []

    match_labels = {
        MatchType.EXACT: "Exact",
        MatchType.PARTIAL: "Partial",
        MatchType.SEMANTIC: "Semantic",
        MatchType.UNIQUE: "Unique",
    }

    for idx, m in enumerate(model.matches):
        color = _MATCH_BORDER_COLORS.get(m.type, "#475569")
        match_rows.append(
            f'<tr>'
            f'  <td style="border: 1px solid #cbd5e1; padding: 6px; text-align: center;">#{m.match_id}</td>'
            f'  <td style="border: 1px solid #cbd5e1; padding: 6px; color: {color}; font-weight: bold;">{match_labels.get(m.type, m.type.value)}</td>'
            f'  <td style="border: 1px solid #cbd5e1; padding: 6px; text-align: center;">{m.left_paragraph_id}</td>'
            f'  <td style="border: 1px solid #cbd5e1; padding: 6px; text-align: center;">{m.right_paragraph_id}</td>'
            f'  <td style="border: 1px solid #cbd5e1; padding: 6px; text-align: right; font-weight: bold;">{min(100, round(m.score * 100))}%</td>'
            f'</tr>'
        )

        left_para = model.get_paragraph_by_id(m.left_paragraph_id)
        right_para = model.get_paragraph_by_id(m.right_paragraph_id)

        if left_para and right_para:
            match_details.append(
                f'<div style="page-break-inside: avoid; margin-bottom: 20px;">'
                f'  <div style="font-size: 11pt; font-weight: bold; color: {color}; margin-bottom: 6px;">'
                f'    Match #{m.match_id} &middot; {match_labels.get(m.type, m.type.value)} &middot; {min(100, round(m.score * 100))}% Similarity'
                f'  </div>'
                f'  <table style="width: 100%; border-collapse: collapse; table-layout: fixed;">'
                f'    <tr>'
                f'      <td style="width: 50%; border: 1px solid #cbd5e1; background-color: #f8fafc; padding: 4px 8px; font-size: 9pt; font-weight: bold; color: #475569;">'
                f'        Document A (Left) &mdash; {m.left_paragraph_id} (Sentences: {left_para.sentence_count}, Words: {left_para.word_count})'
                f'      </td>'
                f'      <td style="width: 50%; border: 1px solid #cbd5e1; background-color: #f8fafc; padding: 4px 8px; font-size: 9pt; font-weight: bold; color: #475569;">'
                f'        Document B (Right) &mdash; {m.right_paragraph_id} (Sentences: {right_para.sentence_count}, Words: {right_para.word_count})'
                f'      </td>'
                f'    </tr>'
                f'    <tr>'
                f'      <td style="width: 50%; border: 1px solid #cbd5e1; padding: 8px; font-size: 9pt; vertical-align: top;">'
                f'        {_build_paragraph_html(left_para)}'
                f'      </td>'
                f'      <td style="width: 50%; border: 1px solid #cbd5e1; padding: 8px; font-size: 9pt; vertical-align: top;">'
                f'        {_build_paragraph_html(right_para)}'
                f'      </td>'
                f'    </tr>'
                f'  </table>'
                f'</div>'
            )

    recommendation_text = (
        f"Similarity is critically elevated ({score}%). Immediate manual review of all "
        f"{s.total_matches} matched paragraphs is strongly recommended. Consider flagging this "
        f"submission for academic integrity review."
        if score >= 70 else
        f"Similarity level is elevated ({score}%). Manual review of the "
        f"{s.total_matches} matched paragraphs is recommended."
    )

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
    body {{
        font-family: Arial, sans-serif;
        color: #0f172a;
        font-size: 10pt;
        line-height: 1.45;
    }}
    .title {{
        font-size: 18pt;
        font-weight: bold;
        color: #4f46e5;
        margin-bottom: 2px;
    }}
    .meta-table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 15px;
        margin-bottom: 20px;
    }}
    .meta-cell {{
        padding: 8px;
        border: 1px solid #e2e8f0;
        vertical-align: middle;
    }}
    .meta-label {{
        font-weight: bold;
        background-color: #f8fafc;
        color: #475569;
    }}
    .section-title {{
        font-size: 13pt;
        font-weight: bold;
        color: #1e293b;
        border-bottom: 2px solid #cbd5e1;
        padding-bottom: 4px;
        margin-top: 25px;
        margin-bottom: 12px;
        page-break-after: avoid;
    }}
    .callout {{
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 15px;
        page-break-inside: avoid;
    }}
    .ai-summary {{
        background-color: #f0f4ff;
        border-left: 4px solid #6366f1;
    }}
    .recommendations {{
        background-color: #fffbeb;
        border-left: 4px solid #f59e0b;
        color: #b45309;
    }}
    .stats-table {{
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 15px;
    }}
    .stats-table th {{
        background-color: #f1f5f9;
        border: 1px solid #cbd5e1;
        padding: 8px;
        font-weight: bold;
        text-align: left;
    }}
    .stats-table td {{
        border: 1px solid #cbd5e1;
        padding: 8px;
    }}
    </style>
    </head>
    <body>
      <div class="title">Smart Assignment Similarity Report</div>
      <div style="font-size: 9pt; color: #64748b;">Detailed document similarity analysis.</div>
      
      <table class="meta-table">
        <tr>
          <td class="meta-cell meta-label" style="width: 20%;">Document A:</td>
          <td class="meta-cell" style="width: 50%;">{_escape_html(model.left_document.title)}</td>
          <td class="meta-cell meta-label" style="width: 15%;">Score:</td>
          <td class="meta-cell" style="width: 15%; font-size: 12pt; font-weight: bold; color: {risk_color};">{score}%</td>
        </tr>
        <tr>
          <td class="meta-cell meta-label">Document B:</td>
          <td class="meta-cell">{_escape_html(model.right_document.title)}</td>
          <td class="meta-cell meta-label">Risk Level:</td>
          <td class="meta-cell" style="font-weight: bold; color: {risk_color};">{risk_label}</td>
        </tr>
        <tr>
          <td class="meta-cell meta-label">Report ID:</td>
          <td class="meta-cell">{report_id}</td>
          <td class="meta-cell meta-label">Generated:</td>
          <td class="meta-cell" style="font-size: 8pt; color: #475569;">{timestamp}</td>
        </tr>
      </table>

      <div class="section-title">Executive Summary</div>
      <div class="callout ai-summary">
        <div style="font-weight: bold; color: #312e81; margin-bottom: 4px;">AI Summary</div>
        {_escape_html(_ai_summary(model))}
      </div>

      <div class="callout recommendations">
        <div style="font-weight: bold; color: #78350f; margin-bottom: 4px;">Recommendations</div>
        {_escape_html(recommendation_text)}
      </div>

      <div class="section-title">Statistics</div>
      <table class="stats-table">
        <tr>
          <th>Metric</th>
          <th style="text-align: right; width: 25%;">Value</th>
        </tr>
        <tr>
          <td>Total Highlighted Matches</td>
          <td style="text-align: right; font-weight: bold;">{s.total_matches}</td>
        </tr>
        <tr>
          <td>Exact Matching Sections</td>
          <td style="text-align: right; color: #16a34a;">{s.exact_matches}</td>
        </tr>
        <tr>
          <td>Partial Matching Sections</td>
          <td style="text-align: right; color: #d97706;">{s.partial_matches}</td>
        </tr>
        <tr>
          <td>Semantic Matching Sections</td>
          <td style="text-align: right; color: #4f46e5;">{s.semantic_matches}</td>
        </tr>
        <tr>
          <td>Unique (Independent) Paragraphs</td>
          <td style="text-align: right; color: #64748b;">{s.unique_paragraphs}</td>
        </tr>
        {"".join([
            f"<tr><td>OCR Mean Extraction Confidence</td><td style='text-align: right;'>"
            f"{s.avg_ocr_confidence:.0%}</td></tr>"
        ] if s.ocr_used and s.avg_ocr_confidence > 0 else [])}
      </table>

      <div class="section-title">Match Index</div>
      <table style="width: 100%; border-collapse: collapse; margin-bottom: 25px; page-break-after: avoid;">
        <thead>
          <tr style="background-color: #f1f5f9;">
            <th style="border: 1px solid #cbd5e1; padding: 6px; font-weight: bold; width: 15%; text-align: center;">Match ID</th>
            <th style="border: 1px solid #cbd5e1; padding: 6px; font-weight: bold; width: 20%; text-align: left;">Type</th>
            <th style="border: 1px solid #cbd5e1; padding: 6px; font-weight: bold; width: 25%; text-align: center;">Doc A Para</th>
            <th style="border: 1px solid #cbd5e1; padding: 6px; font-weight: bold; width: 25%; text-align: center;">Doc B Para</th>
            <th style="border: 1px solid #cbd5e1; padding: 6px; font-weight: bold; width: 15%; text-align: right;">Overlap %</th>
          </tr>
        </thead>
        <tbody>
          {"".join(match_rows) if match_rows else '<tr><td colspan="5" style="border: 1px solid #cbd5e1; padding: 10px; text-align: center; color: #64748b;">No matches found.</td></tr>'}
        </tbody>
      </table>

      {"<div style='page-break-before: always;'></div>" if match_details else ""}
      
      {"".join(match_details)}
    </body>
    </html>
    """
    return html


def _decorate_pdf(temp_pdf_path: str, final_pdf_path: str, model: ReportModel, report_id: str, timestamp: str):
    """
    Post-processes the generated PDF using PyMuPDF to draw clean running
    headers, running footers, page numbers, and separators on every page.
    """
    import fitz

    doc = fitz.open(temp_pdf_path)
    page_count = len(doc)

    for i, page in enumerate(doc):
        rect = page.rect
        w, h = rect.width, rect.height

        # --- Running Header ---
        # Draw running header text (left-aligned) and Report ID (right-aligned)
        page.insert_text(
            (42, 36),
            "Smart Assignment Cross-Checking Report",
            fontsize=8,
            color=(0.38, 0.43, 0.51),
        )
        page.insert_text(
            (w - 42 - 130, 36),
            f"Report ID: {report_id}  |  v1.0",
            fontsize=8,
            color=(0.38, 0.43, 0.51),
        )
        # Thin horizontal separator rule under header
        page.draw_line(
            (42, 44),
            (w - 42, 44),
            color=(0.85, 0.88, 0.92),
            width=0.5,
        )

        # --- Running Footer ---
        # Thin horizontal separator rule above footer
        page.draw_line(
            (42, h - 44),
            (w - 42, h - 44),
            color=(0.85, 0.88, 0.92),
            width=0.5,
        )
        # Draw running footer text (left-aligned) and page numbers (right-aligned)
        page.insert_text(
            (42, h - 32),
            f"Generated: {timestamp} · Smart Assignment Checker",
            fontsize=8,
            color=(0.38, 0.43, 0.51),
        )
        page_str = f"Page {i+1} of {page_count}"
        page.insert_text(
            (w - 42 - 50, h - 32),
            page_str,
            fontsize=8,
            color=(0.38, 0.43, 0.51),
        )

    doc.save(final_pdf_path)
    doc.close()


def export_pdf(model: ReportModel, file_path: str, options: Optional[dict] = None) -> str:
    """
    Exports a ReportModel as a professional, publication-quality A4 PDF.
    
    1. Generates styled print HTML.
    2. Uses PySide6's QTextDocument & QPdfWriter to write a temporary PDF.
    3. Uses PyMuPDF (fitz) to overlay running headers, footers, rules, and page numbers.
    """
    report_id = uuid.uuid4().hex[:8].upper()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = _build_pdf_html(model, report_id, timestamp)

    # Initialize a temporary QGuiApplication if one is not running (e.g. CLI or test runs)
    qt_app = QGuiApplication.instance()
    if not qt_app:
        qt_app = QGuiApplication(sys.argv)

    # Write QTextDocument printing flow to a temporary file path
    temp_fd, temp_path = tempfile.mkstemp(suffix=".pdf")
    os.close(temp_fd)

    try:
        writer = QPdfWriter(temp_path)
        writer.setPageSize(QPageSize.A4)
        
        # 15mm left/right, 22mm top/bottom margins.
        # This keeps QTextDocument body elements strictly inside Y=[62, h-62] points,
        # preventing overlap with the header (Y=36) and footer (Y=h-32).
        writer.setPageMargins(QMarginsF(15, 22, 15, 22), QPageLayout.Millimeter)

        doc = QTextDocument()
        doc.setHtml(html)
        doc.print_(writer)

        # Post-process the PDF with headers, footers, and page numbers
        _decorate_pdf(temp_path, file_path, model, report_id, timestamp)
    finally:
        # Clean up temporary file
        try:
            os.remove(temp_path)
        except OSError:
            pass

    return file_path
