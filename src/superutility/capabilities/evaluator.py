from ..models.media import MediaFile
from ..models.operations import Operation, Remux, TranscodeVideo
from .model import CapabilityResult, CapabilityStatus

class CapabilityEvaluator:
    def evaluate(self, media: MediaFile, operation: Operation) -> CapabilityResult:
        if isinstance(operation, Remux):
            if not media.format_name:
                return CapabilityResult(CapabilityStatus.UNKNOWN, ("Container format is unknown.",))
            return CapabilityResult(
                CapabilityStatus.SUPPORTED_WITH_WARNING,
                ("Remuxing requires the target container to accept the existing streams.",),
            )

        if isinstance(operation, TranscodeVideo):
            if not media.video_streams:
                return CapabilityResult(
                    CapabilityStatus.UNSUPPORTED,
                    ("No video stream was found in the input.",),
                )
            return CapabilityResult(CapabilityStatus.SUPPORTED)

        return CapabilityResult(CapabilityStatus.UNKNOWN, ("No evaluator exists for this operation yet.",))
