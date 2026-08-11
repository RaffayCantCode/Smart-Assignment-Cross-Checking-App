"""
test_one_to_many_integration.py

End-to-end integration tests proving that each One-to-Many comparison reuses
the existing One-to-One reporting infrastructure:

    ComparisonResult -> ReportBuilder.build() -> ReportModel -> Detailed
    Report / export_report() (HTML + PDF)

Covers:
    1. One-to-One: confidence flows through the shared calculation, Detailed
       Report model builds, and report generation (HTML + PDF) works
    2. One-to-Many: every comparison exposes its own confidence (reused, not
       re-derived), score, matches, and document metadata
    3. Opening the Detailed Report for a *selected* comparison
    4. Generating a report (PDF) for a *selected* comparison
    5. One failed doc in a batch while the others remain fully reportable
    6. High / low / zero similarity score bands across the batch
    7. GUI wiring: the results screen renders one row per comparison and the
       row actions emit that exact comparison's raw result

Runs with QT_QPA_PLATFORM=offscreen so PDF export (QTextDocument/QPdfWriter)
works without a display. Uses the fast deterministic stub engine.
"""

import os
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from backend.assignment_analyzer import AssignmentAnalyzer
from backend.reporting import ReportBuilder
from backend.reporting.exporter import export_report, build_report_filename

from test_one_to_many import (
    StubEngine,
    _docx,
    _analyzer,
    REFERENCE_PARAS,
    HIGH_SIM_PARAS,
    PARTIAL_PARAS,
    LOW_SIM_PARAS,
    NO_SIM_PARAS,
)


def _model_for(pair: dict):
    """Detailed Report model for one comparison (the UI builds this when the
    user opens the Detailed Report for a selected comparison)."""
    raw = pair["raw_result"]
    assert raw is not None, "pair must carry the raw ComparisonResult"
    model = ReportBuilder.build(raw)
    assert model.left_document.title
    assert model.right_document.title
    assert list(model.left_document.paragraphs)
    assert list(model.right_document.paragraphs)
    return model


def _export_pdf(model, tmp) -> str:
    path = os.path.join(tmp, "selected.pdf")
    out = export_report(model, path, "pdf", options={"open_after_export": False})
    assert os.path.exists(out)
    assert out.endswith(".pdf")
    assert os.path.getsize(out) > 0
    return out


def _export_html(model, tmp) -> str:
    path = os.path.join(tmp, "selected.html")
    out = export_report(model, path, "html", options={"open_after_export": False})
    assert os.path.exists(out)
    assert out.endswith(".html")
    assert os.path.getsize(out) > 0
    return out


# ---------------------------------------------------------------------------
# 1. One-to-One: confidence, Detailed Report, report generation
# ---------------------------------------------------------------------------
def test_one_to_one_confidence_details_and_export():
    with tempfile.TemporaryDirectory() as tmp:
        a = os.path.join(tmp, "a.docx")
        b = os.path.join(tmp, "b.docx")
        _docx(a, REFERENCE_PARAS)
        _docx(b, PARTIAL_PARAS)
        result = _analyzer().analyze_one_to_one(a, b)
        assert not result.get("error"), result.get("summary")
        # Confidence comes from the shared engine statistics calculation
        assert result["confidence_score"] == "95%", result["confidence_score"]
        assert result["score"] > 0

        # Detailed Report for the one-to-one comparison
        model = _model_for(result)
        assert model.statistics.confidence == 0.95

        # Generate Report (HTML + PDF)
        _export_html(model, tmp)
        _export_pdf(model, tmp)
        print("test_one_to_one_confidence_details_and_export: OK")


# ---------------------------------------------------------------------------
# 2. One-to-Many: every comparison carries its own confidence/score/matches
# ---------------------------------------------------------------------------
def test_multi_every_comparison_has_confidence():
    with tempfile.TemporaryDirectory() as tmp:
        ref = os.path.join(tmp, "ref.docx")
        targets = [HIGH_SIM_PARAS, PARTIAL_PARAS, LOW_SIM_PARAS, NO_SIM_PARAS]
        paths = []
        for i, paras in enumerate(targets):
            p = os.path.join(tmp, f"s{i + 1}.docx")
            _docx(p, paras)
            paths.append(p)
        _docx(ref, REFERENCE_PARAS)

        result = _analyzer().analyze_one_to_many(ref, paths)
        assert not result.get("error"), result.get("summary")
        pairs = result["pairs"]
        assert len(pairs) == 4

        scores = []
        for pair in pairs:
            assert not pair["error"]
            # Same confidence source as one-to-one, never a new formula
            assert pair["confidence_score"] == "95%"
            assert "confidence_score" in pair
            assert "similar_paragraphs" in pair
            assert pair["score"] >= 0
            scores.append(pair["score"])
            # Per-comparison metadata for the report title
            assert pair["raw_result"].doc_a.file_name
            assert pair["raw_result"].doc_b.file_name

        assert scores[0] > scores[1] > scores[3]
        print("test_multi_every_comparison_has_confidence:", scores)


