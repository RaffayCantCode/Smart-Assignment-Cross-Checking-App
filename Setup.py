import os
import sys
import tempfile
import zipfile
import shutil
import subprocess
from PySide6.QtCore import QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QProgressBar, QCheckBox,
    QStackedWidget, QFileDialog, QFrame,
)

"""
Setup.py

The installer. When a user runs this (as setup.exe or via `python Setup.py`),
it installs the Smart Assignment Cross-Checking App into a folder containing
SmartAssignmentChecker.exe, uninstall.exe, and every supporting file.

The app package (SmartAssignmentChecker-App.zip) is located from:
  1. Inside this frozen executable (bundled by build_setup.py via --add-data).
  2. Next to this script.
  3. The project's dist/ folder.
  4. A ready-made dist/SmartAssignmentChecker/ application folder.
"""

APP_NAME = "Smart Assignment Checker"
LAUNCHER = "SmartAssignmentChecker.exe"
APP_FOLDER_NAME = "SmartAssignmentChecker"
PACKAGE_ZIPS = ["SmartAssignmentChecker-App.zip", "SmartAssignmentChecker-Source.zip"]

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")


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
    SUCCESS = "#22C55E"
    DANGER = "#EF4444"


class Fonts:
    FAMILY = "Segoe UI Variable, Segoe UI, Inter, -apple-system, Arial, sans-serif"
    SIZE_H1 = 20
    SIZE_H2 = 15
    SIZE_BODY = 12
    SIZE_SMALL = 10


class Radius:
    MD = 8
    LG = 12


