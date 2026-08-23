def test_plan_endpoint(client):
    response = client.post("/api/brain/plan")

    assert response.status_code == 200
    payload = response.json()

    assert "steps" in payload
    assert isinstance(payload["steps"], list)


def test_report_endpoint(client):
    response = client.get("/api/brain/report")

    assert response.status_code == 200
    assert isinstance(response.json(), dict)


def test_safety_check_endpoint(client):
    response = client.post(
        "/api/brain/safety-check",
        json={
            "action_type": "deploy",
            "requires_approval": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert set(payload) >= {"allowed", "reason"}
    assert isinstance(payload["allowed"], bool)
    assert isinstance(payload["reason"], str)

def test_create_and_list_brain_tasks(client):
    create_response = client.post(
        "/api/brain/tasks",
        json={
            "title": "Brain API task",
            "description": "Contract test",
            "priority": "normal",
            "resource_class": "light",
            "risk_level": "low",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()

    assert created["title"] == "Brain API task"
    assert created["description"] == "Contract test"
    assert isinstance(created["id"], int)
    assert "status" in created
    assert "approval_status" in created
    assert "progress" in created

    list_response = client.get("/api/brain/tasks")

    assert list_response.status_code == 200
    tasks = list_response.json()

    assert isinstance(tasks, list)
    assert any(task["id"] == created["id"] for task in tasks)


def test_list_brain_tasks_respects_limit(client):
    response = client.get("/api/brain/tasks?limit=1")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) <= 1

def test_create_brain_task_rejects_empty_title(client):
    response = client.post(
        "/api/brain/tasks",
        json={"title": ""},
    )

    assert response.status_code == 422


def test_list_brain_tasks_rejects_invalid_limit(client):
    response = client.get("/api/brain/tasks?limit=0")

    assert response.status_code == 422

def test_brain_tasks_are_isolated_between_tests(client):
    response = client.get("/api/brain/tasks")

    assert response.status_code == 200
    assert response.json() == []
