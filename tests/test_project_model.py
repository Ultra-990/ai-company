import pytest

from app.models.project import (
    Project,
    ProjectStatus,
    ProjectTransitionError,
)


def make_project(
    status: ProjectStatus = ProjectStatus.DRAFT,
) -> Project:
    return Project(
        name="Projekt testowy",
        business_goal="Dostarczyć zweryfikowany rezultat biznesowy.",
        status=status,
    )


def test_new_project_defaults_to_draft() -> None:
    project = Project(
        name="Projekt domyślny",
        business_goal="Cel projektu.",
    )

    assert project.status is ProjectStatus.DRAFT


def test_project_can_move_from_draft_to_planned() -> None:
    project = make_project()

    project.transition_to(ProjectStatus.PLANNED)

    assert project.status is ProjectStatus.PLANNED


def test_project_can_complete_after_starting() -> None:
    project = make_project(ProjectStatus.PLANNED)

    project.transition_to(ProjectStatus.IN_PROGRESS)
    started_at = project.started_at
    project.transition_to(ProjectStatus.COMPLETED)

    assert project.status is ProjectStatus.COMPLETED
    assert started_at is not None
    assert project.completed_at is not None


def test_blocked_project_can_be_returned_to_planned() -> None:
    project = make_project(ProjectStatus.BLOCKED)

    project.transition_to(ProjectStatus.PLANNED)

    assert project.status is ProjectStatus.PLANNED


@pytest.mark.parametrize(
    ("current_status", "new_status"),
    [
        (ProjectStatus.DRAFT, ProjectStatus.IN_PROGRESS),
        (ProjectStatus.PLANNED, ProjectStatus.COMPLETED),
        (ProjectStatus.BLOCKED, ProjectStatus.COMPLETED),
        (ProjectStatus.COMPLETED, ProjectStatus.IN_PROGRESS),
        (ProjectStatus.CANCELLED, ProjectStatus.DRAFT),
        (ProjectStatus.DRAFT, ProjectStatus.DRAFT),
    ],
)
def test_project_rejects_invalid_transition(
    current_status: ProjectStatus,
    new_status: ProjectStatus,
) -> None:
    project = make_project(current_status)

    with pytest.raises(ProjectTransitionError):
        project.transition_to(new_status)

    assert project.status is current_status
