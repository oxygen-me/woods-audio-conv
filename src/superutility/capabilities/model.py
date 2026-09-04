from dataclasses import dataclass
from enum import Enum

class CapabilityStatus(str, Enum):
    SUPPORTED = "supported"
    SUPPORTED_WITH_WARNING = "supported_with_warning"
    REQUIRES_PROCESSING = "requires_processing"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"

@dataclass(frozen=True, slots=True)
class CapabilityResult:
    status: CapabilityStatus
    reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
