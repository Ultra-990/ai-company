import pytest
from fastapi.testclient import TestClient
from app.client_main import app as client_app


@pytest.mark.parametrize('path',['/os','/os/spatial','/os/work','/client','/','/progress'])
def test_pages_share_appearance_assets_and_safe_navigation(client,path):
    response=client.get(path)
    assert response.status_code==200
    assert '/static/organization-os/theme.js?v=4' in response.text
    assert '/static/organization-os/theme.css?v=2' in response.text
    assert 'class="app-navigation"' in response.text
    assert 'data-back' in response.text and 'data-home' in response.text
    assert 'href="/os" data-home' in response.text


def test_separate_client_surface_keeps_its_own_home_and_serves_palette(client):
    with TestClient(client_app) as customer:
        assert customer.get('/static/organization-os/theme.css').status_code==200
        page=customer.get('/client').text
        assert 'href="/client" data-home' in page
        assert 'href="/os"' not in page
        assert customer.get('/os').status_code==404


def test_workbench_no_longer_overrides_shared_theme(client):
    script=client.get('/static/organization-os/work.js').text
    assert 'dataset.theme=' not in script
    assert 'prefers-color-scheme' not in script


def test_spatial_summary_and_navigation_contract(client):
    script=client.get('/static/spatial/spatial.js').text
    assert 'r.body.scrollTop+=' not in script and 'contents.scrollTop+=' not in script
    assert 'r.summary=' not in script and 'r.children=' not in script
    assert "$('inspector-back').addEventListener" in script
    assert "$('inspector-menu').addEventListener" in script
    assert 'CompanyOrbit?.mount(hit)' in script
    css=client.get('/static/organization-os/theme.css').text
    assert '.planet-ring' in css and 'prefers-reduced-motion' in css
    theme=client.get('/static/organization-os/theme.js').text
    assert "maskUnits:'userSpaceOnUse'" in theme
    assert "moon.dataset.depth=y<0?'behind':'front'" in theme
    assert "document.addEventListener('wheel'" not in script
    assert "stage.addEventListener('wheel'" in script
