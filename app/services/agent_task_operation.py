from app.models.task import Task
from app.services.agent_client import AgentClient


class AgentTaskOperation:
    """Operacja wykonująca zadanie przez przypisanego agenta."""

    def __init__(self, client: AgentClient) -> None:
        self._client = client

    def __call__(self, task: Task) -> str:
        agent = (task.assigned_agent or "").strip()
        if not agent:
            raise RuntimeError(
                "Nie można wykonać zadania bez przypisanego agenta"
            )

        prompt = (task.description or "").strip()
        if not prompt:
            raise RuntimeError(
                "Nie można wykonać zadania bez opisu"
            )

        result = self._client.run(
            agent=agent,
            prompt=prompt,
        )

        if not isinstance(result, str):
            raise RuntimeError(
                "Agent zwrócił wynik, który nie jest tekstem"
            )

        result = result.strip()
        if not result:
            raise RuntimeError(
                "Agent zwrócił pusty wynik"
            )

        return result
