import pytest

from app.models.plan import Plan, PlanStatus, PlanTransitionError


def make_plan(status: PlanStatus = PlanStatus.DRAFT) -> Plan:
    return Plan(
        project_id=1,
        name="Plan testowy",
        objective="Dostarczyć mierzalny rezultat.",
        status=status,
    )


def test_new_plan_defaults_to_draft() -> None:
    plan = Plan(
        project_id=1,
        name="Plan domyślny",
        objective="Cel planu.",
    )

    assert plan.status is PlanStatus.DRAFT


def test_plan_can_move_from_draft_to_ready() -> None:
    plan = make_plan()

    plan.transition_to(PlanStatus.READY)

    assert plan.status is PlanStatus.READY


def test_plan_can_complete_after_starting() -> None:
    plan = make_plan(PlanStatus.READY)

    plan.transition_to(PlanStatus.IN_PROGRESS)
    started_at = plan.started_at
    plan.transition_to(PlanStatus.COMPLETED)

    assert plan.status is PlanStatus.COMPLETED
    assert started_at is not None
    assert plan.completed_at is not None


def test_blocked_plan_can_return_to_ready() -> None:
    plan = make_plan(PlanStatus.BLOCKED)

    plan.transition_to(PlanStatus.READY)

    assert plan.status is PlanStatus.READY


@pytest.mark.parametrize(
    ("current_status", "new_status"),
    [
        (PlanStatus.DRAFT, PlanStatus.IN_PROGRESS),
        (PlanStatus.DRAFT, PlanStatus.COMPLETED),
        (PlanStatus.READY, PlanStatus.COMPLETED),
        (PlanStatus.BLOCKED, PlanStatus.COMPLETED),
        (PlanStatus.COMPLETED, PlanStatus.IN_PROGRESS),
        (PlanStatus.CANCELLED, PlanStatus.DRAFT),
        (PlanStatus.DRAFT, PlanStatus.DRAFT),
    ],
)
def test_plan_rejects_invalid_transition(
    current_status: PlanStatus,
    new_status: PlanStatus,
) -> None:
    plan = make_plan(current_status)

    with pytest.raises(PlanTransitionError):
        plan.transition_to(new_status)

    assert plan.status is current_status
