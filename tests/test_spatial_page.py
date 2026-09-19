from html.parser import HTMLParser


class WorkbenchLinks(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.stack = []
        self.entries = []
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if attrs.get('id') == 'workbench-shortcut':
            self.entries.append((attrs, list(self.stack)))
        if tag not in {'meta', 'link', 'input', 'br', 'hr', 'img'}:
            self.stack.append((tag, attrs))

    def handle_endtag(self, tag):
        for index in range(len(self.stack)-1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break


def test_workbench_entry_is_in_static_navigation_not_hidden_in_dialog(client):
    for path in ('/os', '/os/spatial'):
        response = client.get(path)
        assert response.headers['cache-control'] == 'no-store'
        entries = WorkbenchLinks(response.text).entries
        assert len(entries) == 1
        attrs, ancestors = entries[0]
        assert attrs['href'] == '/os/work'
        assert any(tag == 'nav' and a.get('class') == 'work-entry' for tag, a in ancestors)
        assert not any(tag == 'dialog' or 'hidden' in a for tag, a in ancestors)
    assert client.get('/os/work').status_code == 200


def test_spatial_prototype_is_opt_in_and_assets_are_local(client):
    response = client.get('/os/spatial')
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    assert '/static/spatial/boot.js' in response.text
    assert 'href="/os"' in response.text
    assert 'id="inspector"' in response.text
    assert 'id="scene-track"' in response.text
    assert 'id="department-search"' in response.text
    assert 'id="brain-shortcut"' in response.text
    assert 'href="#directory"' in response.text
    assert 'cdn.' not in response.text
    assert client.get('/os').status_code == 200
    for name in ('boot.js','spatial.js','motion.mjs','spatial.css',
                 'vendor/three.module.js','vendor/three.core.js',
                 'vendor/CSS3DRenderer.js','vendor/THREE-LICENSE.txt'):
        asset = client.get('/static/spatial/' + name)
        assert asset.status_code == 200, name
    renderer = client.get('/static/spatial/vendor/CSS3DRenderer.js').text
    assert "from './three.module.js'" in renderer
