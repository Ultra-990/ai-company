from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime, timezone
import json

from sqlalchemy import text

from app.core.config import load_settings
from app.core.database import create_database_engine

PROJECT_NAME = "Organization OS — fundamenty"
ORGANIZATION_UNIT_ID = 6

TASKS = [
    {
        "title": "OS: model danych i migracje",
        "description": (
            "Utworzenie modeli Organization OS, migracji SQLite oraz "
            "podstawowych encji dla struktury organizacyjnej."
        ),
        "status": "COMPLETED",
        "priority": "HIGH",
        "progress": 100,
        "resource_class": "CPU",
        "risk_level": "LOW",
    },
    {
        "title": "OS: API drzewa organizacyjnego",
        "description": (
            "Udostępnienie endpointów overview, tree, alerts, next-move "
            "oraz preferencji workspace."
        ),
        "status": "COMPLETED",
        "priority": "HIGH",
        "progress": 100,
        "resource_class": "CPU",
        "risk_level": "LOW",
    },
    {
        "title": "OS: kontrakt danych dla frontendu",
        "description": (
            "Przygotowanie stabilnych typów i kontraktów danych dla "
            "interaktywnego frontendu Organization OS."
        ),
        "status": "IN_PROGRESS",
        "priority": "HIGH",
        "progress": 65,
        "resource_class": "CPU",
        "risk_level": "MEDIUM",
    },
    {
        "title": "OS: scena React i silnik okien",
        "description": (
            "Budowa sceny interaktywnej, systemu podglądów, otwierania, "
            "minimalizacji i maksymalizacji okien działów."
        ),
        "status": "PENDING",
        "priority": "HIGH",
        "progress": 0,
        "resource_class": "CPU_HEAVY",
        "risk_level": "MEDIUM",
    },
    {
        "title": "OS: integracja danych 3D i alertów",
        "description": (
            "Powiązanie sceny z API, mapowanie postępu działów oraz "
            "wizualizacja alertów i rekomendacji Brain Core."
        ),
        "status": "BLOCKED",
        "priority": "NORMAL",
        "progress": 15,
        "resource_class": "CPU_HEAVY",
        "risk_level": "HIGH",
    },
]

settings = load_settings()
engine = create_database_engine(settings.database.url)
now = datetime.now(timezone.utc).replace(tzinfo=None)

with engine.begin() as connection:
    project = connection.execute(
        text("""
            SELECT id, name, status, organization_unit_id
            FROM projects
            WHERE name = :name
              AND organization_unit_id = :organization_unit_id
            LIMIT 1
        """),
        {
            "name": PROJECT_NAME,
            "organization_unit_id": ORGANIZATION_UNIT_ID,
        },
    ).mappings().first()

    if project:
        project_id = project["id"]
        print(
            f"Projekt już istnieje: ID={project_id}, "
            f"status={project['status']}, "
            f"organization_unit_id={project['organization_unit_id']}"
        )
    else:
        result = connection.execute(
            text("""
                INSERT INTO projects (
                    name,
                    business_goal,
                    description,
                    status,
                    organization_unit_id,
                    created_at,
                    updated_at,
                    started_at,
                    completed_at
                )
                VALUES (
                    :name,
                    :business_goal,
                    :description,
                    :status,
                    :organization_unit_id,
                    :created_at,
                    :updated_at,
                    :started_at,
                    NULL
                )
            """),
            {
                "name": PROJECT_NAME,
                "business_goal": (
                    "Zbudowanie fundamentów Organization OS: trwałego modelu "
                    "danych, API drzewa organizacyjnego oraz podstaw integracji "
                    "z interaktywnym frontendem."
                ),
                "description": (
                    "Projekt kontrolny służący do weryfikacji przepływu: "
                    "dział → projekt → zadania → weighted progress → API."
                ),
                "status": "IN_PROGRESS",
                "organization_unit_id": ORGANIZATION_UNIT_ID,
                "created_at": now,
                "updated_at": now,
                "started_at": now,
            },
        )
        project_id = result.lastrowid
        print(f"Utworzono projekt: ID={project_id}")

    created_count = 0
    existing_count = 0

    for task in TASKS:
        existing = connection.execute(
            text("""
                SELECT id
                FROM tasks
                WHERE title = :title
                  AND project_id = :project_id
                LIMIT 1
            """),
            {
                "title": task["title"],
                "project_id": project_id,
            },
        ).scalar()

        if existing:
            existing_count += 1
            print(f"  ↳ Zadanie już istnieje: ID={existing} | {task['title']}")
            continue

        completed_at = now if task["status"] == "COMPLETED" else None
        started_at = (
            now
            if task["status"] in {"COMPLETED", "IN_PROGRESS", "BLOCKED"}
            else None
        )

        connection.execute(
            text("""
                INSERT INTO tasks (
                    title,
                    description,
                    status,
                    priority,
                    assigned_agent,
                    created_at,
                    updated_at,
                    progress,
                    stages,
                    resource_class,
                    risk_level,
                    queued_at,
                    started_at,
                    completed_at,
                    approval_status,
                    project_id,
                    plan_id,
                    roadmap_item_id
                )
                VALUES (
                    :title,
                    :description,
                    :status,
                    :priority,
                    NULL,
                    :created_at,
                    :updated_at,
                    :progress,
                    :stages,
                    :resource_class,
                    :risk_level,
                    :queued_at,
                    :started_at,
                    :completed_at,
                    'APPROVED',
                    :project_id,
                    NULL,
                    NULL
                )
            """),
            {
                **task,
                "created_at": now,
                "updated_at": now,
                "queued_at": now,
                "started_at": started_at,
                "completed_at": completed_at,
                "stages": json.dumps([]),
                "project_id": project_id,
            },
        )
        created_count += 1
        print(
            f"  ✓ Utworzono: {task['status']:11} "
            f"{task['progress']:3}% | {task['title']}"
        )

    summary = connection.execute(
        text("""
            SELECT
                COUNT(*) AS task_count,
                ROUND(AVG(progress), 2) AS average_progress,
                SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN status = 'IN_PROGRESS' THEN 1 ELSE 0 END) AS in_progress,
                SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN status = 'BLOCKED' THEN 1 ELSE 0 END) AS blocked
            FROM tasks
            WHERE project_id = :project_id
        """),
        {"project_id": project_id},
    ).mappings().one()

print("\n=== Podsumowanie ===")
print(f"Projekt ID: {project_id}")
print(f"Nowe zadania: {created_count}")
print(f"Istniejące zadania: {existing_count}")
print(f"Liczba zadań w projekcie: {summary['task_count']}")
print(f"Średni postęp zadań: {summary['average_progress']}%")
print(
    "Statusy: "
    f"COMPLETED={summary['completed']}, "
    f"IN_PROGRESS={summary['in_progress']}, "
    f"PENDING={summary['pending']}, "
    f"BLOCKED={summary['blocked']}"
)
