from typing import Any, Dict

from app.brain.context_manager import ContextManager


class Reporter:
    def build_report(self, context: ContextManager) -> Dict[str, Any]:
        return {
            "project": context.project_state.name,
            "version": context.project_state.version,
            "stage": context.project_state.stage,
            "status": context.project_state.status,
            "tasks": len(context.tasks),
            "agents": len(context.agents),
            "decisions": len(context.decisions),
            "approvals": len(context.approvals),
        }
