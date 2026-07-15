"""
styles/theme.py

Single source of truth for the app's visual identity: color palette,
typography, and the global QSS stylesheet. Every screen imports from
here instead of hardcoding colors, so a future re-skin (or a
"light mode" toggle) only touches this one file.
"""

# ----------------------------------------------------------------------
# Color palette
# ----------------------------------------------------------------------
class Colors:
    BG_BASE = "#0F1117"          # app background
    BG_SURFACE = "#161925"       # cards / panels
    BG_SURFACE_ALT = "#1D2130"   # nested panels, inputs
    BORDER = "#2A2F42"           # default border
    BORDER_LIGHT = "#353B52"

    TEXT_PRIMARY = "#F2F3F7"
    TEXT_SECONDARY = "#9BA1B5"
    TEXT_MUTED = "#6B7189"

    ACCENT = "#7C5CFF"           # primary accent (violet)
    ACCENT_HOVER = "#8F72FF"
    ACCENT_PRESSED = "#6A4AE8"
    ACCENT_SOFT = "#241E3D"      # accent tint for glows/backgrounds

    CYAN = "#33D6C0"             # secondary accent
    SUCCESS = "#3DD68C"
    WARNING = "#F5B84D"
    DANGER = "#FF6B6B"

    HIGH_RISK = "#FF6B6B"
    MEDIUM_RISK = "#F5B84D"
    LOW_RISK = "#3DD68C"


# ----------------------------------------------------------------------
# Typography
# ----------------------------------------------------------------------
class Fonts:
    FAMILY = "Segoe UI, Inter, -apple-system, Arial, sans-serif"
    H1 = 32
    H2 = 22
    H3 = 17
    BODY = 13
    SMALL = 11


# ----------------------------------------------------------------------
# Global stylesheet
# ----------------------------------------------------------------------
def build_stylesheet() -> str:
    c = Colors
    return f"""
    * {{
        font-family: {Fonts.FAMILY};
        color: {c.TEXT_PRIMARY};
    }}

    QWidget {{
        background-color: transparent;
    }}

    QMainWindow, #RootWindow {{
        background-color: {c.BG_BASE};
    }}

    QScrollArea {{
        border: none;
        background: transparent;
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {c.BORDER_LIGHT};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c.ACCENT};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QLabel {{
        background: transparent;
    }}

    /* Primary call-to-action button */
    QPushButton#PrimaryButton {{
        background-color: {c.ACCENT};
        color: white;
        border: none;
        border-radius: 12px;
        padding: 14px 28px;
        font-size: 14px;
        font-weight: 600;
    }}
    QPushButton#PrimaryButton:hover {{
        background-color: {c.ACCENT_HOVER};
    }}
    QPushButton#PrimaryButton:pressed {{
        background-color: {c.ACCENT_PRESSED};
    }}
    QPushButton#PrimaryButton:disabled {{
        background-color: {c.BORDER_LIGHT};
        color: {c.TEXT_MUTED};
    }}

    /* Secondary / ghost button */
    QPushButton#SecondaryButton {{
        background-color: transparent;
        color: {c.TEXT_SECONDARY};
        border: 1px solid {c.BORDER_LIGHT};
        border-radius: 12px;
        padding: 12px 24px;
        font-size: 13px;
        font-weight: 500;
    }}
    QPushButton#SecondaryButton:hover {{
        border-color: {c.ACCENT};
        color: {c.TEXT_PRIMARY};
    }}

    /* Small pill / upload buttons */
    QPushButton#PillButton {{
        background-color: {c.BG_SURFACE_ALT};
        color: {c.TEXT_PRIMARY};
        border: 1px solid {c.BORDER_LIGHT};
        border-radius: 10px;
        padding: 8px 18px;
        font-size: 12px;
        font-weight: 600;
    }}
    QPushButton#PillButton:hover {{
        border-color: {c.ACCENT};
        background-color: {c.ACCENT_SOFT};
    }}

    QPushButton#IconButton {{
        background: transparent;
        border: none;
        border-radius: 8px;
    }}
    QPushButton#IconButton:hover {{
        background-color: {c.BG_SURFACE_ALT};
    }}

    QFrame#Card {{
        background-color: {c.BG_SURFACE};
        border: 1px solid {c.BORDER};
        border-radius: 16px;
    }}

    QFrame#Card[selected="true"] {{
        border: 2px solid {c.ACCENT};
        background-color: {c.ACCENT_SOFT};
    }}

    QFrame#DropZone {{
        background-color: {c.BG_SURFACE_ALT};
        border: 2px dashed {c.BORDER_LIGHT};
        border-radius: 14px;
    }}
    QFrame#DropZone[hover="true"] {{
        border: 2px dashed {c.ACCENT};
        background-color: {c.ACCENT_SOFT};
    }}
    QFrame#DropZone[filled="true"] {{
        border: 2px solid {c.SUCCESS};
        background-color: {c.BG_SURFACE_ALT};
    }}

    QProgressBar {{
        background-color: {c.BG_SURFACE_ALT};
        border: none;
        border-radius: 8px;
        height: 16px;
        text-align: center;
        color: transparent;
    }}
    QProgressBar::chunk {{
        background-color: {c.ACCENT};
        border-radius: 8px;
    }}

    QToolTip {{
        background-color: {c.BG_SURFACE_ALT};
        color: {c.TEXT_PRIMARY};
        border: 1px solid {c.BORDER_LIGHT};
        padding: 4px 8px;
        border-radius: 6px;
    }}
    """
