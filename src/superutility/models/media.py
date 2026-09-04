from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .streams import Stream

@dataclass(frozen=True, slots=True)
class MediaFile:
    path: Path
    size: int
    format_name: str | None
    format_long_name: str | None
    duration: float | None
    bitrate: int | None
    streams: tuple[Stream, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)
    probe_warnings: tuple[str, ...] = ()

    @property
    def filename(self) -> str:
        return self.path.name

    @property
    def video_streams(self) -> tuple[Stream, ...]:
        return tuple(s for s in self.streams if s.kind == "video")

    @property
    def audio_streams(self) -> tuple[Stream, ...]:
        return tuple(s for s in self.streams if s.kind == "audio")
