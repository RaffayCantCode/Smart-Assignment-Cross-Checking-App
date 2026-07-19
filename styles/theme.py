"""
styles/theme.py

Single source of truth for the app's visual identity: color palette,
typography, spacing, animations, and the global QSS stylesheet.
Also provides SVG icon rendering.
"""

from PySide6.QtGui import QColor, QFont, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import Qt, QByteArray

# ----------------------------------------------------------------------
# Design Tokens
# ----------------------------------------------------------------------

class DarkTheme:
    BG_BASE = "#09090B"          # zinc-950
    BG_SURFACE = "#111115"       # zinc-900 (cards)
    BG_SURFACE_ALT = "#18181B"   # zinc-900 variant (nested, inputs)
    BG_HOVER = "#1F1F23"         # zinc-800 variant (hover)
    
    BORDER = "#27272A"           # zinc-800
    BORDER_LIGHT = "#3F3F46"     # zinc-700
    
    TEXT_PRIMARY = "#FAFAFA"
    TEXT_SECONDARY = "#A1A1AA"
    TEXT_MUTED = "#52525B"
    
    ACCENT = "#6366F1"           # indigo-500
    ACCENT_HOVER = "#818CF8"
    ACCENT_PRESSED = "#4F46E5"
    ACCENT_SOFT = "#1E1B4B"      # indigo bg tint
    
    SUCCESS = "#22C55E"
    WARNING = "#F59E0B"
    DANGER = "#EF4444"

    HIGH_RISK = DANGER
    MEDIUM_RISK = WARNING
    LOW_RISK = SUCCESS

class LightTheme:
    BG_BASE = "#F8FAFC"          # slate-50
    BG_SURFACE = "#FFFFFF"       # white
    BG_SURFACE_ALT = "#F1F5F9"   # slate-100
    BG_HOVER = "#E2E8F0"         # slate-200
    
    BORDER = "#E2E8F0"           # slate-200
    BORDER_LIGHT = "#CBD5E1"     # slate-300
    
    TEXT_PRIMARY = "#0F172A"     # slate-900
    TEXT_SECONDARY = "#475569"   # slate-600
    TEXT_MUTED = "#94A3B8"       # slate-400
    
    ACCENT = "#4F46E5"           # indigo-600
    ACCENT_HOVER = "#4338CA"
    ACCENT_PRESSED = "#3730A3"
    ACCENT_SOFT = "#EEF2FF"      # indigo-50
    
    SUCCESS = "#16A34A"
    WARNING = "#D97706"
    DANGER = "#DC2626"

    HIGH_RISK = DANGER
    MEDIUM_RISK = WARNING
    LOW_RISK = SUCCESS

class Colors:
    pass

# We also need a way to track the current theme
class ActiveTheme:
    mode = "System"

def apply_theme(mode: str):
    ActiveTheme.mode = mode
    # For 'System', we'll default to Dark unless we do full OS detection.
    # For now, let's just make System = Dark in this prototype.
    actual_mode = "Dark" if mode == "System" else mode
    
    theme_cls = LightTheme if actual_mode == "Light" else DarkTheme
    for attr in dir(theme_cls):
        if not attr.startswith("__"):
            setattr(Colors, attr, getattr(theme_cls, attr))

apply_theme("System")
class Fonts:
    FAMILY = "Segoe UI Variable, Segoe UI, Inter, -apple-system, Arial, sans-serif"
    SIZE_DISPLAY = 56
    SIZE_H1 = 28
    SIZE_H2 = 22
    SIZE_H3 = 17
    SIZE_BODY_LG = 15
    SIZE_BODY = 13
    SIZE_SMALL = 11

class Radius:
    SM = 6
    MD = 8
    LG = 12
    XL = 16
    PILL = 999

class Spacing:
    XS = 4
    SM = 8
    MD = 16
    LG = 24
    XL = 32
    XXL = 48
    XXXL = 64

class Anim:
    HOVER = 150
    SELECT = 220
    PAGE = 280
    RING = 1400

class IconSize:
    SM = 14
    MD = 18
    LG = 24
    XL = 32

# ----------------------------------------------------------------------
# Icons (Lucide SVG strings)
# ----------------------------------------------------------------------

class Icons:
    _base_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{path}</svg>'
    
    FILE = _base_svg.format(color="{color}", path='<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/>')
    CHECK = _base_svg.format(color="{color}", path='<polyline points="20 6 9 17 4 12"/>')
    SETTINGS = _base_svg.format(color="{color}", path='<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>')
    ARROW_LEFT = _base_svg.format(color="{color}", path='<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>')
    ONE_TO_ONE = _base_svg.format(color="{color}", path='<path d="m16 3 4 4-4 4"/><path d="M20 7H4"/><path d="m8 21-4-4 4-4"/><path d="M4 17h16"/>')
    ONE_TO_MANY = _base_svg.format(color="{color}", path='<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>')
    UPLOAD = _base_svg.format(color="{color}", path='<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/>')
    LAYERS = _base_svg.format(color="{color}", path='<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 12 12 17 22 12"/><polyline points="2 17 12 22 22 17"/>')
    CLOCK = _base_svg.format(color="{color}", path='<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>')
    SHIELD_ALERT = _base_svg.format(color="{color}", path='<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M12 8v4"/><path d="M12 16h.01"/>')
    REFRESH = _base_svg.format(color="{color}", path='<path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/>')

