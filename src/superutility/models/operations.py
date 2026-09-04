from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

class StreamMode(str, Enum):
    AUTO = "auto"
    COPY = "copy"
    ENCODE = "encode"

@dataclass(frozen=True, slots=True)
class Operation:
    operation_id: str
    input_path: Path
    output_path: Path
    overwrite: bool = False

@dataclass(frozen=True, slots=True)
class TranscodeVideo(Operation):
    video_codec: str | None = None
    audio_codec: str | None = None
    stream_mode: StreamMode = StreamMode.AUTO
    extra_args: tuple[str, ...] = field(default_factory=tuple)

@dataclass(frozen=True, slots=True)
class Remux(Operation):
    extra_args: tuple[str, ...] = field(default_factory=tuple)
