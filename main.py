import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QComboBox,
    QProgressBar,
    QMessageBox,
    QFrame,
    QSpinBox,
    QCheckBox,
    QAbstractItemView,
)

# FFmpeg is supplied by the imageio-ffmpeg Python package.
# This avoids requiring the user to install FFmpeg manually.
try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None


SUPPORTED_INPUTS = {
    ".mp3", ".wav", ".flac", ".ogg", ".oga", ".opus",
    ".aac", ".m4a", ".mp4", ".aiff", ".aif", ".wma",
}

FORMAT_OPTIONS = {
    "MP3": {"extension": ".mp3", "codec": "libmp3lame"},
    "WAV": {"extension": ".wav", "codec": "pcm_s16le"},
    "FLAC": {"extension": ".flac", "codec": "flac"},
    "OGG Vorbis": {"extension": ".ogg", "codec": "libvorbis"},
    "Opus": {"extension": ".opus", "codec": "libopus"},
    "AAC / M4A": {"extension": ".m4a", "codec": "aac"},
    "AIFF": {"extension": ".aiff", "codec": "pcm_s16be"},
}


def get_ffmpeg():
    """Return the FFmpeg executable bundled by imageio-ffmpeg."""
    if imageio_ffmpeg is None:
        return None

    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def unique_output_path(path: Path) -> Path:
    if not path.exists():
        return path

    for counter in range(1, 10000):
        candidate = path.with_name(
            f"{path.stem} ({counter}){path.suffix}"
        )
        if not candidate.exists():
            return candidate

    raise RuntimeError("Could not create a unique output filename.")


class ConverterWorker(QObject):
    progress = Signal(int)
    current_file = Signal(str)
    finished_file = Signal(str)
    error = Signal(str)
    finished = Signal()
    cancelled = Signal()

    def __init__(self, files, output_directory, output_format, bitrate, overwrite):
        super().__init__()
        self.files = files
        self.output_directory = output_directory
        self.output_format = output_format
        self.bitrate = bitrate
        self.overwrite = overwrite
        self._cancel_requested = False

    def cancel(self):
        self._cancel_requested = True

    def run(self):
        ffmpeg = get_ffmpeg()

        if not ffmpeg:
            self.error.emit(
                "The bundled FFmpeg engine could not be found.\n\n"
                "Install the imageio-ffmpeg package and try again."
            )
            self.finished.emit()
            return

        info = FORMAT_OPTIONS[self.output_format]
        extension = info["extension"]
        codec = info["codec"]
        total = len(self.files)

        for index, input_file in enumerate(self.files):
            if self._cancel_requested:
                self.cancelled.emit()
                return

            input_path = Path(input_file)
            output_path = Path(self.output_directory) / (
                input_path.stem + extension
            )

            if not self.overwrite:
                output_path = unique_output_path(output_path)

            self.current_file.emit(input_path.name)

            command = [
                ffmpeg,
                "-y" if self.overwrite else "-n",
                "-i", str(input_path),
                "-vn",
                "-map_metadata", "0",
                "-c:a", codec,
            ]

            if self.output_format in {"MP3", "OGG Vorbis", "Opus", "AAC / M4A"}:
                command += ["-b:a", f"{self.bitrate}k"]

            command.append(str(output_path))

            try:
                process = __import__("subprocess").Popen(
                    command,
                    stdout=__import__("subprocess").PIPE,
                    stderr=__import__("subprocess").PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )

                _, stderr = process.communicate()

                if self._cancel_requested:
                    try:
                        process.kill()
                    except Exception:
                        pass

                    if output_path.exists():
                        try:
                            output_path.unlink()
                        except OSError:
                            pass

                    self.cancelled.emit()
                    return

                if process.returncode != 0:
                    message = stderr.strip()
                    if len(message) > 1400:
                        message = message[-1400:]
                    self.error.emit(f"{input_path.name}\n\n{message}")
                else:
                    self.finished_file.emit(str(output_path))

            except Exception as exc:
                self.error.emit(f"{input_path.name}\n\n{exc}")

            self.progress.emit(int(((index + 1) / total) * 100))

        self.finished.emit()


