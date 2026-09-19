from html.parser import HTMLParser
from base64 import b64decode

import pytest
from sqlalchemy import select, func

from app.models.artifact import Artifact
from app.models.task import TaskAttempt
from app.services.package_previews import preview_sources, PreviewUnavailable, MAX_CSS_BYTES, TAGS, ATTRS
from app.services.workspace_packages import validate_files
from app.services.work_orders import website_starter
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS
from tests.test_package_checks import save


def preview(files):
    return preview_sources({"files": validate_files(files)})


class Parsed(HTMLParser):
    def __init__(self, document):
        super().__init__(); self.tags = []; self.feed(document)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def test_starter_retains_real_css_and_text():
    files = website_starter(dict(title='Pracownia <bez skryptów>', goal='Opis strony',
                                audience='Klienci', constraints='Bez sieci', acceptance_criteria=['Mobile']))
    data = preview(files)
    assert data['stylesheets'] == ['styles.css']
    doc = data['document']
    parsed = Parsed(doc)
    css = next(attrs['href'] for tag, attrs in parsed.tags if tag == 'link')
    assert b64decode(css.split(',', 1)[1]).decode() == files['styles.css']
    assert 'Pracownia &lt;bez skryptów&gt;' in doc
    assert not data['scripts_executed'] and not data['product_accepted']


@pytest.mark.parametrize('source', [
    '<script>parent.document.body.innerHTML="stolen"</script><h1>OK</h1>',
    '<svg><foreignObject><script>alert(1)</script></foreignObject></svg><h1>OK</h1>',
    '<math><mtext><img src=x onerror=alert(1)></mtext></math><h1>OK</h1>',
    '<iframe srcdoc="<script>alert(1)</script>"></iframe><object data="/api/x"></object><h1>OK</h1>',
    '<meta http-equiv=refresh content="0;url=https://example.invalid"><base href="https://example.invalid"><h1>OK</h1>',
    '<a href="javascript:alert(1)" ping="/api/x" target="_top">OK</a>',
    '<form action="/api/tasks"><input name=x value=secret><button formaction="/api/x">OK</button></form>',
    '<div style="background:url(/api/x)" onclick="alert(1)" data-x="secret">OK</div>',
    '<template shadowrootmode="open"><script>alert(1)</script></template><h1>OK</h1>',
    '<noscript><img src=x onerror=alert(1)></noscript><h1>OK</h1>',
])
def test_active_markup_and_urls_never_reach_body(source):
    doc = preview({'index.html':source})['document']
    body = doc.split('<body>', 1)[1]
    assert 'OK' in body
    for tag, attrs in Parsed(body).tags:
        assert tag in TAGS
        assert set(attrs) <= ATTRS | {'disabled', 'type'}
    assert 'secret' not in body
    assert 'alert(1)' not in body
    assert '/api/' not in body


def test_css_is_data_not_html_and_never_fetched_from_urls():
    css = 'body { color:red } /* </style><script>alert(1)</script> */'
    data = preview({'index.html':'<link rel=stylesheet href="./styles.css"><link rel=stylesheet href="https://example.invalid/x"><h1>A</h1>', 'styles.css':css})
    assert data['stylesheets'] == ['styles.css']
    assert '<script>' not in data['document'] and 'example.invalid' not in data['document']
    assert "default-src &#x27;none&#x27;" in data['document']
    assert "style-src data:" in data['document']
    assert data['omitted_items'] == 1


def test_bare_link_attributes_are_ignored():
    data = preview({'index.html':'<link rel href="styles.css"><link rel=stylesheet href><h1>OK</h1>', 'styles.css':'body{}'})
    assert data['stylesheets'] == [] and data['omitted_items'] == 2


@pytest.mark.parametrize('files', [
    {'main.py':'raise RuntimeError()'},
    {'index.html':'<div>'*129},
    {'index.html':'<br>'*5001},
    {'index.html':'<link rel=stylesheet href="large.css">', 'large.css':' '* (MAX_CSS_BYTES+1)},
])
def test_limits_fail_closed(files):
    with pytest.raises(PreviewUnavailable):
        preview(files)


def test_owner_read_only_version_binding(client, task_repository):
    task, package = save(client, task_repository)
    url = f'/api/tasks/{task.id}/workspace-packages/{package}/preview'
    for headers, code in (({},401),(WORKER_HEADERS,403),(OWNER_HEADERS,200)):
        response = client.get(url, headers=headers)
        assert response.status_code == code, response.text
    data = response.json()
    assert data['task_id'] == task.id and data['package_id'] == package
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert response.headers['content-type'] == 'application/json'
    assert data['source_checksum']
    assert task_repository.get_required(task.id).progress == 0
    with task_repository._session_factory() as session:
        assert session.scalar(select(func.count()).select_from(TaskAttempt)) == 0
        assert session.scalar(select(func.count()).select_from(Artifact)) == 1
        artifact = session.get(Artifact, package)
        artifact.content += ' '
        session.commit()
    assert client.get(url, headers=OWNER_HEADERS).status_code == 409


def test_missing_wrong_task_and_unsupported(client, task_repository):
    task, package = save(client, task_repository, {'code.py':'print("not run")'})
    assert client.get(f'/api/tasks/{task.id}/workspace-packages/{package}/preview', headers=OWNER_HEADERS).status_code == 422
    other = task_repository.create(title='Other task')
    assert client.get(f'/api/tasks/{other.id}/workspace-packages/{package}/preview', headers=OWNER_HEADERS).status_code == 404
    assert client.get(f'/api/tasks/{task.id}/workspace-packages/999999/preview', headers=OWNER_HEADERS).status_code == 404


def test_parent_csp_does_not_allow_inline_scripts_or_styles(client):
    page = client.get('/os/work')
    policy = page.headers['content-security-policy']
    assert "script-src 'self';" in policy
    assert "style-src 'self' data:;" in policy
    assert 'unsafe-inline' not in policy and 'unsafe-eval' not in policy
    assert 'sandbox=""' in page.text and 'allow-same-origin' not in page.text
