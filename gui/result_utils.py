"""
gui/result_utils.py

Shared helpers used by the One-to-Many results dashboard and the detailed
report page. Centralises the derived metadata so both screens render the
same student / assignment / risk information consistently.

The backend does not currently model student identity directly, so student
name + student ID are derived, best-effort, from the file name and the head
of the document text. Keep these pure (no QWidget imports) so they are easy
to unit-test.
"""

import re

from backend.domain.document import Document
from backend.domain.comparison import ComparisonResult
from styles.theme import Colors

RISK_HIGH = "high"
RISK_MEDIUM = "medium"
RISK_LOW = "low"

# Common UK-university style student IDs are 7-9 digit integers.
_ID_REGEX = re.compile(r"\b\d{7,9}\b")

_RISK_LABELS = {
    RISK_HIGH: "High Risk",
    RISK_MEDIUM: "Medium Risk",
    RISK_LOW: "Low Risk",
}


def risk_bucket(score: int) -> str:
    """Map a similarity percentage to High / Medium / Low."""
    if score >= 70:
        return RISK_HIGH
    if score >= 40:
        return RISK_MEDIUM
    return RISK_LOW


def risk_label(bucket: str) -> str:
    return _RISK_LABELS.get(bucket, "Unknown")


def risk_color(bucket: str) -> str:
    return {
        RISK_HIGH: Colors.DANGER,
        RISK_MEDIUM: Colors.WARNING,
        RISK_LOW: Colors.SUCCESS,
    }.get(bucket, Colors.BORDER)


def risk_color_for_score(score: int) -> str:
    return risk_color(risk_bucket(score))


def _clean_student_name(stem: str, sid: str) -> str:
    """Turn a file stem into a readable display name, stripping the ID."""
    parts = re.split(r"[\s_\-]+", stem.strip())
    words = [p for p in parts if p and not _ID_REGEX.fullmatch(p)]
    name = " ".join(words).strip() or None
    if not name:
        name = stem.strip().title() or None
    else:
        name = name.title()
    return name


def derive_student_identity(doc: Document | None) -> tuple[str, str]:
    """
    Best-effort (student_name, student_id) extraction from a document.

    Students rarely name files cleanly, so we try multiple locations in
    priority order:

      1. An embedded 7-9 digit ID token inside the file name.
      2. A 7-9 digit ID in the head of the document text.
      3. Otherwise the file stem itself becomes the display name.

    Returns ("", "") when no document is available (failed comparisons).
    """
    if doc is None:
        return "", ""

    file_name = doc.file_name or ""
    stem = file_name.rsplit(".", 1)[0] if "." in file_name else file_name

    # Any 7-9 digit token embedded in the file name (e.g. Smith_12345678.pdf)
    sid = ""
    for part in re.split(r"[\s_\-]+", stem):
        if _ID_REGEX.fullmatch(part):
            sid = part
            break

    name = _clean_student_name(stem, sid)

    # Fall back to scanning the document head for a student ID.
    if not sid:
        head = (doc.content.raw_text or "")[:600]
        m = _ID_REGEX.search(head)
        if m:
            sid = m.group(0)

    if name == sid:  # stem was just an ID — avoid a pointless duplicate
        name = ""

    return name, sid


def confidence_percent(result: ComparisonResult) -> float:
    """Overall engine confidence expressed as a 0-100 percentage."""
    try:
        return float(result.statistics.confidence) * 100.0
    except Exception:
        return 0.0


def confidence_label_from_pct(pct: float) -> str:
    if pct >= 85:
        return "Very High"
    if pct >= 70:
        return "High"
    if pct >= 45:
        return "Medium"
    return "Low"


def confidence_label(result: ComparisonResult) -> str:
    return confidence_label_from_pct(confidence_percent(result))