def _get_check_icon_path() -> str:
    """Returns a temporary path to a clean SVG checkmark for checkboxes."""
    icon_path = os.path.join(tempfile.gettempdir(), "sac_check_icon.svg")
    svg_content = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" '
        'viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="3" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="20 6 9 17 4 12"></polyline></svg>'
    )
    try:
        with open(icon_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
    except Exception:
        pass
    return icon_path.replace("\\", "/")


# ----------------------------------------------------------------------
# Locate the installable package
# ----------------------------------------------------------------------
def resolve_package_path():
    """Locate the installable package: the zip, or a ready-made app folder."""
    search_dirs = []
    if hasattr(sys, "_MEIPASS"):
        search_dirs.append(sys._MEIPASS)
    search_dirs.append(PROJECT_ROOT)
    search_dirs.append(DIST_DIR)
    search_dirs.append(os.getcwd())

    seen = set()
    for d in search_dirs:
        if d in seen:
            continue
        seen.add(d)
        for pkg_name in PACKAGE_ZIPS:
            candidate = os.path.join(d, pkg_name)
            if os.path.isfile(candidate):
                return candidate

    for d in search_dirs:
        if d in seen:
            continue
        seen.add(d)
        folder = os.path.join(d, APP_FOLDER_NAME)
        if os.path.isfile(os.path.join(folder, LAUNCHER)) or os.path.isfile(os.path.join(folder, "main.py")):
            return folder
    return None


# ----------------------------------------------------------------------
# Background installation thread
# ----------------------------------------------------------------------
class InstallWorker(QThread):
    progress_updated = Signal(int)
    status_updated = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, source, dest_dir):
        super().__init__()
        self.source = source
        self.dest_dir = dest_dir

    def _run_copy_folder(self):
        items = os.listdir(self.source)
        total = len(items)
        for i, name in enumerate(items):
            src = os.path.join(self.source, name)
            dst = os.path.join(self.dest_dir, name)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
            percent = int(((i + 1) / total) * 100)
            self.progress_updated.emit(percent)
            self.status_updated.emit(f"Copying: {name}")
        self.finished.emit(True, "Success")

    def run(self):
        try:
            os.makedirs(self.dest_dir, exist_ok=True)

            if os.path.isdir(self.source):
                self._run_copy_folder()
                return

            if not os.path.isfile(self.source):
                self.finished.emit(False, f"Package not found: {self.source}")
                return

            with zipfile.ZipFile(self.source, "r") as zip_ref:
                all_files = zip_ref.infolist()
                total_files = len(all_files)
                if total_files == 0:
                    self.finished.emit(False, "Package is empty.")
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
# Setup wizard
# ----------------------------------------------------------------------
class SetupWizard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — Setup")
        self.setFixedSize(580, 450)

        self.package_source = resolve_package_path()
        check_icon = _get_check_icon_path()

        local_app_data = os.getenv("LOCALAPPDATA", os.path.expanduser("~"))
        self.install_dir = os.path.join(local_app_data, APP_FOLDER_NAME)

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
                padding: 10px 22px;
                font-size: {Fonts.SIZE_BODY}px;
                font-weight: 600;
            }}
            QPushButton#PrimaryButton:hover {{
                background-color: {Colors.ACCENT_HOVER};
            }}
            QPushButton#PrimaryButton:pressed {{
                background-color: {Colors.ACCENT_PRESSED};
            }}
            QPushButton#PrimaryButton:disabled {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_MUTED};
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
                spacing: 10px;
                font-size: {Fonts.SIZE_BODY}px;
                color: {Colors.TEXT_PRIMARY};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1.5px solid {Colors.BORDER_LIGHT};
                border-radius: 4px;
                background-color: {Colors.BG_SURFACE};
            }}
            QCheckBox::indicator:hover {{
                border-color: {Colors.ACCENT};
            }}
            QCheckBox::indicator:checked {{
                background-color: {Colors.ACCENT};
                border-color: {Colors.ACCENT};
                image: url("{check_icon}");
            }}
        """)

        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(30, 30, 30, 30)

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

        self.title_label = QLabel(APP_NAME)
        self.title_label.setStyleSheet(f"font-size: {Fonts.SIZE_H1}px; font-weight: 700;")
        self.header_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("Setup Wizard")
        self.subtitle_label.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_SECONDARY};")
        self.header_layout.addWidget(self.subtitle_label)

        self.main_layout.addWidget(self.header_card)
        self.main_layout.addSpacing(20)

        self.pages = QStackedWidget()
        self.main_layout.addWidget(self.pages)

        self._setup_page_welcome()
        self._setup_page_dir()
        self._setup_page_installing()
        self._setup_page_finished()

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

        self._show_package_status()

    # ------------------------------------------------------------------
    def _setup_page_welcome(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        desc = QLabel(
            "This setup will install the Smart Assignment Cross-Checking App on your "
            "computer.\n\n"
            "The similarity analysis engine, reports, PDF exporter, and modern interface will "
            "be installed into a single folder with the executable and all supporting files."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.TEXT_SECONDARY}; line-height: 1.4;")
        layout.addWidget(desc)

        self.lbl_package = QLabel("")
        self.lbl_package.setWordWrap(True)
        self.lbl_package.setStyleSheet(f"font-size: {Fonts.SIZE_SMALL}px; color: {Colors.TEXT_MUTED};")
        layout.addWidget(self.lbl_package)

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

        lbl_space = QLabel("All application files (executable + folders) are installed inside this single folder.")
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
        self.progress_bar.setRange(0, 100)
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
        self.lbl_finish_status.setStyleSheet(
            f"font-size: {Fonts.SIZE_H2}px; font-weight: 700; color: {Colors.SUCCESS};"
        )
        layout.addWidget(self.lbl_finish_status)

        self.lbl_finish_detail = QLabel("")
        self.lbl_finish_detail.setWordWrap(True)
        self.lbl_finish_detail.setStyleSheet(f"font-size: {Fonts.SIZE_SMALL}px; color: {Colors.TEXT_MUTED};")
        layout.addWidget(self.lbl_finish_detail)

        self.chk_shortcut = QCheckBox("Create Desktop Shortcut")
        self.chk_shortcut.setChecked(True)
        layout.addWidget(self.chk_shortcut)

        self.chk_launch = QCheckBox("Launch after closing setup")
        self.chk_launch.setChecked(True)
        layout.addWidget(self.chk_launch)
        layout.addStretch()

        self.pages.addWidget(page)

    # ------------------------------------------------------------------
    def _show_package_status(self):
        if self.package_source:
            self.lbl_package.setText("The application is ready to install.")
        else:
            self.lbl_package.setText(
                "The application package was not found in this setup. "
                "This setup file may be damaged or incomplete."
            )
            self.btn_next.setEnabled(False)

    def _on_dir_changed(self, text):
        self.install_dir = text.strip()

    def _browse_dir(self):
        selected = QFileDialog.getExistingDirectory(self, "Select Installation Folder", self.install_dir)
        if selected:
            self.dir_input.setText(selected)

    def _next_page(self):
        curr = self.pages.currentIndex()
        if curr == 0:
            self.pages.setCurrentIndex(1)
            self.btn_back.setVisible(True)
        elif curr == 1:
            self.pages.setCurrentIndex(2)
            self.btn_back.setVisible(False)
            self.btn_next.setVisible(False)
            self._start_installation()
        elif curr == 3:
            self._finalize_installation()

    def _prev_page(self):
        curr = self.pages.currentIndex()
        if curr == 1:
            self.pages.setCurrentIndex(0)
            self.btn_back.setVisible(False)

    # ------------------------------------------------------------------
    def update_progress(self, value):
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(value)

    def update_status(self, text):
        self.lbl_detail.setText(text)

    @Slot(bool, str)
    def _on_install_finished(self, success, message):
        if success:
            self.lbl_finish_detail.setText(f"Installed to:\n{self.install_dir}")
            self.pages.setCurrentIndex(3)
            self.btn_next.setText("Finish")
            self.btn_next.setVisible(True)
        else:
            self.lbl_status.setText("Installation failed.")
            self.lbl_status.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.DANGER};")
            self.lbl_detail.setText(message)
            self.btn_next.setText("Close")
            self.btn_next.setVisible(True)
            self.btn_next.clicked.disconnect()
            self.btn_next.clicked.connect(self.close)

    def _start_installation(self):
        source = self.package_source or resolve_package_path()
        if not source:
            self.lbl_status.setText("Installation failed.")
            self.lbl_status.setStyleSheet(f"font-size: {Fonts.SIZE_BODY}px; color: {Colors.DANGER};")
            self.lbl_detail.setText("Could not locate the application package.")
            return

        self.lbl_status.setText("Installing application files...")
        self.worker = InstallWorker(source, self.install_dir)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.status_updated.connect(self.update_status)
        self.worker.finished.connect(self._on_install_finished)
        self.worker.start()

    def _finalize_installation(self):
        launcher = os.path.join(self.install_dir, LAUNCHER)
        main_py = os.path.join(self.install_dir, "main.py")

        target_exec = launcher if os.path.isfile(launcher) else None

        if self.chk_shortcut.isChecked() and target_exec:
            try:
                ps_cmd = f"""
                $WshShell = New-Object -ComObject WScript.Shell
                
                # Desktop shortcut
                $DesktopPath = [System.IO.Path]::Combine([System.Environment]::GetFolderPath('Desktop'), '{APP_NAME}.lnk')
                $Shortcut = $WshShell.CreateShortcut($DesktopPath)
                $Shortcut.TargetPath = '{target_exec}'
                $Shortcut.WorkingDirectory = '{self.install_dir}'
                $Shortcut.IconLocation = '{target_exec},0'
                $Shortcut.Save()

                # Start Menu shortcut
                $StartMenuDir = [System.IO.Path]::Combine([System.Environment]::GetFolderPath('Programs'), '{APP_NAME}')
                if (-not (Test-Path $StartMenuDir)) {{ New-Item -ItemType Directory -Path $StartMenuDir -Force | Out-Null }}
                $StartMenuPath = [System.IO.Path]::Combine($StartMenuDir, '{APP_NAME}.lnk')
                $StartShortcut = $WshShell.CreateShortcut($StartMenuPath)
                $StartShortcut.TargetPath = '{target_exec}'
                $StartShortcut.WorkingDirectory = '{self.install_dir}'
                $StartShortcut.IconLocation = '{target_exec},0'
                $StartShortcut.Save()
                """
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps_cmd],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
                )
            except Exception as e:
                print(f"Failed to create shortcuts: {e}")

        if self.chk_launch.isChecked():
            if target_exec and os.path.isfile(target_exec):
                try:
                    if hasattr(os, "startfile"):
                        os.startfile(target_exec)
                    else:
                        subprocess.Popen(
                            [target_exec],
                            cwd=self.install_dir,
                            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
                        )
                except Exception as e:
                    print(f"Failed to launch application: {e}")
            elif os.path.isfile(main_py):
                try:
                    for interp in ("pythonw", "python", "py"):
                        if shutil.which(interp):
                            subprocess.Popen(
                                [shutil.which(interp), main_py],
                                cwd=self.install_dir,
                                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
                            )
                            break
                except Exception as e:
                    print(f"Failed to launch main.py: {e}")

        self.close()
        QApplication.quit()


def main():
    app = QApplication(sys.argv)
    wizard = SetupWizard()
    wizard.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()