"""Static help never reads operational data or mutates project state."""
from pathlib import Path
import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import help_center
from app.help_content import OWNER, CLIENT

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def help_client():
    app = FastAPI()
    app.include_router(help_center.owner_router)
    app.include_router(help_center.client_router)
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize('path,catalog', [('/os/help', OWNER), ('/client/help', CLIENT)])
def test_public_instructions_without_credentials(help_client, path, catalog):
    response = help_client.get(path)
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['referrer-policy'] == 'no-referrer'
    assert "connect-src 'none'" in response.headers['content-security-policy']
    assert 'id="help-search"' in response.text
    assert '<noscript>' in response.text
    for topic in catalog:
        assert f'id="{topic["id"]}"' in response.text
        assert topic['title'] in response.text
    assert '<script>' not in response.text


@pytest.mark.parametrize('catalog,prefix', [(OWNER, '/os'), (CLIENT, '/client')])
def test_catalog_complete_and_links_internal(catalog, prefix):
    ids = [t['id'] for t in catalog]
    assert len(ids) == len(set(ids))
    assert ids[0] == 'start'
    for topic in catalog:
        assert re.fullmatch('[a-z-]+', topic['id'])
        assert topic['title'] and topic['summary'] and topic['steps']
        assert all(isinstance(s, str) and s for s in topic['steps'])
        assert topic['warning'] and topic['action']
        assert topic['href'].startswith(prefix)
        assert '?' not in topic['href'] or topic['href'] == '/os/work?teams=1'


def test_content_is_escaped(monkeypatch, help_client):
    malicious = OWNER[0] | {'title': '<img src=x onerror=alert(1)>',
                            'steps': ['<script>unsafe()</script>']}
    monkeypatch.setattr(help_center, 'OWNER', [malicious])
    text = help_client.get('/os/help').text
    assert '<img' not in text and '<script>' not in text
    assert '&lt;img' in text and '&lt;script&gt;' in text


def test_separate_client_surface_and_assets():
    from app.client_main import app
    with TestClient(app) as client:
        response = client.get('/client/help')
        assert response.status_code == 200
        assert '/os/' not in response.text
        assert 'Qwen' not in response.text
        assert 'Token właściciela' not in response.text
        assert client.get('/os/help').status_code == 404
        assert client.get('/static/organization-os/help.js').status_code == 200
        assert client.get('/static/organization-os/help.css').status_code == 200
        assert client.get('/static/organization-os/build.js').status_code == 404


@pytest.mark.parametrize('name', ['command', 'spatial', 'work', 'build', 'review',
                                 'publishing', 'client-history', 'client'])
def test_visible_help_navigation(name):
    text = (ROOT / f'app/templates/organization-os/{name}.html').read_text()
    target = '/client/help' if name == 'client' else '/os/help'
    assert f'<a href="{target}" data-help-link>Pomoc</a>' in text


def test_application_registers_help_and_action_targets(client):
    for path in {'/os/help', '/client/help'} | {t['href'] for t in OWNER + CLIENT}:
        assert client.get(path).status_code == 200, path


def test_search_uses_no_api_or_storage():
    text = (ROOT / 'app/static/organization-os/help.js').read_text()
    for prohibited in ['fetch(', 'XMLHttpRequest', 'localStorage', 'sessionStorage', 'innerHTML']:
        assert prohibited not in text
