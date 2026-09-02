from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    handler: Callable[..., Any]
    risk_level: str = "low"
    requires_approval: bool = False

    def execute(self, **kwargs: Any) -> Any:
        return self.handler(**kwargs)
