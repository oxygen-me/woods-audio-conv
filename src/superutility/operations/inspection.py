from pathlib import Path
from backends.ffmpeg.ffprobe import FFProbeBackend

class InspectionService:
    def __init__(self, probe: FFProbeBackend | None = None):
        self.probe = probe or FFProbeBackend()

    def inspect(self, path: Path):
        return self.probe.probe(path)
