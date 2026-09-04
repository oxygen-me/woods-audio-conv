from dataclasses import dataclass
from ..models.operations import Operation, Remux, TranscodeVideo

@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    operation_id: str
    description: str
    steps: tuple[str, ...]

class Planner:
    def plan(self, operation: Operation) -> ExecutionPlan:
        if isinstance(operation, Remux):
            return ExecutionPlan(
                operation.operation_id,
                "Copy existing streams into a new container.",
                ("open input", "copy streams", "mux", "write temporary output", "validate", "commit"),
            )
        if isinstance(operation, TranscodeVideo):
            return ExecutionPlan(
                operation.operation_id,
                "Decode/process/encode selected media streams.",
                ("open input", "select streams", "decode", "encode", "mux", "write temporary output", "validate", "commit"),
            )
        raise ValueError(f"Unsupported operation: {type(operation).__name__}")
