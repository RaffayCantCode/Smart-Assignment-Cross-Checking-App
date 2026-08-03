import os
import sys
import zipfile
import subprocess
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QProgressBar, QCheckBox,
    QStackedWidget, QFileDialog, QFrame, QSizePolicy
)

# ----------------------------------------------------------------------
# Design Constants (Zinc Dark Theme)
# ----------------------------------------------------------------------
class Colors:
    BG_BASE = "#09090B"
    BG_SURFACE = "#111115"
    BORDER = "#27272A"
    BORDER_LIGHT = "#3F3F46"
    TEXT_PRIMARY = "#FAFAFA"
    TEXT_SECONDARY = "#A1A1AA"
    TEXT_MUTED = "#52525B"
    ACCENT = "#6366F1"
    ACCENT_HOVER = "#818CF8"
    ACCENT_PRESSED = "#4F46E5"
    ACCENT_SOFT = "#1E1B4B"
    SUCCESS = "#22C55E"

class Fonts:
    FAMILY = "Segoe UI Variable, Segoe UI, Inter, -apple-system, Arial, sans-serif"
    SIZE_H1 = 20
    SIZE_H2 = 15
    SIZE_BODY = 12
    SIZE_SMALL = 10

class Radius:
    MD = 8
    LG = 12

# ----------------------------------------------------------------------
# Helper to resolve bundled resources
# ----------------------------------------------------------------------
def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# ----------------------------------------------------------------------
# Background extraction thread
# ----------------------------------------------------------------------
class UnzipWorker(QThread):
    progress_updated = Signal(int)
    status_updated = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, zip_path, dest_dir):
        super().__init__()
        self.zip_path = zip_path
        self.dest_dir = dest_dir

    def run(self):
        try:
            if not os.path.exists(self.zip_path):
                self.finished.emit(False, f"Source package not found: {self.zip_path}")
                return

            os.makedirs(self.dest_dir, exist_ok=True)

            with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
                all_files = zip_ref.infolist()
                total_files = len(all_files)
                if total_files == 0:
                    self.finished.emit(False, "Source package is empty.")
                    return

                for i, file_info in enumerate(all_files):
                    zip_ref.extract(file_info, self.dest_dir)
                    percent = int(((i + 1) / total_files) * 100)
                    self.progress_updated.emit(percent)
                    self.status_updated.emit(f"Extracting: {file_info.filename}")

            self.finished.emit(True, "Success")
        except Exception as e:
            self.finished.emit(False, str(e))

