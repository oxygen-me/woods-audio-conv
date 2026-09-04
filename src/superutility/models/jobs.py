from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from datetime import datetime, timezone

class JobState(str, Enum):
    QUEUED = "queued"
    PREPARING = "preparing"
    RUNNING = "running"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"

@dataclass
class Job:
    job_id: str
    state: JobState
    input_path: Path
    output_path: Path
    created_at: str
    progress: float | None = None
    message: str = ""

    @classmethod
    def create(cls, job_id: str, input_path: Path, output_path: Path) -> "Job":
        return cls(
            job_id=job_id,
            state=JobState.QUEUED,
            input_path=input_path,
            output_path=output_path,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
