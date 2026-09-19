from enum import StrEnum


class NodeKind(StrEnum):
    ORGANIZATION = "organization"
    DIVISION = "division"
    DEPARTMENT = "department"
    TEAM = "team"
    PROJECT = "project"
    INITIATIVE = "initiative"


class NodeStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    AT_RISK = "at_risk"
    BLOCKED = "blocked"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TaskStatus(StrEnum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    IN_REVIEW = "in_review"
    DONE = "done"
    CANCELLED = "cancelled"


class AlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    BLOCKER = "blocker"
    CRITICAL = "critical"


class AlertStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class AgentKind(StrEnum):
    OWNER = "owner"
    BRAIN = "brain"
    HUMAN = "human"
    AI = "ai"
    EXTERNAL = "external"