# ----------------------------------------------------------------------
# Main Wizard Window
# ----------------------------------------------------------------------
class InstallerWizard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Assignment Checker Installer")
        self.setFixedSize(550, 400)

        # Default installation directory
        local_app_data = os.getenv("LOCALAPPDATA", os.path.expanduser("~"))
        self.install_dir = os.path.join(local_app_data, "SmartAssignmentChecker")

        # Set central widget and main dark stylesheet
        self.central_widget = QWidget()
        self.central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(self.central_widget)

        self.setStyleSheet(f"""
            #CentralWidget {{
                background-color: {Colors.BG_BASE};
            }}
            * {{
                font-family: {Fonts.FAMILY};
                color: {Colors.TEXT_PRIMARY};
            }}
            QLabel {{
                background: transparent;
            }}
            QPushButton#PrimaryButton {{
                background-color: {Colors.ACCENT};
                color: white;
                border: none;
                border-radius: {Radius.MD}px;
                padding: 10px 20px;
                font-size: {Fonts.SIZE_BODY}px;
                font-weight: 600;
            }}
            QPushButton#PrimaryButton:hover {{
                background-color: {Colors.ACCENT_HOVER};
            }}
            QPushButton#PrimaryButton:pressed {{
                background-color: {Colors.ACCENT_PRESSED};
            }}
            QPushButton#SecondaryButton {{
                background-color: transparent;
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_LIGHT};
                border-radius: {Radius.MD}px;
                padding: 9px 18px;
                font-size: {Fonts.SIZE_BODY}px;
                font-weight: 500;
            }}
            QPushButton#SecondaryButton:hover {{
                background-color: {Colors.BG_SURFACE};
                border-color: {Colors.ACCENT};
            }}
            QLineEdit {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: {Radius.MD}px;
                padding: 8px 12px;
                color: {Colors.TEXT_PRIMARY};
                font-size: {Fonts.SIZE_BODY}px;
            }}
            QLineEdit:focus {{
                border-color: {Colors.ACCENT};
            }}
            QProgressBar {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                text-align: center;
                color: transparent;
                height: 12px;
            }}
            QProgressBar::chunk {{
                background-color: {Colors.ACCENT};
                border-radius: 6px;
            }}
            QCheckBox {{
                spacing: 8px;
                font-size: {Fonts.SIZE_BODY}px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                background-color: {Colors.BG_SURFACE};
            }}
            QCheckBox::indicator:checked {{
                background-color: {Colors.ACCENT};
                border-color: {Colors.ACCENT};
            }}
        """)

        # Main layout
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(30, 30, 30, 30)

        # Header card (styled frame)
        self.header_card = QFrame()
        self.header_card.setObjectName("HeaderCard")
        self.header_card.setStyleSheet(f"""
            #HeaderCard {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: {Radius.LG}px;
            }}
        """)
        self.header_layout = QVBoxLayout(self.header_card)
        self.header_layout.setContentsMargins(20, 20, 20, 20)
        self.header_layout.setSpacing(8)

        self.title_label = QLabel("Smart Assignment Checker")
        self.title_label.setStyleSheet(f"font-size: {Fonts.SIZE_H1}px; font-weight: 700;")
        self.header_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("Setup Wizard")
        self.subtitle_label.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_SECONDARY};")
        self.header_layout.addWidget(self.subtitle_label)

        self.main_layout.addWidget(self.header_card)
        self.main_layout.addSpacing(20)

        # Stacked pages
        self.pages = QStackedWidget()
        self.main_layout.addWidget(self.pages)

        self._setup_page_welcome()
        self._setup_page_dir()
        self._setup_page_installing()
        self._setup_page_finished()

        # Bottom buttons row
        self.button_layout = QHBoxLayout()
        self.btn_back = QPushButton("Back")
        self.btn_back.setObjectName("SecondaryButton")
        self.btn_back.clicked.connect(self._prev_page)
        self.btn_back.setVisible(False)
        self.button_layout.addWidget(self.btn_back)

        self.button_layout.addStretch()

        self.btn_next = QPushButton("Next")
        self.btn_next.setObjectName("PrimaryButton")
        self.btn_next.clicked.connect(self._next_page)
        self.button_layout.addWidget(self.btn_next)

        self.main_layout.addLayout(self.button_layout)

    # ------------------------------------------------------------------
    # Wizard Pages Setup
    # ------------------------------------------------------------------
    def _setup_page_welcome(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        desc = QLabel(
            "This setup wizard will install the Smart Assignment Cross-Checking App on your computer.\n\n"
            "The similarity analysis engine, reports, PDF exporter, and modern dark interface will be installed."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_SECONDARY}; line-height: 1.4;")
        layout.addWidget(desc)
        layout.addStretch()

        self.pages.addWidget(page)

    def _setup_page_dir(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        lbl = QLabel("Choose installation destination folder:")
        lbl.setStyleSheet(f"font-size: {Fonts.SIZE_H2}px; font-weight: 600;")
        layout.addWidget(lbl)

        row = QHBoxLayout()
        self.dir_input = QLineEdit(self.install_dir)
        self.dir_input.textChanged.connect(self._on_dir_changed)
        row.addWidget(self.dir_input, 1)

        btn_browse = QPushButton("Browse...")
        btn_browse.setObjectName("SecondaryButton")
        btn_browse.clicked.connect(self._browse_dir)
        row.addWidget(btn_browse)
        layout.addLayout(row)

        lbl_space = QLabel("Requires at least 150 MB of free disk space.")
        lbl_space.setStyleSheet(f"font-size: {Fonts.SIZE_SMALL}px; color: {Colors.TEXT_MUTED};")
        layout.addWidget(lbl_space)
        layout.addStretch()

        self.pages.addWidget(page)

    def _setup_page_installing(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.lbl_status = QLabel("Ready to install.")
        self.lbl_status.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_SECONDARY};")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.lbl_detail = QLabel("")
        self.lbl_detail.setStyleSheet(f"font-size: {Fonts.SIZE_SMALL}px; color: {Colors.TEXT_MUTED};")
        layout.addWidget(self.lbl_detail)
        layout.addStretch()

        self.pages.addWidget(page)

    def _setup_page_finished(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        self.lbl_finish_status = QLabel("Installation Completed successfully!")
        self.lbl_finish_status.setStyleSheet(f"font-size: {Fonts.SIZE_H2}px; font-weight: 700; color: {Colors.SUCCESS};")
        layout.addWidget(self.lbl_finish_status)

        self.chk_shortcut = QCheckBox("Create Desktop Shortcut")
        self.chk_shortcut.setChecked(True)
        layout.addWidget(self.chk_shortcut)

        self.chk_launch = QCheckBox("Launch Smart Assignment Checker")
        self.chk_launch.setChecked(True)
        layout.addWidget(self.chk_launch)
        layout.addStretch()

        self.pages.addWidget(page)

    # ------------------------------------------------------------------
    # Button Logic / Navigation
    # ------------------------------------------------------------------
    def _on_dir_changed(self, text):
        self.install_dir = text.strip()

    def _browse_dir(self):
        selected = QFileDialog.getExistingDirectory(self, "Select Installation Folder", self.install_dir)
        if selected:
            self.dir_input.setText(selected)

    def _next_page(self):
        curr = self.pages.currentIndex()
        if curr == 0:
            # Go to folder selection
            self.pages.setCurrentIndex(1)
            self.btn_back.setVisible(True)
        elif curr == 1:
            # Go to installation page and start install
            self.pages.setCurrentIndex(2)
            self.btn_back.setVisible(False)
            self.btn_next.setVisible(False)
            self._start_installation()
        elif curr == 3:
            # Finished page - handle final actions and exit
            self._finalize_installation()

    def _prev_page(self):
        curr = self.pages.currentIndex()
        if curr == 1:
            self.pages.setCurrentIndex(0)
            self.btn_back.setVisible(False)

    # ------------------------------------------------------------------
    # Installation Execution
    # ------------------------------------------------------------------
    def _start_installation(self):
        self.lbl_status.setText("Installing application files...")
        zip_path = get_resource_path("SmartAssignmentChecker-App.zip")

        self.worker = UnzipWorker(zip_path, self.install_dir)
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.status_updated.connect(self.lbl_detail.setText)
        self.worker.finished.connect(self._on_install_finished)
        self.worker.start()

    @Slot(bool, str)
    def _on_install_finished(self, success, message):
        if success:
            self.pages.setCurrentIndex(3)
            self.btn_next.setText("Finish")
            self.btn_next.setVisible(True)
        else:
            self.pages.setCurrentIndex(2)
            self.lbl_status.setText("Installation failed.")
            self.lbl_status.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: #EF4444;")
            self.lbl_detail.setText(message)
            self.btn_back.setVisible(True)
            self.btn_back.setText("Cancel")
            self.btn_back.clicked.disconnect()
            self.btn_back.clicked.connect(self.close)

    def _finalize_installation(self):
        target_exe = os.path.join(self.install_dir, "SmartAssignmentChecker.exe")

        # 1. Create Desktop shortcut via PowerShell if selected
        if self.chk_shortcut.isChecked():
            try:
                ps_cmd = f"""
                $WshShell = New-Object -ComObject WScript.Shell
                $Shortcut = $WshShell.CreateShortcut([System.IO.Path]::Combine([System.Environment]::GetFolderPath('Desktop'), 'Smart Assignment Checker.lnk'))
                $Shortcut.TargetPath = '{target_exe}'
                $Shortcut.WorkingDirectory = '{self.install_dir}'
                $Shortcut.Save()
                """
                subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, check=True)
            except Exception as e:
                print(f"Failed to create desktop shortcut: {e}")

        # 2. Launch application if selected
        if self.chk_launch.isChecked():
            try:
                if os.path.exists(target_exe):
                    subprocess.Popen([target_exe], cwd=self.install_dir)
            except Exception as e:
                print(f"Failed to launch application: {e}")

        self.close()

# ----------------------------------------------------------------------
# Application Entry Point
# ----------------------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    wizard = InstallerWizard()
    wizard.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