# ---------------------------------------------------------------------------
# 3. Detailed Report for a *selected* comparison in a batch
# ---------------------------------------------------------------------------
def test_multi_detailed_report_for_selected_comparison():
    with tempfile.TemporaryDirectory() as tmp:
        ref = os.path.join(tmp, "ref.docx")
        s1 = os.path.join(tmp, "s1.docx")
        s2 = os.path.join(tmp, "s2.docx")
        _docx(ref, REFERENCE_PARAS)
        _docx(s1, HIGH_SIM_PARAS)
        _docx(s2, PARTIAL_PARAS)
        result = _analyzer().analyze_one_to_many(ref, [s1, s2])
        pairs = result["pairs"]

        # Open Detailed Report for the *second* comparison
        model = _model_for(pairs[1])
        assert model.right_document.title == pairs[1]["raw_result"].doc_b.file_name
        assert model.left_document.title == pairs[1]["raw_result"].doc_a.file_name
        assert model.statistics.similarity_percent == pairs[1]["score"]
        print("test_multi_detailed_report_for_selected_comparison: OK")


# ---------------------------------------------------------------------------
# 4. Generate Report / PDF for a *selected* comparison in a batch
# ---------------------------------------------------------------------------
def test_multi_generate_report_for_selected_comparison():
    with tempfile.TemporaryDirectory() as tmp:
        ref = os.path.join(tmp, "ref.docx")
        s1 = os.path.join(tmp, "s1.docx")
        s2 = os.path.join(tmp, "s2.docx")
        _docx(ref, REFERENCE_PARAS)
        _docx(s1, HIGH_SIM_PARAS)
        _docx(s2, NO_SIM_PARAS)
        result = _analyzer().analyze_one_to_many(ref, [s1, s2])
        pairs = result["pairs"]

        model = _model_for(pairs[0])
        pdf_out = _export_pdf(model, tmp)
        _export_html(model, tmp)

        # Suggested filename identifies the compared pair, not just the reference
        ref_name = pairs[0]["raw_result"].doc_a.file_name
        stu_name = pairs[0]["raw_result"].doc_b.file_name
        suggested = build_report_filename(f"{ref_name} vs {stu_name}")
        assert "Similarity_Report" in suggested
        assert ref_name.split(".")[0] in suggested
        assert stu_name.split(".")[0] in suggested
        print("test_multi_generate_report_for_selected_comparison:", pdf_out)


# ---------------------------------------------------------------------------
# 5. One failed doc in a batch; the others stay fully reportable
# ---------------------------------------------------------------------------
def test_multi_failed_doc_others_reportable():
    with tempfile.TemporaryDirectory() as tmp:
        ref = os.path.join(tmp, "ref.docx")
        s1 = os.path.join(tmp, "s1.docx")
        s2 = os.path.join(tmp, "s2.docx")
        missing = os.path.join(tmp, "missing.docx")
        _docx(ref, REFERENCE_PARAS)
        _docx(s1, HIGH_SIM_PARAS)
        _docx(s2, PARTIAL_PARAS)
        result = _analyzer().analyze_one_to_many(ref, [s1, missing, s2])
        pairs = result["pairs"]
        assert len(pairs) == 3
        assert pairs[1]["error"] is True
        assert not result.get("error"), result.get("summary")

        # Failed pair is excluded from actions but the rest still produce a
        # full Detailed Report + PDF.
        for idx in (0, 2):
            model = _model_for(pairs[idx])
            _export_pdf(model, tmp)
        print("test_multi_failed_doc_others_reportable: OK")


