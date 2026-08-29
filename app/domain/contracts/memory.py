from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class MemoryRecord:
    id: str
    content: str
    memory_type: str = "general"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("MemoryRecord id must not be empty")
        if not self.content.strip():
            raise ValueError("MemoryRecord content must not be empty")
        if not self.memory_type.strip():
            raise ValueError("MemoryRecord memory_type must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "metadata": dict(self.metadata),
            "created_at": self.created_at.isoformat(),
        }
