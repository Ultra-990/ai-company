"""Deterministic organizational staffing. No model, network, queue or process calls."""
from hashlib import sha256

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.models.delegation import TaskDelegation
from app.models.organization import OrganizationUnit
from app.models.organization_os import Agent
from app.models.project import Project
from app.models.task import Task, TaskAttempt, TaskStatus
from app.models.work_order import WorkOrder
from app.models.local_inference import LocalInference
from app.organization_os.department_profiles import role_profile
from app.organization_os.department_operations import operating_model
from app.services.work_orders import STEPS, stored_criterion

PROFILE = "department-team.v1"
ROLES = {
    "manager": "Kierownik działu", "analyst": "Analityk wymagań",
    "builder": "Wykonawca", "tester": "Inżynier testów",
    "delivery": "Koordynator przekazania", "reviewer": "Niezależny kontroler",
}
STAGE_ROLES = ("analyst", "builder", "tester", "delivery")
POLICY = {"execution_enabled": False, "allowed_tools": [], "max_cost": 0,
          "requires_resource_approval": True, "final_acceptance": "owner",
          "external_actions": False}


def team_key(department_id, role):
    return f"team.{department_id}.{role}"


def initialize_teams(session: Session) -> int:
    """Caller owns transaction. Stable keys and no overwrites of customized agents."""
    root = session.scalar(select(OrganizationUnit).where(OrganizationUnit.os_key == "ai-company"))
    brain = session.scalar(select(Agent).where(Agent.agent_key == "brain-core"))
    if not root or not brain or not brain.active:
        raise ValueError("Brakuje aktywnej struktury firmy lub Brain.")
    if root.brain_agent_id != brain.id:
        raise ValueError("Przypisanie Brain w korzeniu wymaga uzgodnienia z rejestrem agentów.")
    departments = list(session.scalars(select(OrganizationUnit).where(
        OrganizationUnit.parent_id == root.id, OrganizationUnit.active.is_(True)).order_by(OrganizationUnit.id)))
    created = 0
    for department in departments:
        manager = None
        for role, title in ROLES.items():
            key = team_key(department.id, role)
            agent = session.scalar(select(Agent).where(Agent.agent_key == key))
            if agent is None:
                supervisor = brain.id if role in {"manager", "reviewer"} else manager.id
                agent = Agent(agent_key=key, name=f"{title} · {department.name}"[:200],
                              kind="ai", active=True, capabilities=[role],
                              description="Zarejestrowana rola. Brak uruchomionej sesji modelu; kompetencje wymagają weryfikacji.",
                              metadata_json={"profile": PROFILE, "department_id": department.id,
                                             "role": role, "supervisor_id": supervisor,
                                             "runtime_status": "not_started", "policy": dict(POLICY)})
                session.add(agent)
                session.flush()
                created += 1
            elif agent.metadata_json.get("profile") != PROFILE or agent.metadata_json.get("department_id") != department.id or agent.metadata_json.get("role") != role:
                raise ValueError("Klucz agenta jest zajęty przez inną konfigurację. Niczego nie nadpisano.")
            if role == "manager":
                manager = agent
        if department.manager_agent in (None, "brain-core", manager.agent_key):
            department.manager_agent = manager.agent_key
    if created:
        session.add(AuditEvent(event_type="agent_team", operation="initialize", decision="configured",
                               allowed=True, reason=f"owner; created={created}; execution=disabled"))
    return created


def roster(session: Session) -> dict:
    units = {u.id: u for u in session.scalars(select(OrganizationUnit))}
    agents = list(session.scalars(select(Agent).order_by(Agent.id)))
    workloads, states = team_activity(session)
    teams = {}
    for agent in agents:
        metadata = agent.metadata_json
        if metadata.get("profile") != PROFILE:
            continue
        unit = units.get(metadata.get("department_id"))
        if not unit:
            continue
        team = teams.setdefault(unit.id, {"department_id": unit.id, "department": unit.name,
                                         "department_key": unit.os_key,
                                         "charter": operating_model(unit.os_key),
                                         "active": unit.active, "agents": []})
        activity = states.get(agent.id, {})
        runtime = next((state for state in ('uncertain','running','queued','awaiting_review','rejected','failed','stale') if activity.get(state)),
                       'idle' if activity else 'not_started')
        team["agents"].append({"id": agent.id, "key": agent.agent_key, "name": agent.name,
                               "role": metadata.get("role"), "role_title": ROLES.get(metadata.get("role"), "Rola"),
                               "supervisor_id": metadata.get("supervisor_id"), "active": agent.active,
                               "runtime_status": runtime,
                               "assigned_tasks": workloads.get(agent.id,0),
                               "latest_run_states": activity,
                               "specialization": role_profile(unit.os_key,metadata.get('role'))})
    return {"teams": list(teams.values()), "policy": POLICY,
            "note": "Jeden lokalny Qwen uruchamiany dla konkretnego zadania. Stany pochodzą z rejestru wykonań, nie z monitorowania procesów. Kierownik koordynuje, końcowy odbiór wykonuje właściciel."}


