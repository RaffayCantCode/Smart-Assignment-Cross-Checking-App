from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from backend.reporting.model import ReportParagraph, MatchType
from styles.theme import Colors, Fonts, Radius

class ParagraphWidget(QWidget):
    def __init__(self, paragraph: ReportParagraph, parent=None):
        super().__init__(parent)
        self.paragraph = paragraph
        self.setObjectName("ParagraphWidget")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 12, 16, 12)
        
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.label.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_PRIMARY}; background: transparent;")
        
        self.layout.addWidget(self.label)
        self._apply_styles()
        self._render_text()

    def _apply_styles(self):
        bg_color = "transparent"
        border_color = "transparent"
        
        if self.paragraph.primary_match_type == MatchType.EXACT:
            bg_color = "#16653420"
            border_color = "#22C55E"
        elif self.paragraph.primary_match_type == MatchType.PARTIAL:
            bg_color = "#CA8A0420"
            border_color = "#F59E0B"
        elif self.paragraph.primary_match_type == MatchType.SEMANTIC:
            bg_color = "#4338CA20"
            border_color = "#6366F1"

        if bg_color != "transparent":
            self.setStyleSheet(f"""
                ParagraphWidget {{
                    background-color: {bg_color};
                    border-left: 4px solid {border_color};
                    border-radius: {Radius.SM}px;
                }}
            """)
        else:
            self.setStyleSheet("ParagraphWidget { background-color: transparent; border: none; }")

    def _render_text(self, search_query: str = ""):
        html = self.paragraph.text.replace("<", "&lt;").replace(">", "&gt;")
        
        if search_query:
            import re
            pattern = re.compile(re.escape(search_query), re.IGNORECASE)
            html = pattern.sub(f"<span style='background-color: #FCD34D; color: #000;'>\g<0></span>", html)

        # Allow newlines to render correctly
        html = html.replace("\n", "<br>")
        self.label.setText(html)
        
    def set_font_size(self, size: int):
        self.label.setStyleSheet(f"font-size: {size}px; color: {Colors.TEXT_PRIMARY}; background: transparent;")

    def highlight_search(self, query: str):
        self._render_text(query)
