from PySide6.QtCore import QSettings


_NAMESPACE = "smart-assignment-checker"


def _settings() -> QSettings:
    return QSettings(_NAMESPACE, _NAMESPACE)


def get_settings() -> QSettings:
    return _settings()


def get_analysis_config() -> dict:
    s = _settings()
    threshold_raw = int(s.value("similarity_threshold", 75, type=int))
    return {
        "similarity_threshold": threshold_raw / 100.0,
        "sentence_threshold": float(s.value("sentence_threshold", 0.80, type=float)),
        "enable_sentence_matching": s.value("enable_sentence_matching", "false") == "true",
        "max_paragraphs": int(s.value("max_paragraphs", 300, type=int)),
        "batch_size": int(s.value("batch_size", 64, type=int)),
        "ignore_quotations": s.value("ignore_quotations", "true") == "true",
        "ignore_references": s.value("ignore_references", "true") == "true",
        "ignore_bibliography": s.value("ignore_bibliography", "true") == "true",
        "ignore_formatting": s.value("ignore_formatting", "true") == "true",
        "max_threads": s.value("max_threads", "Auto"),
        "enable_cache": s.value("enable_cache", "true") == "true",
    }


def get_export_config() -> dict:
    s = _settings()
    return {
        "export_format": str(s.value("export_format", "PDF")).lower(),
        "include_similarity": s.value("include_similarity", "true") == "true",
        "include_highlights": s.value("include_highlights", "true") == "true",
        "include_statistics": s.value("include_statistics", "true") == "true",
        "include_ai_summary": s.value("include_ai_summary", "true") == "true",
        "include_recommendations": s.value("include_recommendations", "true") == "true",
        "auto_open_report": s.value("auto_open_report", "false") == "true",
        "open_after_export": s.value("open_after_export", "true") == "true",
    }


def get_notification_config() -> dict:
    s = _settings()
    return {
        "notify_completion": s.value("notify_completion", "true") == "true",
        "notify_report": s.value("notify_report", "true") == "true",
    }