def team_activity(session):
    """Bounded aggregate queries, no result/brief bodies. Current assignment workload."""
    workloads = {}
    for manager, worker, reviewer, count in session.execute(select(
            TaskDelegation.manager_id,TaskDelegation.worker_id,TaskDelegation.reviewer_id,func.count())
            .group_by(TaskDelegation.manager_id,TaskDelegation.worker_id,TaskDelegation.reviewer_id)):
        for actor in {manager,worker,reviewer}:
            workloads[actor]=workloads.get(actor,0)+count
    latest = select(LocalInference.task_id,func.max(LocalInference.id).label('run_id')).group_by(LocalInference.task_id).subquery()
    rows=session.execute(select(TaskDelegation.worker_id,LocalInference.state,TaskAttempt.verification_status,func.count())
        .join(LocalInference,LocalInference.task_id==TaskDelegation.task_id)
        .join(latest,latest.c.run_id==LocalInference.id)
        .outerjoin(TaskAttempt,TaskAttempt.id==LocalInference.attempt_id)
        .group_by(TaskDelegation.worker_id,LocalInference.state,TaskAttempt.verification_status))
    states={}
    for worker,state,verification,count in rows:
        if state=='awaiting_review' and verification in {'accepted','rejected'}:
            state=verification
        counts=states.setdefault(worker,{})
        counts[state]=counts.get(state,0)+count
    return workloads,states


def department_work(session, department_id, before=None):
    unit=session.get(OrganizationUnit,department_id)
    if not unit or not session.scalar(select(Agent.id).where(Agent.agent_key==team_key(department_id,'manager'))):
        raise LookupError('Nie znaleziono zespołu działu.')
    query=select(Task).join(TaskDelegation,Task.id==TaskDelegation.task_id).where(
        TaskDelegation.department_id==department_id).order_by(Task.id.desc())
    if before is not None:query=query.where(Task.id<before)
    rows=list(session.scalars(query.limit(21)))
    tasks=[]
    for task in rows[:20]:
        delegation=delegation_details(session,task)
        run=session.execute(select(LocalInference.id,LocalInference.state,LocalInference.started_at)
                            .where(LocalInference.task_id==task.id).order_by(LocalInference.id.desc()).limit(1)).first()
        tasks.append({'task_id':task.id,'project_id':task.project_id,'title':task.title,'status':task.status.value,
                      'worker':delegation['worker'],'reviewer':delegation['reviewer'],
                      'planning_blockers':delegation['planning_blockers'],
                      'run':({'id':run.id,'state':run.state,'started_at':run.started_at.isoformat() if run.started_at else None} if run else None),
                      'work_url':f'/os/work?project={task.project_id}'})
    return {'department_id':unit.id,'department':unit.name,'tasks':tasks,
            'next_cursor':rows[19].id if len(rows)>20 else None,'automatically_started':False}


def department_for(session, unit_id):
    seen = set()
    while unit_id:
        if unit_id in seen:
            raise ValueError("Cykl w strukturze organizacji.")
        seen.add(unit_id)
        unit = session.get(OrganizationUnit, unit_id)
        if not unit or not unit.active:
            raise ValueError("Nieaktywny lub brakujący węzeł struktury.")
        parent = session.get(OrganizationUnit, unit.parent_id) if unit.parent_id else None
        if parent and parent.os_key == "ai-company":
            return unit
        unit_id = unit.parent_id
    raise ValueError("Projekt nie należy do działu firmy.")


