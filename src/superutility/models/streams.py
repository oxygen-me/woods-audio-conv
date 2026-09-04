from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True, slots=True)
class Stream:
    index: int
    kind: str
    codec: str | None = None
    codec_id: str | None = None
    profile: str | None = None
    bitrate: int | None = None
    duration: float | None = None
    language: str | None = None
    title: str | None = None
    disposition: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class VideoStream(Stream):
    width: int | None = None
    height: int | None = None
    pixel_format: str | None = None
    fps: float | None = None

@dataclass(frozen=True, slots=True)
class AudioStream(Stream):
    sample_rate: int | None = None
    channels: int | None = None
    channel_layout: str | None = None
    sample_format: str | None = None
