"""Search is a public route catalog, not an operational-data search endpoint."""
from pathlib import Path
import re

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'app/static/organization-os/navigation-search.js'


@pytest.mark.parametrize('name', ['command', 'spatial', 'work', 'build', 'review',
                                 'publishing', 'client-history'])
def test_navigation_assets_and_no_js_client_link(name):
    text = (ROOT / f'app/templates/organization-os/{name}.html').read_text()
    assert 'navigation-search.js?v=1' in text
    assert 'navigation-search.css?v=1' in text
    assert '<a href="/client" data-client-entry>Panel klienta ↗</a>' in text


def test_all_search_routes_exist(client):
    targets = re.findall(r"href: '([^']+)'", SOURCE.read_text())
    assert len(targets) == len(set(targets)) == 16
    assert '/os/media' in targets
    for target in targets:
        assert target.startswith('/') and not target.startswith('//')
        assert client.get(target.split('#')[0]).status_code == 200, target
    html = client.get('/os').text
    assert 'data-view="departments"' in html and 'data-view="decisions"' in html


def test_client_has_no_owner_catalog():
    from app.client_main import app
    with TestClient(app) as client:
        for path in ['/client', '/client/help']:
            assert 'navigation-search' not in client.get(path).text
        for asset in ['navigation-search.js', 'navigation-search.css']:
            assert client.get('/static/organization-os/'+asset).status_code == 404


def test_search_is_local_and_text_safe():
    source = SOURCE.read_text()
    for forbidden in ['fetch(', 'XMLHttpRequest', 'localStorage', 'sessionStorage',
                      'innerHTML', 'eval(', '/api/']:
        assert forbidden not in source
    assert "input.maxLength = 120" in source


def test_owner_help_includes_navigation_search(client):
    assert 'navigation-search.js?v=1' in client.get('/os/help').text