class AudioConverter(QMainWindow):
    def __init__(self):
        super().__init__()

        self.files = []
        self.worker = None
        self.thread = None

        self.setWindowTitle("piss.io")
        self.resize(1050, 720)
        self.setAcceptDrops(True)

        self.build_ui()
        self.apply_stylesheet()
        self.check_ffmpeg()

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main = QVBoxLayout(central)
        main.setContentsMargins(28, 24, 28, 24)
        main.setSpacing(18)

        # Header
        header = QHBoxLayout()
        title_layout = QVBoxLayout()

        title = QLabel("piss.io")
        title.setObjectName("title")

        subtitle = QLabel("Fast, simple batch audio conversion")
        subtitle.setObjectName("subtitle")

        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)

        header.addLayout(title_layout)
        header.addStretch()

        self.ffmpeg_label = QLabel("● FFmpeg Ready")
        self.ffmpeg_label.setObjectName("ffmpegStatus")
        header.addWidget(self.ffmpeg_label)

        main.addLayout(header)

        # Drop area
        self.drop_area = QFrame()
        self.drop_area.setObjectName("dropArea")
        self.drop_area.setMinimumHeight(130)

        drop_layout = QVBoxLayout(self.drop_area)
        drop_layout.setAlignment(Qt.AlignCenter)

        drop_title = QLabel("Drop audio files here")
        drop_title.setObjectName("dropTitle")
        drop_title.setAlignment(Qt.AlignCenter)

        drop_hint = QLabel("or use the Add Files button below")
        drop_hint.setObjectName("dropHint")
        drop_hint.setAlignment(Qt.AlignCenter)

        drop_layout.addWidget(drop_title)
        drop_layout.addWidget(drop_hint)
        main.addWidget(self.drop_area)

        # Files
        files_header = QHBoxLayout()

        files_label = QLabel("Files")
        files_label.setObjectName("sectionTitle")

        self.file_count = QLabel("0 files")
        self.file_count.setObjectName("fileCount")

        files_header.addWidget(files_label)
        files_header.addWidget(self.file_count)
        files_header.addStretch()

        self.add_button = QPushButton("+  Add Files")
        self.add_button.clicked.connect(self.add_files)

        self.remove_button = QPushButton("Remove Selected")
        self.remove_button.clicked.connect(self.remove_selected)

        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_files)

        files_header.addWidget(self.add_button)
        files_header.addWidget(self.remove_button)
        files_header.addWidget(self.clear_button)

        main.addLayout(files_header)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        main.addWidget(self.file_list, 1)

        # Settings
        settings = QFrame()
        settings.setObjectName("settingsFrame")
        settings_layout = QHBoxLayout(settings)
        settings_layout.setContentsMargins(18, 15, 18, 15)

        format_layout = QVBoxLayout()
        format_label = QLabel("Output Format")
        format_label.setObjectName("smallLabel")

        self.format_combo = QComboBox()
        self.format_combo.addItems(FORMAT_OPTIONS.keys())

        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        settings_layout.addLayout(format_layout)

        bitrate_layout = QVBoxLayout()
        bitrate_label = QLabel("Bitrate")
        bitrate_label.setObjectName("smallLabel")

        self.bitrate_spin = QSpinBox()
        self.bitrate_spin.setRange(32, 512)
        self.bitrate_spin.setSingleStep(32)
        self.bitrate_spin.setValue(192)
        self.bitrate_spin.setSuffix(" kbps")

        bitrate_layout.addWidget(bitrate_label)
        bitrate_layout.addWidget(self.bitrate_spin)
        settings_layout.addLayout(bitrate_layout)

        output_layout = QVBoxLayout()
        output_label = QLabel("Output Folder")
        output_label.setObjectName("smallLabel")

        output_row = QHBoxLayout()

        self.output_path = QLabel(str(Path.home() / "Music"))
        self.output_path.setObjectName("pathLabel")
        self.output_path.setMinimumWidth(250)

        self.output_button = QPushButton("Browse")
        self.output_button.clicked.connect(self.choose_output_folder)

        output_row.addWidget(self.output_path)
        output_row.addWidget(self.output_button)

        output_layout.addWidget(output_label)
        output_layout.addLayout(output_row)
        settings_layout.addLayout(output_layout, 1)

        self.no_overwrite = QCheckBox("Don't overwrite")
        self.no_overwrite.setChecked(True)
        settings_layout.addWidget(self.no_overwrite)

        main.addWidget(settings)

        # Progress
        progress_layout = QVBoxLayout()

        self.current_label = QLabel("Ready to convert")
        self.current_label.setObjectName("currentLabel")

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)

        progress_layout.addWidget(self.current_label)
        progress_layout.addWidget(self.progress_bar)
        main.addLayout(progress_layout)

        # Bottom
        bottom = QHBoxLayout()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_conversion)

        self.convert_button = QPushButton("Convert Audio")
        self.convert_button.setObjectName("convertButton")
        self.convert_button.clicked.connect(self.start_conversion)

        bottom.addWidget(self.cancel_button)
        bottom.addStretch()
        bottom.addWidget(self.convert_button)

        main.addLayout(bottom)

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QWidget {
                background: #111318;
                color: #e8eaf0;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 14px;
            }

            QLabel {
                background: transparent;
            }

            QLabel#title {
                font-size: 32px;
                font-weight: 700;
                color: #ffffff;
            }

            QLabel#subtitle {
                color: #858b9b;
                font-size: 14px;
            }

            QLabel#ffmpegStatus {
                color: #65d391;
                font-weight: 600;
                padding: 0;
            }

            QFrame#dropArea {
                background: #151820;
                border: 2px dashed #343947;
                border-radius: 16px;
            }

            QFrame#dropArea:hover {
                border-color: #6572ff;
                background: #181b25;
            }

            QLabel#dropTitle {
                font-size: 19px;
                font-weight: 600;
                color: #ffffff;
            }

            QLabel#dropHint {
                color: #747b8c;
                margin-top: 6px;
            }

            QLabel#sectionTitle {
                font-size: 17px;
                font-weight: 600;
            }

            QLabel#fileCount {
                color: #747b8c;
                margin-left: 8px;
            }

            QListWidget {
                background: #151820;
                border: 1px solid #272b35;
                border-radius: 12px;
                padding: 6px;
                outline: none;
            }

            QListWidget::item {
                padding: 11px;
                border-radius: 8px;
            }

            QListWidget::item:hover {
                background: #1d212c;
            }

            QListWidget::item:selected {
                background: #30375c;
                color: #ffffff;
            }

            QFrame#settingsFrame {
                background: #151820;
                border: 1px solid #272b35;
                border-radius: 12px;
            }

            QLabel#smallLabel {
                color: #858b9b;
                font-size: 12px;
                margin-bottom: 4px;
            }

            QLabel#pathLabel {
                color: #aeb3c0;
                padding: 0;
            }

            QComboBox,
            QSpinBox {
                background: #101218;
                border: 1px solid #303541;
                border-radius: 7px;
                padding: 8px 10px;
                min-height: 18px;
            }

            QComboBox:hover,
            QSpinBox:hover {
                border-color: #50586d;
            }

            QComboBox::drop-down {
                border: none;
                width: 28px;
            }

            QPushButton {
                background: #20242e;
                border: 1px solid #303541;
                border-radius: 8px;
                padding: 9px 15px;
                color: #e6e8ee;
                font-weight: 500;
            }

            QPushButton:hover {
                background: #292e3a;
                border-color: #4b5365;
            }

            QPushButton:pressed {
                background: #181b23;
            }

            QPushButton:disabled {
                color: #555b68;
                background: #191c23;
            }

            QPushButton#convertButton {
                background: #6672ff;
                border: none;
                color: white;
                font-size: 15px;
                font-weight: 700;
                padding: 12px 27px;
                border-radius: 9px;
            }

            QPushButton#convertButton:hover {
                background: #7782ff;
            }

            QProgressBar {
                background: #191c23;
                border: none;
                border-radius: 6px;
                height: 10px;
                text-align: center;
            }

            QProgressBar::chunk {
                background: #6672ff;
                border-radius: 6px;
            }

            QLabel#currentLabel {
                color: #858b9b;
                font-size: 12px;
                margin-bottom: 4px;
            }

            QCheckBox {
                background: transparent;
                color: #aeb3c0;
                spacing: 8px;
            }

            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid #444a58;
                background: #101218;
            }

            QCheckBox::indicator:checked {
                background: #6672ff;
                border-color: #6672ff;
            }
        """)

    def check_ffmpeg(self):
        if get_ffmpeg():
            self.ffmpeg_label.setText("● FFmpeg Ready")
            self.ffmpeg_label.setStyleSheet(
                "color: #65d391; background: transparent; font-weight: 600;"
            )
        else:
            self.ffmpeg_label.setText("● FFmpeg Engine Missing")
            self.ffmpeg_label.setStyleSheet(
                "color: #ff7474; background: transparent; font-weight: 600;"
            )

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = []

        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue

            path = Path(url.toLocalFile())

            if path.is_file():
                paths.append(path)
            elif path.is_dir():
                paths.extend(
                    child for child in path.iterdir()
                    if child.is_file()
                    and child.suffix.lower() in SUPPORTED_INPUTS
                )

        self.add_paths(paths)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Audio Files",
            str(Path.home()),
            (
                "Audio Files (*.mp3 *.wav *.flac *.ogg *.oga *.opus "
                "*.aac *.m4a *.mp4 *.aiff *.aif *.wma);;"
                "All Files (*)"
            ),
        )

        if files:
            self.add_paths([Path(file) for file in files])

    def add_paths(self, paths):
        existing = {str(Path(file).resolve()) for file in self.files}

        for path in paths:
            if path.suffix.lower() not in SUPPORTED_INPUTS:
                continue

            resolved = str(path.resolve())

            if resolved in existing:
                continue

            self.files.append(str(path))
            existing.add(resolved)

            item = QListWidgetItem(
                f"{path.name}    •    {self.format_size(path)}"
            )
            item.setToolTip(str(path))
            self.file_list.addItem(item)

        self.update_file_count()

    @staticmethod
    def format_size(path):
        try:
            size = path.stat().st_size

            for unit in ("B", "KB", "MB", "GB"):
                if size < 1024:
                    return f"{size:.1f} {unit}"
                size /= 1024

            return f"{size:.1f} TB"
        except OSError:
            return "Unknown size"

    def remove_selected(self):
        rows = sorted(
            {self.file_list.row(item) for item in self.file_list.selectedItems()},
            reverse=True,
        )

        for row in rows:
            self.file_list.takeItem(row)
            self.files.pop(row)

        self.update_file_count()

    def clear_files(self):
        self.files.clear()
        self.file_list.clear()
        self.update_file_count()
        self.progress_bar.setValue(0)
        self.current_label.setText("Ready to convert")

    def update_file_count(self):
        count = len(self.files)
        self.file_count.setText(
            f"{count} file" if count == 1 else f"{count} files"
        )

    def choose_output_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            self.output_path.text(),
        )

        if folder:
            self.output_path.setText(folder)

    def start_conversion(self):
        ffmpeg = get_ffmpeg()

        if not ffmpeg:
            QMessageBox.critical(
                self,
                "FFmpeg Engine Missing",
                "The bundled FFmpeg engine is unavailable.\n\n"
                "Install imageio-ffmpeg with:\n\n"
                "pip install imageio-ffmpeg",
            )
            return

        if not self.files:
            QMessageBox.information(
                self,
                "No Files",
                "Add at least one audio file first.",
            )
            return

        output_directory = Path(self.output_path.text())

        try:
            output_directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Output Folder Error",
                str(exc),
            )
            return

        self.set_controls_enabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)

        self.thread = QThread()
        self.worker = ConverterWorker(
            files=self.files.copy(),
            output_directory=str(output_directory),
            output_format=self.format_combo.currentText(),
            bitrate=self.bitrate_spin.value(),
            overwrite=not self.no_overwrite.isChecked(),
        )

        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.current_file.connect(self.on_current_file)
        self.worker.finished_file.connect(self.on_finished_file)
        self.worker.error.connect(self.on_conversion_error)
        self.worker.finished.connect(self.on_conversion_finished)
        self.worker.cancelled.connect(self.on_conversion_cancelled)

        self.thread.start()

    def set_controls_enabled(self, enabled):
        self.convert_button.setEnabled(enabled)
        self.add_button.setEnabled(enabled)
        self.remove_button.setEnabled(enabled)
        self.clear_button.setEnabled(enabled)
        self.output_button.setEnabled(enabled)
        self.format_combo.setEnabled(enabled)
        self.bitrate_spin.setEnabled(enabled)
        self.no_overwrite.setEnabled(enabled)

    def on_current_file(self, filename):
        self.current_label.setText(f"Converting: {filename}")

    def on_finished_file(self, filename):
        self.current_label.setText(
            f"Converted: {Path(filename).name}"
        )

    def on_conversion_error(self, message):
        QMessageBox.warning(self, "Conversion Error", message)

    def on_conversion_finished(self):
        self.cleanup_thread()
        self.progress_bar.setValue(100)
        self.current_label.setText("Conversion complete")

        QMessageBox.information(
            self,
            "Done",
            "All audio files have been processed.",
        )

    def on_conversion_cancelled(self):
        self.cleanup_thread()
        self.current_label.setText("Conversion cancelled")
        self.progress_bar.setValue(0)

    def cancel_conversion(self):
        if self.worker:
            self.worker.cancel()
            self.current_label.setText("Cancelling...")
            self.cancel_button.setEnabled(False)

    def cleanup_thread(self):
        if self.thread:
            self.thread.quit()
            self.thread.wait()

        self.thread = None
        self.worker = None

        self.set_controls_enabled(True)
        self.cancel_button.setEnabled(False)

    def closeEvent(self, event):
        if self.worker:
            self.worker.cancel()

        if self.thread:
            self.thread.quit()
            self.thread.wait()

        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AudioForge")
    app.setOrganizationName("AudioForge")

    font = QFont("Segoe UI")
    font.setPointSize(10)
    app.setFont(font)

    window = AudioConverter()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