# ---------------------------------------------------------------------------
# 6. High / low / zero similarity bands present in the batch
# ---------------------------------------------------------------------------
def test_multi_high_low_zero_bands():
    with tempfile.TemporaryDirectory() as tmp:
        ref = os.path.join(tmp, "ref.docx")
        high = os.path.join(tmp, "high.docx")
        low = os.path.join(tmp, "low.docx")
        none = os.path.join(tmp, "none.docx")
        _docx(ref, REFERENCE_PARAS)
        _docx(high, HIGH_SIM_PARAS)
        _docx(low, LOW_SIM_PARAS)
        _docx(none, NO_SIM_PARAS)
        result = _analyzer().analyze_one_to_many(ref, [high, low, none])
        pairs = result["pairs"]
        assert pairs[0]["score"] == 100
        assert pairs[2]["score"] == 0
        assert result["score"] == 100
        bands = [p["risk_level"] for p in pairs]
        print("test_multi_high_low_zero_bands:", [p["score"] for p in pairs], bands)


# ---------------------------------------------------------------------------
# 7. GUI wiring: results screen renders one row per comparison and each row
#    re-emits that exact comparison's raw result into the report pipeline.
# ---------------------------------------------------------------------------
def test_results_screen_multi_rows_wire_up():
    from PySide6.QtWidgets import QApplication, QPushButton, QLabel
    from gui.results import ResultsScreen, ComparisonRowCard

    app = QApplication.instance() or QApplication([])

    with tempfile.TemporaryDirectory() as tmp:
        ref = os.path.join(tmp, "ref.docx")
        s1 = os.path.join(tmp, "s1.docx")
        s2 = os.path.join(tmp, "s2.docx")
        missing = os.path.join(tmp, "missing.docx")
        _docx(ref, REFERENCE_PARAS)
        _docx(s1, HIGH_SIM_PARAS)
        _docx(s2, PARTIAL_PARAS)
        result = _analyzer().analyze_one_to_many(ref, [s1, missing, s2])

        screen = ResultsScreen()
        screen.display_results(result)

        # One row per comparison, container visible, aggregate actions hidden
        assert not screen.multi_container.isHidden()
        assert screen.multi_list.count() == 3
        assert screen.generate_report_btn.isHidden()
        assert screen.detailed_report_btn.isHidden()

        rows = [screen.multi_list.itemAt(i).widget() for i in range(screen.multi_list.count())]
        assert all(isinstance(r, ComparisonRowCard) for r in rows)
        # Failed row surfaces the error and keeps score at '--'
        labels = [lbl.text() for lbl in rows[1].findChildren(QLabel)]
        assert any("FAILED" in t for t in labels)

        # -- Detailed Report: clicking a row's button emits that pair's raw
        # ComparisonResult via the same report_requested signal.
        captured = []
        screen.report_requested.connect(captured.append)
        det_btn = next(b for b in rows[2].findChildren(QPushButton) if b.text() == "Detailed Report")
        det_btn.click()
        assert len(captured) == 1
        assert captured[0] is result["pairs"][2]["raw_result"]

        # -- Generate Report: clicking routes that pair through the export path
        produced = []
        screen._export_raw = lambda raw, include_right=False: produced.append((raw, include_right))
        gen_btn = next(b for b in rows[0].findChildren(QPushButton) if b.text() == "Generate Report")
        gen_btn.click()
        assert len(produced) == 1
        assert produced[0][0] is result["pairs"][0]["raw_result"]
        assert produced[0][1] is True  # per-comparison filename path

        # Failed row: action buttons disabled
        for b in rows[1].findChildren(QPushButton):
            assert not b.isEnabled(), f"error row button should be disabled: {b.text()}"
        print("test_results_screen_multi_rows_wire_up: OK")


if __name__ == "__main__":
    # Create a real QApplication up front so the PDF exporter reuses it instead
    # of creating a plain QGuiApplication (which would make the GUI test abort).
    from PySide6.QtWidgets import QApplication as _QA
    if _QA.instance() is None:
        _QA([])

    tests = [
        ("test_one_to_one_confidence_details_and_export", test_one_to_one_confidence_details_and_export),
        ("test_multi_every_comparison_has_confidence", test_multi_every_comparison_has_confidence),
        ("test_multi_detailed_report_for_selected_comparison", test_multi_detailed_report_for_selected_comparison),
        ("test_multi_generate_report_for_selected_comparison", test_multi_generate_report_for_selected_comparison),
        ("test_multi_failed_doc_others_reportable", test_multi_failed_doc_others_reportable),
        ("test_multi_high_low_zero_bands", test_multi_high_low_zero_bands),
        ("test_results_screen_multi_rows_wire_up", test_results_screen_multi_rows_wire_up),
    ]
    for name, fn in tests:
        print(f"\n--- {name} ---")
        try:
            fn()
        except AssertionError as e:
            print(f"FAIL: {e}")
            raise
    print("\nAll one-to-many integration tests passed!")