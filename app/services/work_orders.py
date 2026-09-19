"""Deterministic work intake; no inference, process execution or external writes."""
import json
from hashlib import sha256
from html import escape

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.models.organization import OrganizationUnit
from app.models.plan import Plan, PlanStatus
from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskStatus, ApprovalStatus, ResourceClass, RiskLevel
from app.models.work_order import WorkOrder
from app.organization_os.department_operations import workflow_for

STEPS = (
    ("Zakres i specyfikacja", "requirements-analyst", "Specyfikacja, zakres wyłączeń i pytania otwarte zatwierdzone przez właściciela."),
    ("Implementacja", "web-developer", "Wersjonowana paczka źródeł realizuje zatwierdzoną specyfikację."),
    ("Testy i kontrola jakości", "quality-reviewer", "Niezależny raport z rzeczywiście wykonanych testów i listą ograniczeń."),
    ("Odbiór i przekazanie", "delivery-manager", "Potwierdzony odbiór, instrukcja i zatwierdzona wersja przekazania."),
)


def fingerprint(brief: dict) -> str:
    return sha256(json.dumps(brief, ensure_ascii=True, sort_keys=True).encode()).hexdigest()


def order_steps(session: Session, unit: OrganizationUnit):
    """Follow real ancestry, preserving support for pre-existing custom trees."""
    seen = set()
    while unit is not None:
        if unit.id in seen:
            raise ValueError('Cykl w strukturze organizacyjnej.')
        seen.add(unit.id)
        steps = workflow_for(unit.os_key)
        if steps:
            return steps
        unit = session.get(OrganizationUnit, unit.parent_id) if unit.parent_id else None
    return STEPS


def stored_criterion(task: Task, index: int) -> str:
    """Read the criterion saved with this task, not today's mutable template."""
    marker = '\nKryterium etapu: '
    if marker in (task.description or ''):
        return task.description.rsplit(marker, 1)[1].split('\n', 1)[0]
    return STEPS[index][2] if index < len(STEPS) else ''


def create_order(session: Session, request_id: str, brief: dict) -> WorkOrder:
    """Caller owns commit/rollback, including all four tasks and the audit event."""
    previous = session.get(WorkOrder, request_id)
    if previous:
        if previous.request_hash != fingerprint(brief):
            raise ValueError("Ten identyfikator był już użyty z innym opisem. Rozpocznij nowe zlecenie.")
        return previous
    unit = session.get(OrganizationUnit, brief["organization_unit_id"])
    if unit is None or not unit.active:
        raise LookupError("Wybierz istniejący, aktywny punkt struktury.")
    if session.scalar(select(OrganizationUnit.id).where(OrganizationUnit.parent_id == unit.id).limit(1)):
        raise LookupError("Przypisz zlecenie do konkretnego liścia struktury, nie całego działu.")

    project = Project(name=brief["title"], business_goal=brief["goal"],
                      description=brief["constraints"], organization_unit_id=unit.id,
                      status=ProjectStatus.PLANNED)
    session.add(project)
    session.flush()
    plan = Plan(project_id=project.id, name="Realizacja: " + brief["title"][:188],
                objective=brief["goal"], status=PlanStatus.DRAFT,
                description="Szablon czterech etapów, nie plan wygenerowany przez AI. Wymaga dopracowania zakresu i zasobów.")
    session.add(plan)
    session.flush()
    tasks = []
    for index, (name, role, criterion) in enumerate(order_steps(session, unit)):
        task = Task(project_id=project.id, plan_id=plan.id,
                    title=f"{index + 1}. {name}: {brief['title']}"[:200],
                    description=(f"Cel projektu: {brief['goal']}\nOdbiorcy: {brief['audience']}\n"
                                 f"Ograniczenia: {brief['constraints']}\n"
                                 "Kryteria produktu:\n- " + "\n- ".join(brief["acceptance_criteria"]) +
                                 f"\nKryterium etapu: {criterion}\n"
                                 "Nie deklaruj testów, publikacji ani wykonania kodu bez dowodów. "
                                 "Najpierw odbierz wcześniejsze etapy. Zakaz ingerencji w host i wynajem Vast.ai."),
                    assigned_agent=role, status=TaskStatus.PENDING,
                    approval_status=ApprovalStatus.PENDING, resource_class=ResourceClass.CPU,
                    risk_level=RiskLevel.MEDIUM, progress=0, queued_at=None)
        session.add(task)
        tasks.append(task)
    session.flush()
    order = WorkOrder(request_id=request_id, request_hash=fingerprint(brief),
                      project_id=project.id, plan_id=plan.id, brief=brief,
                      task_ids=[task.id for task in tasks])
    session.add(order)
    session.add(AuditEvent(event_type="work_order", operation="create", decision="planned",
                           allowed=True, reason=f"owner; project={project.id}; plan={plan.id}; tasks={order.task_ids}; execution=not_started"))
    session.flush()
    return order


