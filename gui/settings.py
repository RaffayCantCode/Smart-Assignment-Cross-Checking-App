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
from gui.settings_manager import get_settings


def _style_combo(combo: QComboBox) -> QComboBox:
    """Applies a modern segmented-control look to a QComboBox."""
    combo.setStyleSheet(f"""
        QComboBox {{
            font-size: {Fonts.SIZE_BODY}px;
            color: {Colors.TEXT_PRIMARY};
            background-color: {Colors.BG_SURFACE_ALT};
            border: 1px solid {Colors.BORDER};
            border-radius: {Radius.SM}px;
            padding: 7px 12px;
            min-width: 120px;
        }}
        QComboBox:hover {{ border-color: {Colors.ACCENT}; }}
        QComboBox:focus {{ border-color: {Colors.ACCENT}; }}
        QComboBox::drop-down {{
            border: none;
            width: 28px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {Colors.TEXT_MUTED};
            margin-right: 8px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {Colors.BG_SURFACE};
            color: {Colors.TEXT_PRIMARY};
            border: 1px solid {Colors.BORDER};
            border-radius: {Radius.SM}px;
            outline: 0;
            padding: 4px;
            selection-background-color: {Colors.ACCENT};
            selection-color: #FFFFFF;
        }}
    """)
    return combo


def _style_checkbox(cb: QCheckBox) -> QCheckBox:
    """Modern checkable toggle styling with a rounded indicator."""
    cb.setStyleSheet(f"""
        QCheckBox {{
            font-size: {Fonts.SIZE_BODY}px;
            color: {Colors.TEXT_SECONDARY};
            spacing: 10px;
        }}
        QCheckBox:hover {{ color: {Colors.TEXT_PRIMARY}; }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: {Radius.SM}px;
            border: 1px solid {Colors.BORDER_LIGHT};
            background-color: {Colors.BG_SURFACE_ALT};
        }}
        QCheckBox::indicator:hover {{ border-color: {Colors.ACCENT}; }}
        QCheckBox::indicator:checked {{
            background-color: {Colors.ACCENT};
            border-color: {Colors.ACCENT};
        }}
        QCheckBox:disabled {{ color: {Colors.TEXT_MUTED}; }}
        QCheckBox:disabled::indicator {{
            border-color: {Colors.BORDER};
            background-color: {Colors.BG_SURFACE_ALT};
        }}
    """)
    return cb


def _style_slider(slider: QSlider) -> QSlider:
    """Modern accent slider with a filled groove."""
    slider.setStyleSheet(f"""
        QSlider::groove:horizontal {{
            height: 6px;
            background: {Colors.BG_SURFACE_ALT};
            border: 1px solid {Colors.BORDER};
            border-radius: 3px;
        }}
        QSlider::sub-page:horizontal {{
            background: {Colors.ACCENT};
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            width: 18px;
            height: 18px;
            margin: -7px 0;
            border-radius: 9px;
            background: {Colors.BG_SURFACE};
            border: 2px solid {Colors.ACCENT};
        }}
        QSlider::handle:horizontal:hover {{
            background: {Colors.ACCENT_SOFT};
            border-color: {Colors.ACCENT_HOVER};
        }}
    """)
    return slider


def _style_section_card(card: QFrame) -> QFrame:
    card.setObjectName("SettingsCard")
    card.setStyleSheet(f"""
        #SettingsCard {{
            background-color: {Colors.BG_SURFACE};
            border: 1px solid {Colors.BORDER};
            border-radius: {Radius.LG}px;
        }}
        #SettingsCard:hover {{
            border-color: {Colors.BORDER_LIGHT};
        }}
    """)
    return card