def render_icon(svg_string: str, color: str, size: int) -> QPixmap:
    """Render an SVG string to a QPixmap with the specified color and size."""
    svg = svg_string.replace("{color}", color)
    renderer = QSvgRenderer(QByteArray(svg.encode('utf-8')))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter)
    painter.end()
    return pixmap

# ----------------------------------------------------------------------
# Global stylesheet
# ----------------------------------------------------------------------
def build_stylesheet() -> str:
    c = Colors
    r = Radius
    f = Fonts
    
    return f"""
    * {{
        font-family: {f.FAMILY};
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
        background: {c.TEXT_MUTED};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QLabel {{
        background: transparent;
    }}
    
    QLabel#SectionLabel {{
        font-size: {f.SIZE_SMALL}px;
        font-weight: 700;
        letter-spacing: 1px;
        color: {c.TEXT_MUTED};
        text-transform: uppercase;
    }}
    
    QFrame#Divider {{
        background-color: {c.BORDER_LIGHT};
        max-height: 1px;
        min-height: 1px;
    }}

    /* Primary call-to-action button */
    QPushButton#PrimaryButton {{
        background-color: {c.ACCENT};
        color: white;
        border: none;
        border-radius: {r.MD}px;
        padding: 12px 24px;
        font-size: {f.SIZE_BODY}px;
        font-weight: 600;
    }}
    QPushButton#PrimaryButton:hover {{
        background-color: {c.ACCENT_HOVER};
    }}
    QPushButton#PrimaryButton:pressed {{
        background-color: {c.ACCENT_PRESSED};
    }}
    QPushButton#PrimaryButton:disabled {{
        background-color: {c.BG_SURFACE_ALT};
        color: {c.TEXT_MUTED};
        border: 1px solid {c.BORDER};
    }}

    /* Secondary / Ghost button */
    QPushButton#SecondaryButton {{
        background-color: transparent;
        color: {c.TEXT_PRIMARY};
        border: 1px solid {c.BORDER_LIGHT};
        border-radius: {r.MD}px;
        padding: 10px 20px;
        font-size: {f.SIZE_BODY}px;
        font-weight: 500;
    }}
    QPushButton#SecondaryButton:hover {{
        border-color: {c.ACCENT};
        background-color: {c.BG_HOVER};
    }}
    
    QPushButton#GhostButton {{
        background-color: transparent;
        color: {c.TEXT_SECONDARY};
        border: none;
        border-radius: {r.MD}px;
        padding: 8px 16px;
        font-size: {f.SIZE_BODY}px;
        font-weight: 500;
    }}
    QPushButton#GhostButton:hover {{
        background-color: {c.BG_HOVER};
        color: {c.TEXT_PRIMARY};
    }}

    /* Small pill / upload buttons */
    QPushButton#PillButton {{
        background-color: {c.BG_SURFACE_ALT};
        color: {c.TEXT_PRIMARY};
        border: 1px solid {c.BORDER_LIGHT};
        border-radius: {r.PILL}px;
        padding: 6px 16px;
        font-size: 12px;
        font-weight: 500;
    }}
    QPushButton#PillButton:hover {{
        border-color: {c.ACCENT};
        background-color: {c.BG_HOVER};
    }}

    QPushButton#IconButton {{
        background: transparent;
        border: none;
        border-radius: {r.SM}px;
        padding: 8px;
    }}
    QPushButton#IconButton:hover {{
        background-color: {c.BG_HOVER};
    }}

    QFrame#Card {{
        background-color: {c.BG_SURFACE};
        border: 1px solid {c.BORDER};
        border-radius: {r.LG}px;
    }}
    
    QFrame#CardHoverable {{
        background-color: {c.BG_SURFACE};
        border: 1px solid {c.BORDER};
        border-radius: {r.LG}px;
    }}
    QFrame#CardHoverable:hover {{
        border: 1px solid {c.BORDER_LIGHT};
        background-color: {c.BG_HOVER};
    }}

    QFrame#DropZone {{
        background-color: {c.BG_SURFACE_ALT};
        border: 1px solid {c.BORDER};
        border-radius: {r.LG}px;
    }}

    QProgressBar {{
        background-color: {c.BG_SURFACE_ALT};
        border: none;
        border-radius: {r.SM}px;
        height: 8px;
        text-align: center;
        color: transparent;
    }}
    QProgressBar::chunk {{
        background-color: {c.ACCENT};
        border-radius: {r.SM}px;
    }}

    QToolTip {{
        background-color: {c.BG_SURFACE_ALT};
        color: {c.TEXT_PRIMARY};
        border: 1px solid {c.BORDER_LIGHT};
        padding: 4px 8px;
        border-radius: {r.SM}px;
        font-family: {f.FAMILY};
        font-size: {f.SIZE_SMALL}px;
    }}
    """