def delegate_order(session: Session, order: WorkOrder) -> None:
    project = session.get(Project, order.project_id)
    department = department_for(session, project.organization_unit_id)
    if len(order.task_ids) != len(STEPS):
        raise ValueError("Zlecenie nie ma obsługiwanych czterech etapów.")
    agents = {}
    for role in ROLES:
        agent = session.scalar(select(Agent).where(Agent.agent_key == team_key(department.id, role)))
        if (not agent or not agent.active or agent.metadata_json.get("profile") != PROFILE
                or agent.metadata_json.get("department_id") != department.id
                or agent.metadata_json.get("role") != role):
            raise ValueError("Najpierw przygotuj aktywny zespół działu.")
        agents[role] = agent
    if department.manager_agent != agents["manager"].agent_key:
        raise ValueError("Dział ma indywidualnego kierownika. Wymagana jawna rewizja przydziału.")
    created = 0
    for index, task_id in enumerate(order.task_ids):
        task = session.get(Task, task_id)
        if task is None or task.project_id != order.project_id or task.plan_id != order.plan_id:
            raise ValueError("Niespójne powiązanie zadania ze zleceniem.")
        previous = session.get(TaskDelegation, task_id)
        if previous:
            # Replays never reassign or queue existing work.
            continue
        if task.status != TaskStatus.PENDING or task.queued_at is not None or session.scalar(
                select(TaskAttempt.id).where(TaskAttempt.task_id == task_id).limit(1)):
            raise ValueError("Przydział dotyczy wyłącznie nierozpoczętych zadań poza kolejką.")
        worker, reviewer = agents[STAGE_ROLES[index]], agents["reviewer"]
        session.add(TaskDelegation(task_id=task_id, department_id=department.id,
                                  manager_id=agents["manager"].id, worker_id=worker.id, reviewer_id=reviewer.id,
                                  predecessor_id=order.task_ids[index-1] if index else None,
                                  execution_brief=task.description or "", completion_criterion=stored_criterion(task, index),
                                  policy=dict(POLICY)))
        task.assigned_agent = worker.agent_key
        created += 1
    if created:
        session.add(AuditEvent(event_type="task_delegation", operation="assign_order", decision="planned",
                               allowed=True, reason=f"owner; project={order.project_id}; tasks={created}; execution=disabled"))
    session.flush()


def delegation_details(session: Session, task: Task) -> dict | None:
    assignment = session.get(TaskDelegation, task.id)
    if not assignment:
        return None
    blockers = []
    actors = {}
    for role in ("manager", "worker", "reviewer"):
        agent = session.get(Agent, getattr(assignment, role + "_id"))
        actors[role] = {"id": agent.id, "name": agent.name, "key": agent.agent_key} if agent else None
        if not agent or not agent.active:
            blockers.append(f"Nieaktywny lub brakujący {role}.")
    if assignment.worker_id == assignment.reviewer_id:
        blockers.append("Wykonawca nie może sam odebrać swojej pracy.")
    if actors["worker"] and task.assigned_agent != actors["worker"]["key"]:
        blockers.append("Przypisanie zadania zmieniono poza delegacją.")
    if (task.description or "") != assignment.execution_brief:
        blockers.append("Zakres zadania zmieniono po delegacji; potrzebny ponowny przegląd.")
    unit = session.get(OrganizationUnit, assignment.department_id)
    if not unit or not unit.active:
        blockers.append("Dział jest nieaktywny.")
    if assignment.predecessor_id:
        predecessor = session.get(Task, assignment.predecessor_id)
        latest = session.scalar(select(TaskAttempt).where(TaskAttempt.task_id == assignment.predecessor_id)
                                .order_by(TaskAttempt.id.desc()).limit(1))
        accepted = (predecessor and predecessor.status == TaskStatus.COMPLETED and latest and latest.status == "completed"
                    and latest.verification_status == "accepted" and latest.verified_at
                    and latest.result_content and latest.result_checksum == sha256(latest.result_content.encode()).hexdigest())
        if not accepted:
            blockers.append(f"Najpierw odbierz wynik zadania #{assignment.predecessor_id}.")
    return {**actors, "department_id": assignment.department_id,
            "predecessor_id": assignment.predecessor_id, "completion_criterion": assignment.completion_criterion,
            "execution_brief": assignment.execution_brief, "planning_blockers": blockers,
            "planning_ready": not blockers, "execution_enabled": False,
            "execution_hold": "Przydział nie uruchamia AI. Przygotuj instrukcję gotowego etapu i jawnie uruchom lokalny Qwen; kod i testy wymagają profilu izolowanego wykonania.",
            "policy": assignment.policy}