class SettingsScreen(QWidget):

    back_requested = Signal()
    theme_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = get_settings()

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

        subtitle = QLabel("Tune how the app analyzes documents and generates reports.")
        subtitle.setStyleSheet(
            f"font-size: {Fonts.SIZE_BODY_LG}px; "
            f"color: {Colors.TEXT_MUTED};"
        )
        root.addWidget(subtitle)

        root.addSpacing(Spacing.SM)

        # Helper method for creating cards
        def create_section(title, icon_svg):
            card = QFrame()
            _style_section_card(card)
            layout = QVBoxLayout(card)
            layout.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
            layout.setSpacing(Spacing.MD)

            header = QHBoxLayout()
            header.setSpacing(Spacing.SM)

            icon = QLabel()
            icon.setPixmap(render_icon(icon_svg, Colors.ACCENT, IconSize.MD))
            header.addWidget(icon)

            lbl = QLabel(title)
            lbl.setStyleSheet(f"font-size: {Fonts.SIZE_BODY_LG}px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
            header.addWidget(lbl)
            header.addStretch()
            layout.addLayout(header)

            divider = QFrame()
            divider.setObjectName("Divider")
            divider.setStyleSheet(f"#Divider {{ background-color: {Colors.BORDER}; max-height: 1px; min-height: 1px; border: none; }}")
            layout.addWidget(divider)

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
        _style_combo(self.theme_combo)
        
        self.theme_combo.currentTextChanged.connect(self.theme_changed.emit)
        self.theme_combo.currentTextChanged.connect(self._save_theme)
        
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
        
        self._report_cbs = [self.rep_sim_cb, self.rep_high_cb, self.rep_stat_cb, self.rep_ai_cb, self.rep_rec_cb, self.rep_auto_cb]
        for cb in self._report_cbs:
            _style_checkbox(cb)
            cb.stateChanged.connect(lambda _, c=cb: self._save_report_checkboxes())
            rep_layout.addWidget(cb)
            
        root.addWidget(rep_card)

        # -- Export Preferences --
        exp_card, exp_layout = create_section("Export Preferences", Icons.UPLOAD)
        
        fmt_layout = QHBoxLayout()
        fmt_label = QLabel("Default report format:")
        fmt_label.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_SECONDARY};")
        fmt_layout.addWidget(fmt_label)
        
        self.export_fmt_combo = QComboBox()
        self.export_fmt_combo.addItems(["PDF", "HTML", "TXT"])
        _style_combo(self.export_fmt_combo)
        self.export_fmt_combo.currentTextChanged.connect(self._save_export_format)
        fmt_layout.addWidget(self.export_fmt_combo)
        fmt_layout.addStretch()
        exp_layout.addLayout(fmt_layout)
        
        self.exp_open_cb = QCheckBox("Open report after export")
        self.exp_open_cb.setChecked(True)
        _style_checkbox(self.exp_open_cb)
        self.exp_open_cb.stateChanged.connect(self._save_export_open)
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
        _style_slider(self.thresh_slider)
        thresh_layout.addWidget(self.thresh_slider)
        
        self.thresh_val_label = QLabel("20%")
        self.thresh_val_label.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_PRIMARY};")
        self.thresh_slider.valueChanged.connect(lambda v: self.thresh_val_label.setText(f"{v}%"))
        self.thresh_slider.valueChanged.connect(self._save_threshold)
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
        
        self._analysis_cbs = [self.ign_quotes_cb, self.ign_refs_cb, self.ign_bib_cb, self.ign_fmt_cb]
        for cb in self._analysis_cbs:
            _style_checkbox(cb)
            cb.stateChanged.connect(lambda _, c=cb: self._save_analysis_checkboxes())
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
        _style_combo(self.thread_combo)
        self.thread_combo.currentTextChanged.connect(self._save_threads)
        thread_layout.addWidget(self.thread_combo)
        thread_layout.addStretch()
        perf_layout.addLayout(thread_layout)
        
        self.perf_cache_cb = QCheckBox("Enable caching")
        self.perf_cache_cb.setChecked(True)
        self.perf_cache_cb.stateChanged.connect(self._save_cache)
        self.perf_hw_cb = QCheckBox("Hardware acceleration (future)")
        self.perf_hw_cb.setEnabled(False)
        
        for cb in [self.perf_cache_cb, self.perf_hw_cb]:
            _style_checkbox(cb)
            perf_layout.addWidget(cb)
            
        root.addWidget(perf_card)
        
        # -- Notifications --
        notif_card, notif_layout = create_section("Notifications", Icons.CHECK)
        
        self.notif_comp_cb = QCheckBox("Notify when analysis completes")
        self.notif_comp_cb.setChecked(True)
        self.notif_rep_cb = QCheckBox("Notify when report is generated")
        self.notif_rep_cb.setChecked(True)
        
        self._notif_cbs = [self.notif_comp_cb, self.notif_rep_cb]
        for cb in self._notif_cbs:
            _style_checkbox(cb)
            cb.stateChanged.connect(lambda _, c=cb: self._save_notification_checkboxes())
            notif_layout.addWidget(cb)
            
        root.addWidget(notif_card)

        root.addStretch()

        self._load_settings()

    def showEvent(self, event):
        super().showEvent(event)
        self._load_settings()

    def _save_value(self, key: str, value):
        self._settings.setValue(key, value)

    def _load_settings(self):
        self.thresh_slider.setValue(int(self._settings.value("similarity_threshold", 75, type=int)))
        self.export_fmt_combo.setCurrentText(self._settings.value("export_format", "HTML"))

        cb_map = {
            self.rep_sim_cb: ("include_similarity", True),
            self.rep_high_cb: ("include_highlights", True),
            self.rep_stat_cb: ("include_statistics", True),
            self.rep_ai_cb: ("include_ai_summary", True),
            self.rep_rec_cb: ("include_recommendations", True),
            self.rep_auto_cb: ("auto_open_report", False),
            self.exp_open_cb: ("open_after_export", True),
            self.ign_quotes_cb: ("ignore_quotations", True),
            self.ign_refs_cb: ("ignore_references", True),
            self.ign_bib_cb: ("ignore_bibliography", True),
            self.ign_fmt_cb: ("ignore_formatting", True),
            self.perf_cache_cb: ("enable_cache", True),
            self.notif_comp_cb: ("notify_completion", True),
            self.notif_rep_cb: ("notify_report", True),
        }
        for cb, (key, default) in cb_map.items():
            val = self._settings.value(key, "true" if default else "false")
            cb.setChecked(val == "true")

        thread_val = self._settings.value("max_threads", "Auto")
        idx = self.thread_combo.findText(thread_val)
        if idx >= 0:
            self.thread_combo.setCurrentIndex(idx)

    def _save_theme(self, mode: str):
        self._settings.setValue("theme", mode)

    def _save_report_checkboxes(self):
        keys = {
            self.rep_sim_cb: "include_similarity",
            self.rep_high_cb: "include_highlights",
            self.rep_stat_cb: "include_statistics",
            self.rep_ai_cb: "include_ai_summary",
            self.rep_rec_cb: "include_recommendations",
            self.rep_auto_cb: "auto_open_report",
        }
        for cb, key in keys.items():
            self._settings.setValue(key, "true" if cb.isChecked() else "false")

    def _save_export_format(self, fmt: str):
        self._settings.setValue("export_format", fmt)

    def _save_export_open(self):
        self._settings.setValue("open_after_export", "true" if self.exp_open_cb.isChecked() else "false")

    def _save_threshold(self):
        self._settings.setValue("similarity_threshold", self.thresh_slider.value())

    def _save_analysis_checkboxes(self):
        keys = {
            self.ign_quotes_cb: "ignore_quotations",
            self.ign_refs_cb: "ignore_references",
            self.ign_bib_cb: "ignore_bibliography",
            self.ign_fmt_cb: "ignore_formatting",
        }
        for cb, key in keys.items():
            self._settings.setValue(key, "true" if cb.isChecked() else "false")

    def _save_threads(self, val: str):
        self._settings.setValue("max_threads", val)

    def _save_cache(self):
        self._settings.setValue("enable_cache", "true" if self.perf_cache_cb.isChecked() else "false")

    def _save_notification_checkboxes(self):
        keys = {
            self.notif_comp_cb: "notify_completion",
            self.notif_rep_cb: "notify_report",
        }
        for cb, key in keys.items():
            self._settings.setValue(key, "true" if cb.isChecked() else "false")

