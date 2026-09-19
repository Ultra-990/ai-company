"""Bounded, deterministic source inspection. Never imports or executes package code."""
import json
import posixpath
from datetime import timezone
from hashlib import sha256
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.artifact import Artifact, ArtifactType
from app.models.audit import AuditEvent
from app.services.workspace_packages import (
    canonical_json, read_package, PackageIntegrityError, PackageNotFound,
)

CHECK_NAME = "organization-os.static-check.v1"
MAX_CHECKS = 400
MAX_TAGS = 10000
MAX_JSON_DEPTH = 128
NOT_CHECKED = [
    "Nie uruchomiono HTML w przeglądarce ani kodu JS, Python, poleceń lub testów paczki.",
    "Nie zweryfikowano wyglądu, działania, wydajności, pełnej dostępności ani kryteriów klienta.",
    "Nie analizowano składni CSS/JS ani adresów w CSS, srcset i dynamicznie tworzonych zasobach.",
    "Nie pobierano zewnętrznych adresów. Raport nie jest audytem bezpieczeństwa ani odbiorem produktu.",
]


class InspectionLimit(ValueError):
    pass


def check_json_depth(source: str) -> None:
    """Bound nesting before the standard parser, without changing process limits."""
    depth = 0
    quoted = escaped = False
    for char in source:
        if quoted:
            if escaped: escaped = False
            elif char == "\\": escaped = True
            elif char == '"': quoted = False
        elif char == '"': quoted = True
        elif char in "[{":
            depth += 1
            if depth > MAX_JSON_DEPTH: raise InspectionLimit()
        elif char in "]}": depth -= 1


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = 0
        self.lang = False
        self.doctype = False
        self.viewport = False
        self.h1 = 0
        self.main = 0
        self.in_title = False
        self.title = False
        self.ids = set()
        self.duplicate_ids = False
        self.references = []
        self.missing_alt = []
        self.active = False
        self.base = False

    def handle_decl(self, decl):
        self.doctype = self.doctype or decl.strip().lower() == "doctype html"

    def handle_starttag(self, tag, attrs):
        self.tags += 1
        if self.tags > MAX_TAGS:
            raise InspectionLimit()
        a = dict(attrs)
        line = self.getpos()[0]
        if tag == "html": self.lang = bool((a.get("lang") or "").strip())
        if tag == "meta" and (a.get("name") or "").lower() == "viewport":
            self.viewport = "width=device-width" in (a.get("content") or "").replace(" ", "").lower()
        if tag == "h1": self.h1 += 1
        if tag == "main" or a.get("role") == "main": self.main += 1
        if tag == "title": self.in_title = True
        if tag == "base": self.base = True
        if tag in {"script", "iframe", "object", "embed", "form"} or any(k.startswith("on") for k in a):
            self.active = True
        if "id" in a and a["id"]:
            self.duplicate_ids |= a["id"] in self.ids
            self.ids.add(a["id"])
        if tag == "img" and "alt" not in a: self.missing_alt.append(line)
        for attr in ("href", "src"):
            if a.get(attr) is not None and tag != "base":
                self.references.append((a[attr], line))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == "title": self.in_title = False

    def handle_data(self, data):
        if self.in_title and data.strip(): self.title = True