def website_starter(brief: dict) -> dict[str, str]:
    """Own fixed HTML/CSS template; brief data is escaped, never executable code."""
    title, goal, audience = (escape(brief[key], quote=True) for key in ("title", "goal", "audience"))
    html = f'''<!doctype html>
<html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'self'; base-uri 'none'; form-action 'none'">
<title>{title}</title><link rel="stylesheet" href="styles.css"></head><body>
<a class="skip" href="#main">Przejdź do treści</a>
<header><a href="#main">{title}</a><nav aria-label="Nawigacja"><a href="#about">O projekcie</a></nav></header>
<main id="main"><section class="hero"><p class="eyebrow">WERSJA ROBOCZA · DO ODBIORU</p>
<h1>{title}</h1><p class="lead">{goal}</p><a class="cta" href="#about">Poznaj projekt <span aria-hidden="true">↗</span></a></section>
<section id="about"><p class="eyebrow">DLA KOGO</p><h2>Stworzone z myślą o odbiorcach</h2><p>{audience}</p>
<p class="note">To szkielet strony. Treści, identyfikacja, funkcje i dane kontaktowe wymagają uzupełnienia oraz weryfikacji.</p></section></main>
<footer>Projekt roboczy — bez formularzy, analityki i połączeń zewnętrznych.</footer></body></html>'''
    css = '''*{box-sizing:border-box}html{scroll-behavior:smooth;color-scheme:light dark}body{margin:0;background:#eeefe7;color:#172c2a;font:18px/1.6 system-ui,sans-serif}header,main,footer{max-width:1180px;margin:auto;padding:28px clamp(22px,6vw,80px)}header{display:flex;justify-content:space-between;gap:24px;border-bottom:1px solid #82938a}a{color:inherit;text-underline-offset:5px}a:focus-visible{outline:3px solid #bd6815;outline-offset:6px}.hero{padding:90px 0 120px;max-width:960px}h1{font-size:clamp(42px,8vw,100px);line-height:1.04;letter-spacing:-.045em;overflow-wrap:anywhere}h2{font-size:clamp(28px,5vw,48px);line-height:1.15}.lead{max-width:700px;font-size:clamp(20px,3vw,28px);white-space:pre-wrap;overflow-wrap:anywhere}.eyebrow{font-size:12px;letter-spacing:.2em}.cta{display:inline-block;background:#173d35;color:white;border-radius:40px;padding:16px 28px;margin-top:20px;text-decoration:none}#about{border-top:1px solid #82938a;padding:48px 0 90px;overflow-wrap:anywhere}.note,footer{font-size:14px}.skip{position:absolute;left:20px;top:-100px}.skip:focus{top:10px;background:white;color:black;padding:8px}footer{border-top:1px solid #82938a}@media(prefers-color-scheme:dark){body{background:#101f1d;color:#e4ece3}.cta{background:#b2dac6;color:#101f1d}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}'''
    return {"index.html": html, "styles.css": css,
            "brief.json": json.dumps(brief, indent=2, ensure_ascii=True),
            "README.md": ("# Szkielet strony\n\nŹródło: lokalny szablon AI Company, nie wynik modelu AI.\n"
                          "Nie wykonywano kodu, testów tej realizacji ani publikacji. Nie jest to odebrany produkt.\n"
                          "Otwórz index.html po pobraniu i rozpakowaniu ZIP w osobnym folderze.\n"
                          "Brak zależności do instalacji, skryptów, zewnętrznych fontów i żądań sieciowych.\n"
                          "Następnie dopracuj treść, design i funkcje według brief.json.\n"
                          "Przed odbiorem sprawdź klawiaturę, telefon, oba motywy, treści i wymagania.\n")}
