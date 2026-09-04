from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True, slots=True)
class ValidationResult:
    valid: bool
    path: Path
    reason: str = ""