def inspect_sources(payload: dict) -> dict:
    files = {entry["path"]: entry["content"] for entry in payload["files"]}
    checks, pages = [], {}
    incomplete = False
    supported = 0

    def add(code, status, message, path=None, line=None):
        nonlocal incomplete
        if len(checks) >= MAX_CHECKS:
            incomplete = True
            return
        checks.append(dict(code=code, status=status, message=message, path=path, line=line))

    add("integrity", "passed", "Manifest, rozmiary i sumy plików zweryfikowano przed analizą.")
    for path, source in files.items():
        extension = posixpath.splitext(path)[1].lower()
        if extension in {".html", ".htm"}:
            supported += 1
            page = Page()
            try:
                page.feed(source)
                page.close()
            except InspectionLimit:
                incomplete = True
                add("html.limit", "warning", "Przekroczono limit 10000 znaczników; plik nie został w pełni sprawdzony.", path)
                continue
            except (ValueError, AssertionError):
                add("html.parse", "failed", "Nie można przeanalizować tego zapisu HTML.", path)
                continue
            pages[path] = page
            for code, ok, description in (
                ("doctype", page.doctype, "Deklaracja HTML5"),
                ("lang", page.lang, "Niepusty atrybut języka dokumentu"),
                ("title", page.title, "Niepusty tytuł dokumentu"),
                ("viewport", page.viewport, "Viewport z width=device-width"),
                ("h1", page.h1 == 1, "Dokładnie jeden nagłówek h1 (reguła profilu)"),
                ("main", page.main == 1, "Dokładnie jeden obszar main"),
                ("ids", not page.duplicate_ids, "Brak powtarzających się identyfikatorów"),
            ):
                add("html." + code, "passed" if ok else "failed", description, path)
            for line in page.missing_alt:
                add("html.alt", "failed", "Obraz nie ma atrybutu alt; pusty alt dopuszczalny dla dekoracji.", path, line)
            if page.active:
                add("html.active", "warning", "Aktywne elementy wymagają osobnej kontroli; nie zostały wykonane.", path)
            if page.base:
                incomplete = True
                add("html.base", "warning", "Element base zmienia rozwiązywanie adresów; odnośniki tego pliku pominięto.", path)
        elif extension == ".json":
            supported += 1
            try:
                def invalid_constant(_): raise ValueError("Non-JSON constant")
                check_json_depth(source)
                json.loads(source, parse_constant=invalid_constant)
                add("json.syntax", "passed", "Poprawna składnia JSON; schemat biznesowy nie był sprawdzany.", path)
            except (ValueError, RecursionError):
                add("json.syntax", "failed", "Nieprawidłowy JSON lub przekroczona głębokość parsera.", path)

    for path, page in pages.items():
        if page.base: continue
        for raw, line in page.references:
            try:
                ref = urlsplit(raw.strip())
                if ref.scheme or ref.netloc:
                    dangerous = ref.scheme.lower() in {"javascript", "vbscript", "file", "data"}
                    add("link.external", "failed" if dangerous else "warning",
                        "Adres aktywny/lokalny spoza paczki wymaga usunięcia lub odrębnej kontroli." if dangerous
                        else "Odnośnik zewnętrzny nie był sprawdzany ani pobierany.", path, line)
                    continue
                relative = unquote(ref.path)
                if "\\" in relative or any(ord(c) < 32 for c in relative):
                    raise ValueError()
                target = path if not relative else posixpath.normpath(
                    relative.lstrip("/") if relative.startswith("/") else posixpath.join(posixpath.dirname(path), relative))
                if target == ".." or target.startswith("../"): raise ValueError()
                if relative.endswith("/"):
                    target = posixpath.join(target, "index.html")
                    if target.startswith("./"): target = target[2:]
                if target not in files:
                    add("link.missing", "failed", "Brak wskazanego lokalnego pliku w paczce.", path, line)
                elif ref.fragment and target in pages and unquote(ref.fragment) not in pages[target].ids:
                    add("link.fragment", "failed", "Nie znaleziono wskazanego ID w docelowym dokumencie HTML.", path, line)
                else:
                    add("link.local", "passed", "Lokalny plik/odnośnik znaleziony w paczce (bez wykonywania).", path, line)
            except ValueError:
                add("link.invalid", "failed", "Nieobsługiwany lub wychodzący poza paczkę adres.", path, line)

    counts = {status: sum(c["status"] == status for c in checks) for status in ("passed", "failed", "warning")}
    outcome = "issues_found" if counts["failed"] else "incomplete" if incomplete or not supported else "checks_passed"
    return dict(checker=CHECK_NAME, outcome=outcome, counts=counts, checks=checks,
                analysis_incomplete=incomplete, file_count=len(files), inspected_documents=supported,
                code_executed=False, product_accepted=False, not_checked=NOT_CHECKED)


def create_check(session: Session, task_id: int, package_id: int) -> Artifact:
    source, payload = read_package(session, task_id, package_id)
    report = inspect_sources(payload)
    report.update(task_id=task_id, package_id=package_id, source_checksum=source.checksum)
    content = canonical_json(report)
    artifact = Artifact(project_id=source.project_id, plan_id=source.plan_id, task_id=task_id,
                        artifact_type=ArtifactType.TEST_RESULT, name=CHECK_NAME,
                        uri=f"workspace-package:{package_id}", content=content,
                        checksum=sha256(content.encode()).hexdigest(), created_by="static-checker:v1",
                        description=f"Kontrola statyczna paczki #{package_id}: {report['outcome']}. Bez wykonania kodu i odbioru.")
    session.add(artifact)
    session.flush()
    session.add(AuditEvent(event_type="package_static_check", operation="inspect", decision=report["outcome"],
                           allowed=True, reason=f"owner; task={task_id}; package={package_id}; report={artifact.id}; source_sha256={source.checksum}"))
    session.commit()
    return artifact


def read_check(session: Session, task_id: int, report_id: int) -> dict:
    artifact = session.scalar(select(Artifact).where(Artifact.id == report_id, Artifact.task_id == task_id,
                              Artifact.artifact_type == ArtifactType.TEST_RESULT, Artifact.name == CHECK_NAME))
    if artifact is None: raise PackageNotFound("Nie znaleziono raportu dla tego zadania.")
    content = artifact.content or ""
    if sha256(content.encode()).hexdigest() != artifact.checksum:
        raise PackageIntegrityError("Niezgodna suma kontrolna raportu.")
    try:
        report = json.loads(content)
        if (report["checker"] != CHECK_NAME or report["task_id"] != task_id
                or artifact.uri != f"workspace-package:{report['package_id']}"
                or not isinstance(report["checks"], list)):
            raise ValueError()
        source, _ = read_package(session, task_id, report["package_id"])
        if source.checksum != report["source_checksum"]:
            raise ValueError()
    except (ValueError, TypeError, KeyError) as exc:
        raise PackageIntegrityError("Raport nie odpowiada aktualnej integralności paczki.") from exc
    created_at = artifact.created_at
    if created_at.tzinfo is None: created_at = created_at.replace(tzinfo=timezone.utc)
    return dict(report_id=artifact.id, report_checksum=artifact.checksum,
                created_at=created_at.astimezone(timezone.utc).isoformat(), **report)
