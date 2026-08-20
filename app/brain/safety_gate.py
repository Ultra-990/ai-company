from dataclasses import dataclass


@dataclass
class SafetyResult:
    allowed: bool
    reason: str = ""


class SafetyGate:
    def approve(self, action_type: str, requires_approval: bool = False) -> SafetyResult:
        if requires_approval:
            return SafetyResult(
                allowed=False,
                reason=f"Action '{action_type}' requires owner approval",
            )
        return SafetyResult(allowed=True, reason="Approved by safety gate")
