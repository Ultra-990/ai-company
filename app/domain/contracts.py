from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ContractError(ValueError):
    """Raised when a domain contract is invalid."""


class TaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AutonomyLevel(str, Enum):
    A0 = "A0"
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"


@dataclass
class TaskContract:
    id: str
    title: str
    status: TaskStatus = TaskStatus.PENDING
    parent_id: str | None = None
    retry_count: int = 0
    max_retries: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ContractError("task id must not be empty")
        if not self.title.strip():
            raise ContractError("task title must not be empty")
        if self.retry_count < 0:
            raise ContractError("retry_count must not be negative")
        if self.max_retries < 0:
            raise ContractError("max_retries must not be negative")
        if self.retry_count > self.max_retries:
            raise ContractError("retry_count cannot exceed max_retries")

    def transition(self, target: TaskStatus) -> None:
        if not isinstance(target, TaskStatus):
            raise ContractError("target must be a TaskStatus")
        allowed = {
            TaskStatus.PENDING: {TaskStatus.READY, TaskStatus.BLOCKED, TaskStatus.CANCELLED},
            TaskStatus.READY: {TaskStatus.RUNNING, TaskStatus.BLOCKED, TaskStatus.CANCELLED},
            TaskStatus.RUNNING: {TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.BLOCKED, TaskStatus.CANCELLED},
            TaskStatus.BLOCKED: {TaskStatus.READY, TaskStatus.CANCELLED},
            TaskStatus.FAILED: {TaskStatus.READY, TaskStatus.CANCELLED},
            TaskStatus.SUCCEEDED: set(),
            TaskStatus.CANCELLED: set(),
        }
        if target not in allowed[self.status]:
            raise ContractError(f"Invalid task transition: {self.status.value} -> {target.value}")
        self.status = target

    def retry(self) -> None:
        if self.status != TaskStatus.FAILED:
            raise ContractError("Only failed tasks can be retried")
        if self.retry_count >= self.max_retries:
            raise ContractError("Maximum retries exceeded")
        self.retry_count += 1
        self.status = TaskStatus.READY


@dataclass
class ApprovalRequestContract:
    id: str
    subject: str
    requested_by: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    risk: RiskLevel = RiskLevel.MEDIUM
    autonomy: AutonomyLevel = AutonomyLevel.A0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ContractError("approval id must not be empty")
        if not self.subject.strip():
            raise ContractError("approval subject must not be empty")
        if not self.requested_by.strip():
            raise ContractError("requested_by must not be empty")

    def transition(self, target: ApprovalStatus) -> None:
        if not isinstance(target, ApprovalStatus):
            raise ContractError("target must be an ApprovalStatus")
        allowed = {
            ApprovalStatus.PENDING: {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED, ApprovalStatus.EXPIRED},
            ApprovalStatus.APPROVED: {ApprovalStatus.EXPIRED},
            ApprovalStatus.REJECTED: set(),
            ApprovalStatus.EXPIRED: set(),
        }
        if target not in allowed[self.status]:
            raise ContractError(
                f"Invalid approval transition: {self.status.value} -> {target.value}"
            )
        self.status = target


@dataclass
class AgentContract:
    id: str
    name: str
    role: str
    department: str
    autonomy: AutonomyLevel = AutonomyLevel.A0
    active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolContract:
    id: str
    name: str
    risk: RiskLevel = RiskLevel.MEDIUM
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionContract:
    id: str
    subject: str
    decision: str
    rationale: str = ""
    author: str = ""
    source: str = ""
    approved: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportContract:
    id: str
    task_id: str
    status: str
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditEventContract:
    id: str
    action: str
    actor: str
    outcome: str
    task_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryRecordContract:
    id: str
    content: str
    source: str
    author: str
    confidence: float = 1.0
    version: int = 1
    invalidated: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ContractError("confidence must be between 0 and 1")
        if self.version < 1:
            raise ContractError("version must be positive")
