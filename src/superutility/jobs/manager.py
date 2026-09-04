import uuid
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QThread

from backends.ffmpeg.backend import FFmpegBackend
from execution.process import ProcessRunner
from models.jobs import Job, JobState
from models.results import ValidationResult

class JobWorker(QThread):
    progress_message = Signal(str)
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, operation):
        super().__init__()
        self.operation = operation
        self.backend = FFmpegBackend()
        self.runner = ProcessRunner()

    def run(self):
        try:
            if not self.backend.executable.exists():
                raise FileNotFoundError(f"ffmpeg.exe not found: {self.backend.executable}")
            self.progress_message.emit("Running FFmpeg…")
            result = self.runner.run(self.backend.command(self.operation))
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or f"FFmpeg exited with code {result.returncode}")
            output = Path(self.operation.output_path)
            if not output.exists() or output.stat().st_size == 0:
                raise RuntimeError("FFmpeg reported success, but the output was not valid.")
            self.finished_ok.emit(
                ValidationResult(True, output, "Output exists and is non-empty.")
            )
        except Exception as exc:
            self.failed.emit(str(exc))

class JobManager(QObject):
    message = Signal(str)
    completed = Signal(object)
    failed = Signal(str)

    def start(self, operation) -> Job:
        job = Job.create(
            str(uuid.uuid4()),
            Path(operation.input_path),
            Path(operation.output_path),
        )
        worker = JobWorker(operation)
        worker.progress_message.connect(self.message)
        worker.finished_ok.connect(self.completed)
        worker.failed.connect(self.failed)
        worker.finished.connect(worker.deleteLater)
        worker.start()
        self._worker = worker
        return job
