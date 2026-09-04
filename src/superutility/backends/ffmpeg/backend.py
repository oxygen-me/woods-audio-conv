from pathlib import Path
from backends.ffmpeg.translator import FFmpegTranslator
from app.paths import ffmpeg_path

class FFmpegBackend:
    def __init__(self, executable: Path | None = None):
        self.executable = executable or ffmpeg_path()
        self.translator = FFmpegTranslator()

    def build_args(self, operation) -> list[str]:
        return self.translator.translate(operation)

    def command(self, operation) -> list[str]:
        return [str(self.executable), *self.build_args(operation)]
