from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QFrame, QMessageBox, QComboBox
)

from app.paths import APP_NAME, history_db_path
from operations.inspection import InspectionService
from operations.conversion import make_remux, make_transcode
from jobs.manager import JobManager
from storage.database import HistoryDatabase

class DropZone(QFrame):
    file_dropped = __import__("PySide6.QtCore", fromlist=["Signal"]).Signal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumHeight(150)
        layout = QVBoxLayout(self)
        self.label = QLabel("Drop a media file here\nor click Browse")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.file_dropped.emit("")
        super().mousePressEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            self.file_dropped.emit(urls[0].toLocalFile())
            event.acceptProposedAction()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} 0.1.0")
        self.resize(980, 700)
        self.current_media = None
        self.current_path = None
        self.inspector = InspectionService()
        self.jobs = JobManager()
        self.history = HistoryDatabase(history_db_path())

        self.jobs.message.connect(self._set_status)
        self.jobs.completed.connect(self._job_completed)
        self.jobs.failed.connect(self._job_failed)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        title = QLabel("Multimedia Superutility")
        title.setStyleSheet("font-size: 26px; font-weight: 600;")
        root.addWidget(title)

        subtitle = QLabel("Local-first. No account. No bullshit.")
        root.addWidget(subtitle)

        self.drop = DropZone()
        self.drop.file_dropped.connect(self._select_file)
        root.addWidget(self.drop)

        buttons = QHBoxLayout()
        browse = QPushButton("Browse…")
        browse.clicked.connect(lambda: self._select_file(""))
        buttons.addWidget(browse)

        self.inspect_button = QPushButton("Inspect")
        self.inspect_button.clicked.connect(self._inspect)
        self.inspect_button.setEnabled(False)
        buttons.addWidget(self.inspect_button)

        self.convert_button = QPushButton("Convert to…")
        self.convert_button.clicked.connect(self._convert)
        self.convert_button.setEnabled(False)
        buttons.addWidget(self.convert_button)
        root.addLayout(buttons)

        self.format_box = QComboBox()
        self.format_box.addItems(["MP4 (H.264/AAC)", "MKV (stream copy/remux)", "WebM (VP9/Opus)"])
        self.format_box.setEnabled(False)
        root.addWidget(self.format_box)

        self.info = QLabel("Nothing loaded.")
        self.info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.info.setWordWrap(True)
        self.info.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        root.addWidget(self.info, 1)

        self.status = QLabel("Ready.")
        root.addWidget(self.status)

    def _select_file(self, path: str):
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Choose media")
        if not path:
            return
        self.current_path = Path(path)
        self.current_media = None
        self.info.setText(f"Selected:\n{self.current_path}")
        self.inspect_button.setEnabled(True)
        self.convert_button.setEnabled(False)
        self.format_box.setEnabled(False)

    def _inspect(self):
        if not self.current_path:
            return
        try:
            self._set_status("Inspecting with ffprobe…")
            media = self.inspector.inspect(self.current_path)
            self.current_media = media
            lines = [
                f"File: {media.filename}",
                f"Size: {media.size:,} bytes",
                f"Container: {media.format_name or 'unknown'}",
                f"Duration: {media.duration:.3f}s" if media.duration is not None else "Duration: unknown",
                f"Bitrate: {media.bitrate:,} bit/s" if media.bitrate else "Bitrate: unknown",
                "",
                f"Streams: {len(media.streams)}",
            ]
            for s in media.streams:
                detail = f"#{s.index} {s.kind}: {s.codec or 'unknown'}"
                if getattr(s, "width", None):
                    detail += f" {s.width}x{s.height}"
                if getattr(s, "sample_rate", None):
                    detail += f" {s.sample_rate} Hz"
                lines.append(detail)
            self.info.setText("\n".join(lines))
            self.convert_button.setEnabled(True)
            self.format_box.setEnabled(True)
            self._set_status("Inspection complete.")
        except Exception as exc:
            self._show_error("Inspection failed", str(exc))

    def _convert(self):
        if not self.current_path:
            return
        suffixes = [".mp4", ".mkv", ".webm"]
        idx = self.format_box.currentIndex()
        suffix = suffixes[idx]
        output = self.current_path.with_name(
            f"{self.current_path.stem}.converted{suffix}"
        )
        if output.exists():
            answer = QMessageBox.question(
                self, "Output exists",
                f"{output.name} already exists.\n\nReplace it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return

        if idx == 1:
            operation = make_remux(self.current_path, output)
        elif idx == 2:
            operation = make_transcode(
                self.current_path, output,
                video_codec="libvpx-vp9",
                audio_codec="libopus",
            )
        else:
            operation = make_transcode(
                self.current_path, output,
                video_codec="libx264",
                audio_codec="aac",
            )

        self.convert_button.setEnabled(False)
        self._set_status(f"Starting job → {output.name}")
        job = self.jobs.start(operation)
        self._active_job = job

    def _job_completed(self, result):
        self.convert_button.setEnabled(True)
        self._set_status(f"Completed: {result.path.name}")
        self.history.record(
            getattr(self._active_job, "created_at", ""),
            "media-conversion",
            self._active_job.input_path,
            self._active_job.output_path,
            "completed",
            result.reason,
        )
        QMessageBox.information(self, "Done", f"Created:\n{result.path}")

    def _job_failed(self, message):
        self.convert_button.setEnabled(True)
        self._set_status("Job failed.")
        if hasattr(self, "_active_job"):
            self.history.record(
                self._active_job.created_at,
                "media-conversion",
                self._active_job.input_path,
                self._active_job.output_path,
                "failed",
                message,
            )
        self._show_error("Conversion failed", message)

    def _set_status(self, text: str):
        self.status.setText(text)

    def _show_error(self, title: str, message: str):
        self._set_status(message)
        QMessageBox.critical(self, title, message)
