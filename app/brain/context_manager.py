from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ProjectState:
    name: str = "AI Company"
    version: str = "v2"
    stage: str = "consolidation"
    status: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    id: str
    title: str
    description: str = ""
    status: str = "pending"
    priority: str = "medium"
    resource_class: str = "general"
    risk_level: str = "medium"
    assigned_agent: Optional[str] = None
    queued_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentProfile:
    id: str
    name: str
    role: str
    enabled: bool = True
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Decision:
    id: str
    subject: str
    decision: str
    rationale: str = ""
    approved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ApprovalRequest:
    id: str
    subject: str
    requested_by: str
    reason: str = ""
    required: bool = True
    status: str = "pending"
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextManager:
    def __init__(self, project_state: Optional[ProjectState] = None):
        self.project_state = project_state or ProjectState()
        self.tasks: List[Task] = []
        self.agents: List[AgentProfile] = []
        self.decisions: List[Decision] = []
        self.approvals: List[ApprovalRequest] = []

    def add_task(self, task: Task) -> Task:
        self.tasks.append(task)
        return task

    def add_agent(self, agent: AgentProfile) -> AgentProfile:
        self.agents.append(agent)
        return agent

    def add_decision(self, decision: Decision) -> Decision:
        self.decisions.append(decision)
        return decision

    def add_approval(self, approval: ApprovalRequest) -> ApprovalRequest:
        self.approvals.append(approval)
        return approval

    def clear_tasks(self) -> None:
        self.tasks.clear()

    def clear_agents(self) -> None:
        self.agents.clear()

    def clear_decisions(self) -> None:
        self.decisions.clear()

    def clear_approvals(self) -> None:
        self.approvals.clear()

    def snapshot(self) -> Dict[str, Any]:
        return {
            "project_state": self._serialize(self.project_state),
            "tasks": [self._serialize(task) for task in self.tasks],
            "agents": [self._serialize(agent) for agent in self.agents],
            "decisions": [self._serialize(decision) for decision in self.decisions],
            "approvals": [self._serialize(approval) for approval in self.approvals],
        }

    def _serialize(self, item: Any) -> Any:
        if is_dataclass(item):
            return asdict(item)
        if isinstance(item, list):
            return [self._serialize(value) for value in item]
        if isinstance(item, dict):
            return {key: self._serialize(value) for key, value in item.items()}
        return item
