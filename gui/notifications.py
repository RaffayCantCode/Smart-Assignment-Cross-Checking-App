from PySide6.QtWidgets import QSystemTrayIcon, QApplication
from gui.settings_manager import get_notification_config

_tray_icon = None

def get_tray_icon() -> QSystemTrayIcon:
    global _tray_icon
    if _tray_icon is None:
        app = QApplication.instance()
        if app:
            _tray_icon = QSystemTrayIcon(app)
            _tray_icon.setVisible(True)
    return _tray_icon

def notify_analysis_complete(similarity_score: int):
    cfg = get_notification_config()
    if not cfg.get("notify_completion", True):
        return
    tray = get_tray_icon()
    if tray and tray.isSystemTrayAvailable():
        tray.showMessage(
            "Analysis Complete",
            f"Cross-checking finished. Similarity score: {similarity_score}%.",
            QSystemTrayIcon.Information,
            3500
        )

def notify_report_exported(file_path: str):
    cfg = get_notification_config()
    if not cfg.get("notify_report", True):
        return
    filename = file_path.replace("\\", "/").split("/")[-1]
    tray = get_tray_icon()
    if tray and tray.isSystemTrayAvailable():
        tray.showMessage(
            "Report Exported",
            f"Successfully exported report to {filename}.",
            QSystemTrayIcon.Information,
            3500
        )
