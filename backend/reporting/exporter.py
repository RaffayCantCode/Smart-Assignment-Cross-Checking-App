import os
from datetime import datetime
from typing import Optional, Tuple

from .model import ReportModel, MatchType

_FORMAT_FILTERS = {
    "pdf": "PDF Files (*.pdf)",
    "html": "HTML Files (*.html)",
    "txt": "Text Files (*.txt)",
}


def sanitize_assignment_name(title: str) -> str:
    assignment_name = title or "Assignment"
    if "." in assignment_name:
        assignment_name = assignment_name.rsplit(".", 1)[0]
    for c in '<>:"/\\|?*':
        assignment_name = assignment_name.replace(c, "_")
    return assignment_name


def normalize_export_format(fmt: str) -> str:
    fmt = fmt.lower().lstrip(".")
    if fmt == "text":
        fmt = "txt"
    return fmt if fmt in _FORMAT_FILTERS else "html"


def build_report_filename(assignment_name: str, fmt: str = "html") -> str:
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M")
    ext = normalize_export_format(fmt)
    safe_name = sanitize_assignment_name(assignment_name)
    return f"Similarity_Report_{safe_name}_{date_str}_{time_str}.{ext}"


def build_save_file_filter(default_fmt: str = "html") -> str:
    default = normalize_export_format(default_fmt)
    order = ["pdf", "html", "txt"]
    order.remove(default)
    order.insert(0, default)
    return ";;".join(_FORMAT_FILTERS[f] for f in order)


def resolve_export_extension(
    file_path: str,
    selected_filter: str,
    fallback_fmt: str = "html",
) -> Tuple[str, str]:
    ext = os.path.splitext(file_path)[1].lower().lstrip(".")
    if ext in ("pdf", "html", "txt", "text"):
        return file_path, normalize_export_format(ext)

    fallback = normalize_export_format(fallback_fmt)
    filter_lower = selected_filter.lower()
    if "pdf" in filter_lower:
        ext = "pdf"
    elif "html" in filter_lower:
        ext = "html"
    elif "txt" in filter_lower or "text" in filter_lower:
        ext = "txt"
    else:
        ext = fallback
    return f"{file_path}.{ext}", ext


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )


def _ai_summary(model: ReportModel) -> str:
    """Generates a natural-language summary from report statistics."""
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


def _build_html(model: ReportModel, options: Optional[dict] = None) -> str:
    options = options or {}
    inc_sim = options.get("include_similarity", True)
    inc_high = options.get("include_highlights", True)
    inc_stats = options.get("include_statistics", True)
    inc_rec = options.get("include_recommendations", True)
    inc_ai = options.get("include_ai_summary", True)

    match_labels = {
        MatchType.EXACT: "Exact Match",
        MatchType.PARTIAL: "Partial Match",
        MatchType.SEMANTIC: "Semantic Match",
        MatchType.UNIQUE: "Unique",
        MatchType.NONE: "",
    }

    paragraphs_html = []
    for side, doc in [("A", model.left_document), ("B", model.right_document)]:
        paragraphs_html.append(f'<h2>Document: {_escape_html(doc.title)}</h2>')
        for p in doc.paragraphs:
            label = match_labels.get(p.primary_match_type, "")
            match_info = f'<span class="tag {p.primary_match_type.value}">{_escape_html(label)}</span>' if (label and inc_high) else ""
            ref_info = f' → <em>{_escape_html(p.matched_paragraph_id)}</em>' if (p.matched_paragraph_id and inc_high) else ""
            
            p_class = f"paragraph {p.primary_match_type.value}" if inc_high else "paragraph"
            paragraphs_html.append(
                f'<div class="{p_class}">'
                f'<div class="para-id">{_escape_html(p.paragraph_id)}{ref_info} {match_info}</div>'
                f'<p>{_escape_html(p.text)}</p>'
                f'</div>'
            )

    s = model.statistics
    stats_parts = []
    if inc_sim:
        stats_parts.append(f"Similarity: {s.similarity_percent}%")
    if inc_stats:
        stats_parts.extend([
            f"Total Matches: {s.total_matches}",
            f"Exact: {s.exact_matches}",
            f"Partial: {s.partial_matches}",
            f"Semantic: {s.semantic_matches}",
            f"Unique: {s.unique_paragraphs}"
        ])
        if s.ocr_used:
            conf_str = f"{s.avg_ocr_confidence:.0%}" if s.avg_ocr_confidence > 0 else "Yes"
            stats_parts.append(f"OCR Used: {conf_str}")

    stats_html = f'<div class="stats"><p>{" | ".join(stats_parts)}</p></div>' if stats_parts else ""

    ai_html = ""
    if inc_ai:
        ai_html = f'<div class="ai-summary"><h3>Analysis Summary</h3><p>{_escape_html(_ai_summary(model))}</p></div>'

    rec_html = ""
    if inc_rec and s.similarity_percent >= 40:
        rec_html = f'<div class="recommendations"><h3>Analysis Alert</h3><p>Similarity level is elevated ({s.similarity_percent}%). Manual review of matched paragraphs is recommended.</p></div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Smart Assignment Cross-Checking Report</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       max-width: 1000px; margin: 40px auto; padding: 0 20px;
       background: #0f0f13; color: #e4e4e7; }}
