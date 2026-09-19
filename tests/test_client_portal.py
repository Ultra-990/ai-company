from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pytest
from sqlalchemy import select

from app.models.client_portal import ClientShare
from app.models.project import Project
from app.api.client_portal import PublishedProject
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS


@pytest.fixture
def project_id(task_repository):
    with task_repository._session_factory() as session:
        p = Project(name="INTERNAL SECRET PROJECT", business_goal="INTERNAL BUDGET AND STRATEGY")
        session.add(p); session.commit(); return p.id


def content(title="Strona dla klienta"):
    return {"title": title, "summary": "Uzgodniony zakres strony", "progress": 25,
            "status": "in_progress", "next_step": "Akceptacja projektu graficznego",
            "milestones": [{"title": "Makieta", "status": "completed"}]}


def issue(client, project_id, **changes):
    return client.post("/api/client-shares", json=content() | {"project_id": project_id} | changes, headers=OWNER_HEADERS)


def test_owner_only_issue_and_allowlisted_client_view(client, task_repository, project_id):
    data = content() | {"project_id": project_id}
    assert client.post("/api/client-shares", json=data).status_code == 401
    assert client.post("/api/client-shares", json=data, headers=WORKER_HEADERS).status_code == 403
    response = issue(client, project_id)
    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    share = response.json(); token = share["token"]
    assert len(token) == 43
    result = client.get("/api/client/overview", headers={"Authorization": "Bearer " + token})
    assert result.status_code == 200
    assert result.headers["cache-control"] == "no-store"
    assert result.json()["project"] == PublishedProject.model_validate(content()).model_dump()
    assert set(result.json()) == {"project", "updated_at", "expires_at", "source", "publication_checksum", "client_decisions"}
    assert "INTERNAL" not in result.text
    assert "project_id" not in result.text
    assert token not in result.text
    with task_repository._session_factory() as session:
        record = session.get(ClientShare, share["id"])
        assert record.token_digest == sha256(token.encode()).hexdigest()
        assert token not in record.public_content


def test_two_clients_cannot_select_each_others_snapshot(client, project_id):
    one = issue(client, project_id, title="Klient A").json()
    two = issue(client, project_id, title="Klient B").json()
    assert one["token"] != two["token"]
    for share, expected in ((one, "Klient A"), (two, "Klient B")):
        result = client.get(f'/api/client/overview?project_id={project_id}&share_id={two["id"]}',
                            headers={"Authorization": "Bearer " + share["token"]})
        assert result.json()["project"]["title"] == expected
        assert client.get("/api/client-shares", params={"project_id": project_id},
                          headers={"Authorization": "Bearer " + share["token"]}).status_code == 401


@pytest.mark.parametrize("headers", [{}, WORKER_HEADERS, OWNER_HEADERS, {"Authorization": "Bearer " + "x"*43}, {"Authorization": "Basic x"}])
def test_invalid_client_credentials_fail_closed(client, headers):
    response = client.get("/api/client/overview", headers=headers)
    assert response.status_code == 401
    assert "project" not in response.json()


def test_expiry_revocation_and_updates(client, task_repository, project_id):
    share = issue(client, project_id).json()
    path = f'/api/client-shares/{share["id"]}'
    token_headers = {"Authorization": "Bearer " + share["token"]}
    assert client.put(path, json=content("Updated"), headers=token_headers).status_code == 401
    assert client.put(path, json=content("Updated"), headers=OWNER_HEADERS).status_code == 200
    assert client.get("/api/client/overview", headers=token_headers).json()["project"]["title"] == "Updated"
    assert client.post(path+"/revoke", headers=WORKER_HEADERS).status_code == 403
    assert client.post(path+"/revoke", headers=OWNER_HEADERS).status_code == 200
    assert client.post(path+"/revoke", headers=OWNER_HEADERS).status_code == 200
    assert client.get("/api/client/overview", headers=token_headers).status_code == 401
    assert client.put(path, json=content(), headers=OWNER_HEADERS).status_code == 409
    other = issue(client, project_id).json()
    with task_repository._session_factory() as session:
        session.get(ClientShare, other["id"]).expires_at = datetime.now(timezone.utc)-timedelta(seconds=1)
        session.commit()
    assert client.get("/api/client/overview", headers={"Authorization":"Bearer "+other["token"]}).status_code == 401
    assert client.put(f'/api/client-shares/{other["id"]}', json=content(), headers=OWNER_HEADERS).status_code == 409


def test_listing_does_not_redisclose_tokens(client, project_id):
    share = issue(client, project_id).json()
    response = client.get("/api/client-shares", params={"project_id":project_id}, headers=OWNER_HEADERS)
    assert response.status_code == 200
    assert share["token"] not in response.text
    assert "token_digest" not in response.text
    assert response.json()["shares"][0]["id"] == share["id"]
    assert client.get("/api/client-shares?project_id=999999", headers=OWNER_HEADERS).json() == {"shares":[]}


@pytest.mark.parametrize("changes", [{"progress":101}, {"progress":True}, {"expires_in_days":0}, {"expires_in_days":31},
                                      {"title":"   "}, {"tasks":[]}, {"milestones":[{"title":"X", "budget":12}]}])
def test_invalid_publication_rejected(client, project_id, changes):
    assert issue(client, project_id, **changes).status_code == 422


def test_client_shell_no_data_and_restrictive_headers(client):
    response = client.get("/client")
    assert response.status_code == 200
    assert "INTERNAL" not in response.text
    assert 'id="client-login"' in response.text
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert issue(client, 999999).status_code == 404


def test_separate_client_app_has_no_internal_routes(client, project_id):
    from fastapi.testclient import TestClient
    from app.client_main import app as portal
    from app.main import app as internal
    from app.api.organization_os import get_organization_session

    share = issue(client, project_id).json()
    portal.dependency_overrides[get_organization_session] = internal.dependency_overrides[get_organization_session]
    try:
        with TestClient(portal) as customer:
            for path in ("/api/tasks", "/api/local-inference", "/api/application-revisions", "/static/organization-os/application-revisions.js", "/api/package-runs", "/api/package-runs/preview", "/os/application-frame", "/static/organization-os/application-frame.js", "/static/organization-os/application-preview.js", "/os/build", "/static/organization-os/build.js", "/api/organization-os/tree", "/api/client-shares", "/docs", "/openapi.json", "/os",
                         "/api/application-quality", "/api/application-quality/1/run", "/static/organization-os/application-quality.js",
                         "/os/legacy", "/os/publishing", "/os/review", "/static/organization-os/command.js", "/static/organization-os/command.css",
                         "/static/organization-os/delivery-center.js", "/static/organization-os/client-publishing.js"):
                assert customer.get(path).status_code == 404
            response = customer.get("/api/client/overview", headers={"Authorization":"Bearer "+share["token"]})
            assert response.status_code == 200
            assert response.json()["project"] == PublishedProject.model_validate(content()).model_dump()
            assert response.headers["cache-control"] == "no-store"
            assert customer.get("/api/client/overview").status_code == 401
            assert customer.get("/client").status_code == 200
            assert customer.get("/static/organization-os/theme.js").status_code == 200
            for path in ('/os/clients', '/api/client-history', f'/api/client-shares/{share["id"]}/history', '/static/organization-os/client-history.js'):
                assert customer.get(path).status_code == 404
    finally:
        portal.dependency_overrides.clear()
