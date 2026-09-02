from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Department:
    id: str
    name: str
    description: str = ""

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Department id must not be empty")
        if not self.name.strip():
            raise ValueError("Department name must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
        }