h1 {{ font-size: 24px; border-bottom: 1px solid #27272a; padding-bottom: 12px; }}
h2 {{ font-size: 18px; color: #a1a1aa; }}
.paragraph {{ padding: 8px 12px; margin: 4px 0; border-left: 3px solid transparent;
             border-radius: 4px; background: #111115; }}
.paragraph.exact {{ border-left-color: #22c55e; background: #16653415; }}
.paragraph.partial {{ border-left-color: #f59e0b; background: #ca8a0415; }}
.paragraph.semantic {{ border-left-color: #818cf8; background: #4338ca15; }}
.para-id {{ font-size: 11px; font-weight: 700; color: #52525b; letter-spacing: 0.5px; }}
.tag {{ font-size: 10px; font-weight: 600; padding: 1px 6px; border-radius: 3px; }}
.tag.exact {{ color: #22c55e; }}
.tag.partial {{ color: #f59e0b; }}
.tag.semantic {{ color: #818cf8; }}
p {{ margin: 6px 0 0 0; line-height: 1.6; }}
.stats {{ background: #111115; border: 1px solid #27272a; border-radius: 8px;
          padding: 12px 16px; margin-bottom: 20px; }}
.ai-summary {{ background: #111115; border: 1px solid #27272a; border-radius: 8px;
               padding: 12px 16px; margin-bottom: 20px; }}
.ai-summary h3 {{ color: #818cf8; margin: 0 0 6px 0; font-size: 14px; }}
.recommendations {{ background: #271f11; border: 1px solid #f59e0b; border-radius: 8px;
                   padding: 12px 16px; margin-bottom: 20px; color: #f59e0b; }}
</style>
</head>
<body>
<h1>Smart Assignment Cross-Checking Report</h1>
{stats_html}
{ai_html}
{rec_html}
{''.join(paragraphs_html)}
</body>
</html>"""


def _build_text(model: ReportModel, options: Optional[dict] = None) -> str:
    options = options or {}
    inc_sim = options.get("include_similarity", True)
    inc_high = options.get("include_highlights", True)
    inc_stats = options.get("include_statistics", True)
    inc_rec = options.get("include_recommendations", True)
    inc_ai = options.get("include_ai_summary", True)

    lines = []
    lines.append("=" * 60)
    lines.append("SMART ASSIGNMENT CROSS-CHECKING REPORT")
    lines.append("=" * 60)
    lines.append("")

    s = model.statistics
    if inc_sim:
        lines.append(f"Similarity: {s.similarity_percent}%")
    if inc_stats:
        lines.append(f"Total Matches: {s.total_matches}")
        lines.append(f"Exact: {s.exact_matches}  Partial: {s.partial_matches}  Semantic: {s.semantic_matches}")
        lines.append(f"Unique Paragraphs: {s.unique_paragraphs}")
        if s.ocr_used:
            conf = f"{s.avg_ocr_confidence:.0%}" if s.avg_ocr_confidence > 0 else "Yes"
            lines.append(f"OCR Used: {conf}")
    if inc_rec and s.similarity_percent >= 40:
        lines.append("")
        lines.append(f"RECOMMENDATION: Similarity level is elevated ({s.similarity_percent}%). Manual review advised.")
    if inc_ai:
        lines.append("")
        lines.append("ANALYSIS SUMMARY:")
        lines.append(_ai_summary(model))
    lines.append("")

    match_labels = {
        MatchType.EXACT: "[EXACT]",
        MatchType.PARTIAL: "[PARTIAL]",
        MatchType.SEMANTIC: "[SEMANTIC]",
        MatchType.UNIQUE: "",
        MatchType.NONE: "",
    }

    for side, doc in [("A", model.left_document), ("B", model.right_document)]:
        lines.append("-" * 60)
        lines.append(f"Document: {doc.title}")
        lines.append("-" * 60)
        for p in doc.paragraphs:
            label = match_labels.get(p.primary_match_type, "") if inc_high else ""
            ref = f" -> {p.matched_paragraph_id}" if (p.matched_paragraph_id and inc_high) else ""
            lines.append(f"  {p.paragraph_id}{ref} {label}")
            lines.append(f"  {p.text}")
            lines.append("")

    return "\n".join(lines)


def export_report(
    model: ReportModel,
    file_path: str,
    fmt: str = "html",
    options: Optional[dict] = None,
) -> str:
    fmt = fmt.lower().lstrip(".")
    if fmt == "pdf":
        from .pdf_exporter import export_pdf
        file_path = os.path.splitext(file_path)[0] + ".pdf"
        export_pdf(model, file_path, options)
        # Skip writing string content to file since pdf generation is handled natively
    elif fmt == "html":
        content = _build_html(model, options)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    elif fmt in ("txt", "text"):
        content = _build_text(model, options)
        file_path = os.path.splitext(file_path)[0] + ".txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    else:
        content = _build_html(model, options)
        file_path = os.path.splitext(file_path)[0] + ".html"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    # Auto-open if requested
    if options and (options.get("open_after_export") or options.get("auto_open_report")):
        try:
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        except Exception:
            try:
                import webbrowser
                webbrowser.open(f"file://{os.path.abspath(file_path)}")
            except Exception:
                pass

    return file_path
