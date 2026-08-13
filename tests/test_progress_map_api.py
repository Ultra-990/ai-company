from app.services.project_progress import load_project_progress


def test_project_progress_is_calculated_from_stages() -> None:
    data = load_project_progress()

    assert data["project"] == "Virtual Company"
    assert data["total_progress"] == 53
    assert data["stages"]

    calculated = round(
        sum(stage["progress"] for stage in data["stages"])
        / len(data["stages"])
    )

    assert data["total_progress"] == calculated
