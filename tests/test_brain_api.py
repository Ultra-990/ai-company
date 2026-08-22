def test_plan_endpoint(client):
    response = client.post("/api/brain/plan")
    assert response.status_code == 200
    assert "steps" in response.json()


def test_report_endpoint(client):
    response = client.get("/api/brain/report")
    assert response.status_code == 200


def test_safety_check_endpoint(client):
    response = client.post(
        "/api/brain/safety-check",
        json={
            "action_type": "deploy",
            "requires_approval": True,
        },
    )
    assert response.status_code == 200
    assert "allowed" in response.json()
    assert "reason" in response.json()
