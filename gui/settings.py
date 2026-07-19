"""
gui/settings.py

Settings screen layout redesigned with modern styling.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QComboBox, QCheckBox, QSlider
)

from styles.theme import Colors, Fonts, Spacing, Icons, IconSize, render_icon, Radius, ActiveTheme


class SettingsScreen(QWidget):

    back_requested = Signal()
    theme_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)

        root = QVBoxLayout(container)
        root.setContentsMargins(Spacing.XXXL, Spacing.XXL, Spacing.XXXL, Spacing.XXL)
        root.setSpacing(Spacing.LG)
        root.setAlignment(Qt.AlignTop)

        # -- top bar: back ----------------------------------------------------
        top_bar = QHBoxLayout()
        back_button = QPushButton("  Back")
        back_button.setObjectName("GhostButton")
        back_button.setIcon(render_icon(Icons.ARROW_LEFT, Colors.TEXT_SECONDARY, IconSize.SM))
        back_button.setCursor(Qt.PointingHandCursor)
        back_button.clicked.connect(self.back_requested.emit)
        top_bar.addWidget(back_button)
        top_bar.addStretch()
        root.addLayout(top_bar)

        title = QLabel("Settings")
        title.setStyleSheet(f"font-size: {Fonts.SIZE_H2}px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
        root.addWidget(title)
        
        root.addSpacing(Spacing.SM)

        # Helper method for creating cards
        def create_section(title, icon_svg):
            card = QFrame()
            card.setObjectName("Card")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
            layout.setSpacing(Spacing.MD)

            header = QHBoxLayout()
            icon = QLabel()
            icon.setPixmap(render_icon(icon_svg, Colors.TEXT_PRIMARY, IconSize.LG))
            header.addWidget(icon)
            
            lbl = QLabel(title)
            lbl.setStyleSheet(f"font-size: {Fonts.SIZE_BODY_LG}px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
            header.addWidget(lbl)
            header.addStretch()
            layout.addLayout(header)
            
            return card, layout
            
        # -- Appearance --
        app_card, app_layout = create_section("Appearance", Icons.LAYERS)
        
        theme_layout = QHBoxLayout()
        theme_label = QLabel("Theme:")
        theme_label.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_SECONDARY};")
        theme_layout.addWidget(theme_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "System"])
        self.theme_combo.setCurrentText(ActiveTheme.mode)
        self.theme_combo.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; background-color: {Colors.BG_SURFACE_ALT}; color: {Colors.TEXT_PRIMARY}; border: 1px solid {Colors.BORDER}; padding: 4px; border-radius: {Radius.SM}px;")
        
        # Emit signal when changed
        self.theme_combo.currentTextChanged.connect(self.theme_changed.emit)
        
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        app_layout.addLayout(theme_layout)
        root.addWidget(app_card)

        # -- Reports --
        rep_card, rep_layout = create_section("Reports", Icons.FILE)
        
        self.rep_sim_cb = QCheckBox("Include similarity percentage")
        self.rep_sim_cb.setChecked(True)
        self.rep_high_cb = QCheckBox("Include highlighted text")
        self.rep_high_cb.setChecked(True)
        self.rep_stat_cb = QCheckBox("Include statistics")
        self.rep_stat_cb.setChecked(True)
        self.rep_ai_cb = QCheckBox("Include AI summary")
        self.rep_ai_cb.setChecked(True)
        self.rep_rec_cb = QCheckBox("Include recommendations")
        self.rep_rec_cb.setChecked(True)
        self.rep_auto_cb = QCheckBox("Auto-open report after generation")
        
        for cb in [self.rep_sim_cb, self.rep_high_cb, self.rep_stat_cb, self.rep_ai_cb, self.rep_rec_cb, self.rep_auto_cb]:
            cb.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_SECONDARY};")
            rep_layout.addWidget(cb)
            
        root.addWidget(rep_card)

        # -- Export Preferences --
        exp_card, exp_layout = create_section("Export Preferences", Icons.UPLOAD)
        
        fmt_layout = QHBoxLayout()
        fmt_label = QLabel("Default report format:")
        fmt_label.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_SECONDARY};")
        fmt_layout.addWidget(fmt_label)
        
        self.export_fmt_combo = QComboBox()
        self.export_fmt_combo.addItems(["PDF", "DOCX", "HTML"])
        self.export_fmt_combo.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; background-color: {Colors.BG_SURFACE_ALT}; color: {Colors.TEXT_PRIMARY}; border: 1px solid {Colors.BORDER}; padding: 4px; border-radius: {Radius.SM}px;")
        fmt_layout.addWidget(self.export_fmt_combo)
        fmt_layout.addStretch()
        exp_layout.addLayout(fmt_layout)
        
        self.exp_open_cb = QCheckBox("Open report after export")
        self.exp_open_cb.setChecked(True)
        self.exp_open_cb.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_SECONDARY};")
        exp_layout.addWidget(self.exp_open_cb)
        
        root.addWidget(exp_card)
        
        # -- Analysis Preferences --
        ana_card, ana_layout = create_section("Analysis Preferences", Icons.SETTINGS)
        
        thresh_layout = QHBoxLayout()
        thresh_label = QLabel("Similarity Threshold:")
        thresh_label.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_SECONDARY};")
        thresh_layout.addWidget(thresh_label)
        
        self.thresh_slider = QSlider(Qt.Horizontal)
        self.thresh_slider.setRange(0, 100)
        self.thresh_slider.setValue(20)
        thresh_layout.addWidget(self.thresh_slider)
        
        self.thresh_val_label = QLabel("20%")
        self.thresh_val_label.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_PRIMARY};")
        self.thresh_slider.valueChanged.connect(lambda v: self.thresh_val_label.setText(f"{v}%"))
        thresh_layout.addWidget(self.thresh_val_label)
        ana_layout.addLayout(thresh_layout)
        
        self.ign_quotes_cb = QCheckBox("Ignore quotations")
        self.ign_quotes_cb.setChecked(True)
        self.ign_refs_cb = QCheckBox("Ignore references")
        self.ign_refs_cb.setChecked(True)
        self.ign_bib_cb = QCheckBox("Ignore bibliography")
        self.ign_bib_cb.setChecked(True)
        self.ign_fmt_cb = QCheckBox("Ignore formatting differences")
        self.ign_fmt_cb.setChecked(True)
        
        for cb in [self.ign_quotes_cb, self.ign_refs_cb, self.ign_bib_cb, self.ign_fmt_cb]:
            cb.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_SECONDARY};")
            ana_layout.addWidget(cb)
            
        root.addWidget(ana_card)
        
        # -- Performance --
        perf_card, perf_layout = create_section("Performance", Icons.CLOCK)
        
        thread_layout = QHBoxLayout()
        thread_label = QLabel("Maximum comparison threads:")
        thread_label.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_SECONDARY};")
        thread_layout.addWidget(thread_label)
        
        self.thread_combo = QComboBox()
        self.thread_combo.addItems(["1", "2", "4", "8", "Auto"])
        self.thread_combo.setCurrentText("Auto")
        self.thread_combo.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; background-color: {Colors.BG_SURFACE_ALT}; color: {Colors.TEXT_PRIMARY}; border: 1px solid {Colors.BORDER}; padding: 4px; border-radius: {Radius.SM}px;")
        thread_layout.addWidget(self.thread_combo)
        thread_layout.addStretch()
        perf_layout.addLayout(thread_layout)
        
        self.perf_cache_cb = QCheckBox("Enable caching")
        self.perf_cache_cb.setChecked(True)
        self.perf_hw_cb = QCheckBox("Hardware acceleration (future)")
        self.perf_hw_cb.setEnabled(False)
        
        for cb in [self.perf_cache_cb, self.perf_hw_cb]:
            cb.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_SECONDARY};")
            perf_layout.addWidget(cb)
            
        root.addWidget(perf_card)
        
        # -- Notifications --
        notif_card, notif_layout = create_section("Notifications", Icons.CHECK)
        
        self.notif_comp_cb = QCheckBox("Notify when analysis completes")
        self.notif_comp_cb.setChecked(True)
        self.notif_rep_cb = QCheckBox("Notify when report is generated")
        self.notif_rep_cb.setChecked(True)
        
        for cb in [self.notif_comp_cb, self.notif_rep_cb]:
            cb.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_SECONDARY};")
            notif_layout.addWidget(cb)
            
        root.addWidget(notif_card)

        root.addStretch()

