"""Restricted static representation, not a browser runner or HTML hosting service.

Only returned as owner-authenticated JSON. Consumers MUST use a sandboxed frame
without allow-scripts or allow-same-origin, never the owner's document DOM.
"""
from base64 import b64encode
from html import escape
from html.parser import HTMLParser

from app.services.workspace_packages import read_package

PROFILE = "organization-os.static-preview.v1"
CSP = ("default-src 'none'; script-src 'none'; style-src data:; "
       "img-src 'none'; font-src 'none'; connect-src 'none'; frame-src 'none'; "
       "object-src 'none'; base-uri 'none'; form-action 'none'")
MAX_TAGS = 5000
MAX_DEPTH = 128
MAX_CSS_BYTES = 128 * 1024
TAGS = set("main header footer nav section article aside div span p h1 h2 h3 h4 h5 h6 "
           "ul ol li dl dt dd strong em b i u s small mark sub sup blockquote pre code "
           "br hr a button details summary figure figcaption table caption thead tbody "
           "tfoot tr th td time address abbr".split())
VOID = {"br", "hr"}
SUPPRESS = {"script", "style", "title", "iframe", "object", "embed", "svg", "math", "template", "noscript"}
ATTRS = {"class", "id", "title", "lang", "dir", "role", "aria-label", "aria-labelledby",
         "aria-describedby", "aria-hidden", "colspan", "rowspan", "scope", "datetime"}


class PreviewUnavailable(ValueError):
    pass


def css_url(source: str) -> str:
    return "data:text/css;base64," + b64encode(source.encode("utf-8")).decode("ascii")


class StaticHTML(HTMLParser):
    def __init__(self, files):
        super().__init__(convert_charrefs=True)
        self.files = files
        self.parts = []
        self.stack = []
        self.styles = []
        self.css_bytes = 0
        self.tags = 0
        self.omitted = 0
        self.suppressed = None

    def handle_starttag(self, tag, attrs):
        self.tags += 1
        if self.tags > MAX_TAGS:
            raise PreviewUnavailable("HTML przekracza limit 5000 elementów podglądu.")
        if self.suppressed:
            return
        if tag in SUPPRESS:
            self.omitted += 1
            # Embed is a void element; do not hide the rest of the page.
            if tag != "embed":
                self.suppressed = tag
            return
        if tag == "link":
            values = dict(attrs)
            path = values.get("href") or ""
            if path.startswith("./"):
                path = path[2:]
            # Only exact package members; no URL resolution or filesystem access.
            if ((values.get("rel") or "").lower() == "stylesheet"
                    and path.endswith(".css") and path in self.files):
                if path not in self.styles:
                    self.css_bytes += len(self.files[path].encode("utf-8"))
                    if self.css_bytes > MAX_CSS_BYTES:
                        raise PreviewUnavailable("CSS przekracza limit 128 KiB podglądu.")
                    self.styles.append(path)
            else:
                self.omitted += 1
            return
        if tag not in TAGS:
            if tag not in {"html", "head", "body", "meta"}:
                self.omitted += 1
            return
        if len(self.stack) >= MAX_DEPTH:
            raise PreviewUnavailable("HTML przekracza limit 128 poziomów podglądu.")
        safe = []
        seen = set()
        for key, value in attrs:
            if key in ATTRS and key not in seen and value is not None:
                safe.append(f' {key}="{escape(value, quote=True)}"')
                seen.add(key)
            else:
                self.omitted += 1
        if tag == "button":
            safe.append(' type="button" disabled')
        # All URL-bearing and event attributes are absent, including href/ping.
        self.parts.append(f'<{tag}{"".join(safe)}>')
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.suppressed:
            if tag == self.suppressed:
                self.suppressed = None
            return
        if tag in self.stack:
            while self.stack:
                closing = self.stack.pop()
                self.parts.append(f"</{closing}>")
                if closing == tag:
                    break

    def handle_data(self, data):
        if not self.suppressed:
            self.parts.append(escape(data))

    def document(self):
        for tag in reversed(self.stack):
            self.parts.append(f"</{tag}>")
        styles = "".join(f'<link rel="stylesheet" href="{css_url(self.files[p])}">' for p in self.styles)
        return (f'<!doctype html><html lang="pl"><head><meta charset="utf-8">'
                f'<meta http-equiv="Content-Security-Policy" content="{escape(CSP, quote=True)}">'
                '<meta name="referrer" content="no-referrer">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                f'<title>Statyczny podgląd paczki</title>{styles}</head><body>'
                + "".join(self.parts) + '</body></html>')


def preview_sources(payload):
    files = {entry["path"]: entry["content"] for entry in payload["files"]}
    if "index.html" not in files:
        raise PreviewUnavailable("Podgląd wymaga pliku index.html w głównym katalogu paczki.")
    parser = StaticHTML(files)
    parser.feed(files["index.html"])
    parser.close()
    return dict(profile=PROFILE, entry="index.html", document=parser.document(),
                stylesheets=parser.styles, omitted_items=parser.omitted,
                scripts_executed=False, product_accepted=False,
                limitations=[
                    "To przekształcony podgląd HTML/CSS, nie uruchomiona aplikacja ani odbiór.",
                    "Skrypty, formularze, nawigacja, obrazy, SVG, multimedia i fonty zewnętrzne są wyłączone.",
                    "Style inline i atrybuty style są pomijane. Obsługiwane są lokalne arkusze .css wskazane przez link.",
                    "CSS nie może pobierać zasobów sieciowych. Podgląd może różnić się od pełnego produktu.",
                ])


def read_preview(session, task_id, package_id):
    artifact, payload = read_package(session, task_id, package_id)
    return dict(task_id=task_id, package_id=package_id, source_checksum=artifact.checksum,
                **preview_sources(payload))
