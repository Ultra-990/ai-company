import json
import argparse
import os
import re

import httpx
import pytest
from scripts.serve_studio_preview import estimate_path, sources, preview_bind
from tests.test_upwork_web_design import baseline


@pytest.mark.parametrize('path', ['/api/estimate?service=landing&pages=3&rush=1',
                                  '/api/estimate?pages=20&service=site&rush=0'])
def test_only_bounded_calculation(path):
    assert estimate_path(path) == path


@pytest.mark.parametrize('path', [None, '/', 'https://remote/api/estimate?service=site&pages=1&rush=0',
    '/api/estimate?service=site&pages=1&rush=0#x', '/api/estimate?service=site&pages=1&rush=0&pages=2',
    '/api/estimate?service=site&pages=21&rush=0', '/api/estimate?service=site&pages=1&rush=true',
    '/api/estimate?service=unknown&pages=1&rush=0', '/api/estimate?service=site&pages=1&rush=0&extra=1',
    '/api/estimate?service=site&pages=1.5&rush=0', '/api/estimate?service=site&pages=1',
    '/api/estimate?service=site&pages=%D9%A1&rush=0'])
def test_preview_rejects_arbitrary_paths_and_queries(path):
    with pytest.raises(ValueError): estimate_path(path)


def test_sources_are_frozen_synthetic_unpublished_candidate():
    report, _, files = baseline()
    assert sources(report) == files
    for changes in [{'accepted': True}, {'deployed': True}, {'status': 'failed'}, {'source_checksums': {}}]:
        with pytest.raises(ValueError): sources(report | changes)


@pytest.mark.parametrize('address', ['127.0.0.1', '10.0.0.57', '192.168.1.2', '172.16.0.2'])
def test_explicit_local_preview_addresses(address):
    assert preview_bind(address) == address


@pytest.mark.parametrize('address', ['0.0.0.0', '::', '8.8.8.8', '169.254.1.1',
                                   '100.76.245.65', 'localhost', '127.1', '224.0.0.1'])
def test_preview_cannot_bind_wildcard_public_or_overlay_network(address):
    with pytest.raises(argparse.ArgumentTypeError):
        preview_bind(address)


@pytest.mark.skipif(not os.environ.get('AIC_STUDIO_PREVIEW_URL'), reason='Explicit local preview only')
def test_running_preview_has_real_calculation_and_no_owner_access():
    base = os.environ['AIC_STUDIO_PREVIEW_URL']
    match = re.fullmatch(r'http://([0-9.]+):\d+', base)
    assert match and preview_bind(match[1])
    with httpx.Client(base_url=base, timeout=30, trust_env=False) as client:
        page = client.get('/')
        assert page.status_code == 200
        assert 'sandbox="allow-scripts allow-forms"' in page.text
        assert page.text.index("addEventListener('message'") < page.text.index("frame.src='/frame'")
        assert not re.search(r'<iframe[^>]+\bsrc=', page.text)
        token = json.loads(re.search(r"'X-Preview-CSRF':(\"[^\"]+\")", page.text).group(1))
        frame = client.get('/frame')
        assert frame.status_code == 200
        assert "connect-src 'none'" in frame.headers['content-security-policy']
        assert 'allow-same-origin' not in frame.headers['content-security-policy']
        assert client.get('/api/tasks').status_code == 404
        assert client.get('/', headers={'Host': 'untrusted.invalid'}).status_code == 403
        body = {'path': '/api/estimate?service=landing&pages=3&rush=1'}
        assert client.post('/probe', json=body).status_code == 403
        headers = {'Origin': base, 'X-Preview-CSRF': token}
        assert client.post('/probe', json=body, headers=headers | {'Origin': 'https://untrusted.invalid'}).status_code == 403
        assert client.post('/probe', json={'path': '/api/tasks'}, headers=headers).status_code == 409
        result = client.post('/probe', json=body, headers=headers)
        assert result.status_code == 200
        reply = result.json()['response']
        assert reply['status'] == 200 and json.loads(reply['body'])['total'] == 2125
