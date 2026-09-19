from __future__ import annotations

from sqlalchemy import Engine, inspect, text

from app.organization_os.taxonomy import (
    LEGACY_DOMAIN_KEYS,
    ORGANIZATION_OS_DOMAINS,
)


def migrate_media_generation_schema(engine: Engine) -> None:
    """Additive media job schema; preserve draft jobs from early live reloads."""
    from app.models.media_generation import MediaGeneration
    MediaGeneration.__table__.create(engine, checkfirst=True)
    columns = {c['name'] for c in inspect(engine).get_columns('media_generations')}
    with engine.begin() as connection:
        if 'project_id' not in columns:
            connection.execute(text('ALTER TABLE media_generations ADD COLUMN project_id INTEGER REFERENCES projects(id)'))
        if 'plan_id' not in columns:
            connection.execute(text('ALTER TABLE media_generations ADD COLUMN plan_id INTEGER REFERENCES plans(id)'))


def migrate_legacy_organization_os_enum_values(engine: Engine) -> None:
    """Normalizuje znane historyczne wartości enumów Organization OS.

    Wczesny inicjalizator Organization OS zapisywał ręcznie nazwy, których
    aktualne enumy SQLAlchemy już nie obsługują. Bez tej migracji samo
    odczytanie zadania lub projektu kończyło się błędem 500. Operacja jest
    idempotentna i nic nie robi, gdy odpowiednie tabele jeszcze nie istnieją.
    """
    tables = set(inspect(engine).get_table_names())

    with engine.begin() as connection:
        if "projects" in tables:
            connection.execute(
                text(
                    """
                    UPDATE projects
                    SET status = 'IN_PROGRESS'
                    WHERE status = 'ACTIVE'
                    """
                )
            )

        if "tasks" in tables:
            connection.execute(
                text(
                    """
                    UPDATE tasks
                    SET resource_class = 'CPU'
                    WHERE resource_class = 'MEDIUM'
                    """
                )
            )
            connection.execute(
                text(
                    """
                    UPDATE tasks
                    SET resource_class = 'CPU_HEAVY'
                    WHERE resource_class = 'HEAVY'
                    """
                )
            )


TASK_QUEUE_COLUMNS = {
    "resource_class": (
        "VARCHAR(32) NOT NULL DEFAULT 'LIGHT'"
    ),
    "risk_level": (
        "VARCHAR(16) NOT NULL DEFAULT 'LOW'"
    ),
    "approval_status": (
        "VARCHAR(16) NOT NULL DEFAULT 'APPROVED'"
    ),
    "queued_at": "DATETIME",
    "started_at": "DATETIME",
    "completed_at": "DATETIME",
}


def migrate_task_queue_schema(engine: Engine) -> None:
    """
    Uzupełnia istniejącą tabelę tasks o pola kolejki.

    Migracja jest idempotentna: można ją bezpiecznie wywoływać przy każdym
    utworzeniu TaskRepository. Nie usuwa ani nie przebudowuje tabeli.
    """
    inspector = inspect(engine)

    if "tasks" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("tasks")
    }

    with engine.begin() as connection:
        for name, definition in TASK_QUEUE_COLUMNS.items():
            if name not in existing_columns:
                connection.execute(
                    text(
                        f"ALTER TABLE tasks "
                        f"ADD COLUMN {name} {definition}"
                    )
                )

        connection.execute(
            text(
                """
                UPDATE tasks
                SET resource_class = 'LIGHT'
                WHERE resource_class IS NULL
                   OR TRIM(resource_class) = ''
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE tasks
                SET risk_level = 'LOW'
                WHERE risk_level IS NULL
                   OR TRIM(risk_level) = ''
                """
            )
        )
        # Backfill only while introducing the column. NULL in a current
        # schema deliberately means "not queued" (e.g. a draft work order).
        # Reopening a repository must never silently enqueue held tasks.
        if "queued_at" not in existing_columns:
            connection.execute(
                text(
                    """
                    UPDATE tasks
                    SET queued_at = created_at
                    WHERE queued_at IS NULL
                    """
                )
            )
        connection.execute(
            text(
                """
                UPDATE tasks
                SET started_at = updated_at
                WHERE status = 'IN_PROGRESS'
                  AND started_at IS NULL
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE tasks
                SET completed_at = updated_at
                WHERE status = 'COMPLETED'
                  AND completed_at IS NULL
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_tasks_resource_class
                ON tasks (resource_class)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_tasks_risk_level
                ON tasks (risk_level)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_tasks_queued_at
                ON tasks (queued_at)
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE tasks
                SET approval_status = 'APPROVED'
                WHERE approval_status IS NULL
                   OR TRIM(approval_status) = ''
                """
            )
        )


TASK_ROADMAP_ITEM_COLUMNS = {
    "roadmap_item_id": "VARCHAR(200)",
}


def migrate_task_roadmap_item_schema(engine: Engine) -> None:
    """
    Dodaje opcjonalne przypisanie zadania do punktu roadmapy.

    Migracja jest idempotentna. Nie tworzy klucza obcego, ponieważ
    źródłem prawdy punktów roadmapy jest docs/roadmap.yaml.
    """
    inspector = inspect(engine)

    if "tasks" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("tasks")
    }

    with engine.begin() as connection:
        for name, definition in TASK_ROADMAP_ITEM_COLUMNS.items():
            if name not in existing_columns:
                connection.execute(
                    text(
                        "ALTER TABLE tasks "
                        f"ADD COLUMN {name} {definition}"
                    )
                )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_tasks_roadmap_item_id
                ON tasks (roadmap_item_id)
                """
            )
        )


APPROVAL_REQUEST_COLUMNS = {
    "tool_name": "VARCHAR(128)",
    "arguments_digest": "VARCHAR(64)",
    "executed_at": "DATETIME",
}


def migrate_approval_request_schema(engine: Engine) -> None:
    """
    Dodaje pola kontraktu wykonania narzędzi do approval_requests.

    Migracja jest idempotentna i pozostawia historyczne rekordy bez zmian.
    """
    inspector = inspect(engine)

    if "approval_requests" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("approval_requests")
    }

    with engine.begin() as connection:
        for name, definition in APPROVAL_REQUEST_COLUMNS.items():
            if name not in existing_columns:
                connection.execute(
                    text(
                        "ALTER TABLE approval_requests "
                        f"ADD COLUMN {name} {definition}"
                    )
                )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_approval_requests_tool_name
                ON approval_requests (tool_name)
                """
            )
        )


def migrate_pending_tool_execution_schema(engine: Engine) -> None:
    """
    Tworzy trwały magazyn argumentów oczekujących wykonań narzędzi.

    Migracja jest idempotentna i bezpieczna dla istniejących baz SQLite.
    """
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS pending_tool_executions (
                    id INTEGER PRIMARY KEY,
                    approval_request_id INTEGER NOT NULL UNIQUE,
                    tool_name VARCHAR(128) NOT NULL,
                    arguments_json TEXT NOT NULL,
                    arguments_digest VARCHAR(64) NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS
                ix_pending_tool_executions_approval_request_id
                ON pending_tool_executions (approval_request_id)
                """
            )
        )


TASK_ATTEMPT_VERIFICATION_COLUMNS = {
    "result_content": "TEXT",
    "result_checksum": "VARCHAR(64)",
    "verification_status": (
        "VARCHAR(20) NOT NULL DEFAULT 'pending'"
    ),
    "verification_reason": "TEXT",
    "verified_at": "DATETIME",
}


def migrate_task_attempt_schema(engine: Engine) -> None:
    """
    Tworzy i aktualizuje trwały rejestr prób wykonania zadań.

    Migracja jest idempotentna i obsługuje zarówno nowe bazy, jak i bazy
    zawierające tabelę task_attempts utworzoną przed fazą 5.
    """
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS task_attempts (
                    id INTEGER PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    worker_id VARCHAR(100) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'started',
                    started_at DATETIME NOT NULL,
                    finished_at DATETIME,
                    error_summary TEXT,
                    result_content TEXT,
                    result_checksum VARCHAR(64),
                    verification_status VARCHAR(20)
                        NOT NULL DEFAULT 'pending',
                    verification_reason TEXT,
                    verified_at DATETIME,
                    FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
                )
                """
            )
        )

        # Inspektor jest tworzony po CREATE TABLE, dzięki czemu obsługujemy
        # też całkowicie nową bazę danych.
        existing_columns = {
            column["name"]
            for column in inspect(engine).get_columns("task_attempts")
        }

        for name, definition in TASK_ATTEMPT_VERIFICATION_COLUMNS.items():
            if name not in existing_columns:
                connection.execute(
                    text(
                        "ALTER TABLE task_attempts "
                        f"ADD COLUMN {name} {definition}"
                    )
                )

        # Historyczne rekordy sprzed fazy 5 nie miały tego pola.
        connection.execute(
            text(
                """
                UPDATE task_attempts
                SET verification_status = 'pending'
                WHERE verification_status IS NULL
                   OR TRIM(verification_status) = ''
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_task_attempts_task_id
                ON task_attempts (task_id)
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_task_attempts_worker_id
                ON task_attempts (worker_id)
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_task_attempts_status
                ON task_attempts (status)
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_task_attempts_result_checksum
                ON task_attempts (result_checksum)
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_task_attempts_verification_status
                ON task_attempts (verification_status)
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_task_attempts_verified_at
                ON task_attempts (verified_at)
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_task_attempts_started_at
                ON task_attempts (started_at)
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_task_attempts_finished_at
                ON task_attempts (finished_at)
                """
            )
        )


def migrate_project_schema(engine: Engine) -> None:
    """
    Tworzy tabelę nadrzędnych agregatów Project.

    Migracja jest idempotentna. Tabela jest tworzona również przez
    Base.metadata.create_all(), lecz jawna migracja zapewnia poprawne
    działanie dla istniejących środowisk i samodzielnych wywołań migracji.
    """
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    business_goal TEXT NOT NULL,
                    description TEXT,
                    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
                    organization_unit_id INTEGER,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    started_at DATETIME,
                    completed_at DATETIME,
                    FOREIGN KEY(organization_unit_id)
                        REFERENCES organization_units(id)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_projects_name
                ON projects (name)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_projects_status
                ON projects (status)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_projects_organization_unit_id
                ON projects (organization_unit_id)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_projects_created_at
                ON projects (created_at)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_projects_started_at
                ON projects (started_at)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_projects_completed_at
                ON projects (completed_at)
                """
            )
        )


def migrate_plan_schema(engine: Engine) -> None:
    """
    Tworzy tabelę planów wykonawczych.

    Migracja jest idempotentna i może być uruchamiana wielokrotnie.
    """
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS plans (
                    id INTEGER PRIMARY KEY,
                    project_id INTEGER NOT NULL,
                    name VARCHAR(200) NOT NULL,
                    objective TEXT NOT NULL,
                    description TEXT,
                    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    started_at DATETIME,
                    completed_at DATETIME,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_plans_project_id
                ON plans (project_id)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_plans_name
                ON plans (name)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_plans_status
                ON plans (status)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_plans_created_at
                ON plans (created_at)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_plans_started_at
                ON plans (started_at)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_plans_completed_at
                ON plans (completed_at)
                """
            )
        )


def migrate_task_project_plan_schema(engine: Engine) -> None:
    """
    Uzupełnia istniejącą tabelę tasks o opcjonalne powiązania domenowe.

    Kolumny pozostają nullable, aby dotychczasowe zadania techniczne mogły
    działać bez przypisania do projektu lub planu. Migracja obsługuje SQLite
    oraz PostgreSQL i może być wykonywana wielokrotnie.
    """
    with engine.begin() as connection:
        dialect = connection.dialect.name

        if dialect == "sqlite":
            columns = {
                row[1]
                for row in connection.execute(
                    text("PRAGMA table_info(tasks)")
                )
            }

            if "project_id" not in columns:
                connection.execute(
                    text(
                        """
                        ALTER TABLE tasks
                        ADD COLUMN project_id INTEGER
                        REFERENCES projects(id)
                        """
                    )
                )

            if "plan_id" not in columns:
                connection.execute(
                    text(
                        """
                        ALTER TABLE tasks
                        ADD COLUMN plan_id INTEGER
                        REFERENCES plans(id)
                        """
                    )
                )
        else:
            connection.execute(
                text(
                    """
                    ALTER TABLE tasks
                    ADD COLUMN IF NOT EXISTS project_id INTEGER
                    REFERENCES projects(id)
                    """
                )
            )
            connection.execute(
                text(
                    """
                    ALTER TABLE tasks
                    ADD COLUMN IF NOT EXISTS plan_id INTEGER
                    REFERENCES plans(id)
                    """
                )
            )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_tasks_project_id
                ON tasks (project_id)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_tasks_plan_id
                ON tasks (plan_id)
                """
            )
        )


def migrate_artifact_schema(engine: Engine) -> None:
    """
    Tworzy trwały rejestr audytowalnych artefaktów workflow.

    Migracja jest idempotentna i bezpieczna dla SQLite oraz PostgreSQL.
    """
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY,
                    project_id INTEGER,
                    plan_id INTEGER,
                    task_id INTEGER,
                    task_attempt_id INTEGER,
                    artifact_type VARCHAR(32) NOT NULL DEFAULT 'other',
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    uri VARCHAR(2048),
                    content TEXT,
                    checksum VARCHAR(64),
                    created_by VARCHAR(100),
                    created_at DATETIME NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id),
                    FOREIGN KEY(plan_id) REFERENCES plans(id),
                    FOREIGN KEY(task_id) REFERENCES tasks(id),
                    FOREIGN KEY(task_attempt_id)
                        REFERENCES task_attempts(id)
                )
                """
            )
        )

        indexes = {
            "ix_artifacts_project_id": "project_id",
            "ix_artifacts_plan_id": "plan_id",
            "ix_artifacts_task_id": "task_id",
            "ix_artifacts_task_attempt_id": "task_attempt_id",
            "ix_artifacts_artifact_type": "artifact_type",
            "ix_artifacts_name": "name",
            "ix_artifacts_checksum": "checksum",
            "ix_artifacts_created_by": "created_by",
            "ix_artifacts_created_at": "created_at",
        }

        for index_name, column_name in indexes.items():
            connection.execute(
                text(
                    f"CREATE INDEX IF NOT EXISTS {index_name} "
                    f"ON artifacts ({column_name})"
                )
            )


def migrate_roadmap_item_state_schema(engine: Engine) -> None:
    """
    Tworzy trwały magazyn stanów punktów roadmapy.

    Struktura roadmapy, w tym identyfikatory, nazwy, zależności i wagi,
    pozostaje w docs/roadmap.yaml. Tabela przechowuje wyłącznie stan
    operacyjny punktu oraz jego dowody i notatki.
    """
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS roadmap_item_states (
                    item_id VARCHAR(200) PRIMARY KEY,
                    status VARCHAR(20) NOT NULL DEFAULT 'planned',
                    evidence TEXT,
                    note TEXT,
                    updated_at DATETIME NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_roadmap_item_states_status
                ON roadmap_item_states (status)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_roadmap_item_states_updated_at
                ON roadmap_item_states (updated_at)
                """
            )
        )


ORGANIZATION_OS_UNIT_COLUMNS = {
    "os_key": "VARCHAR(64)",
    "status": "VARCHAR(32) NOT NULL DEFAULT 'planned'",
    "weight": "INTEGER NOT NULL DEFAULT 1",
    "sort_order": "INTEGER NOT NULL DEFAULT 0",
    "icon": "VARCHAR(64)",
    "color": "VARCHAR(32)",
    "owner_agent_id": "INTEGER",
    "brain_agent_id": "INTEGER",
}


def migrate_organization_os_schema(engine: Engine) -> None:
    """
    Instaluje fundament danych Organization OS.

    Migracja jest idempotentna i nie przebudowuje tabel historycznych.
    Istniejące organization_units zostają zachowane, a nowe pola otrzymują
    bezpieczne wartości domyślne.
    """
    inspector = inspect(engine)

    with engine.begin() as connection:
        if "organization_units" in inspector.get_table_names():
            existing_columns = {
                column["name"]
                for column in inspector.get_columns("organization_units")
            }

            for name, definition in ORGANIZATION_OS_UNIT_COLUMNS.items():
                if name not in existing_columns:
                    connection.execute(
                        text(
                            "ALTER TABLE organization_units "
                            f"ADD COLUMN {name} {definition}"
                        )
                    )

            connection.execute(
                text(
                    """
                    UPDATE organization_units
                    SET status = 'planned'
                    WHERE status IS NULL OR TRIM(status) = ''
                    """
                )
            )
            connection.execute(
                text(
                    """
                    UPDATE organization_units
                    SET weight = 1
                    WHERE weight IS NULL OR weight < 1
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS
                    ix_organization_units_os_key
                    ON organization_units (os_key)
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS
                    ix_organization_units_status
                    ON organization_units (status)
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS
                    ix_organization_units_sort_order
                    ON organization_units (sort_order)
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS
                    ix_organization_units_owner_agent_id
                    ON organization_units (owner_agent_id)
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS
                    ix_organization_units_brain_agent_id
                    ON organization_units (brain_agent_id)
                    """
                )
            )

        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS agents (
                    id INTEGER PRIMARY KEY,
                    agent_key VARCHAR(100) NOT NULL UNIQUE,
                    name VARCHAR(200) NOT NULL,
                    kind VARCHAR(32) NOT NULL DEFAULT 'ai',
                    description TEXT,
                    active BOOLEAN NOT NULL DEFAULT 1,
                    capabilities JSON NOT NULL DEFAULT '[]',
                    metadata_json JSON NOT NULL DEFAULT '{}',
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY,
                    organization_unit_id INTEGER,
                    project_id INTEGER,
                    task_id INTEGER,
                    agent_id INTEGER,
                    severity VARCHAR(16) NOT NULL DEFAULT 'info',
                    status VARCHAR(16) NOT NULL DEFAULT 'open',
                    title VARCHAR(200) NOT NULL,
                    message TEXT NOT NULL,
                    source VARCHAR(100),
                    resolution_note TEXT,
                    created_at DATETIME NOT NULL,
                    acknowledged_at DATETIME,
                    resolved_at DATETIME,
                    FOREIGN KEY(organization_unit_id)
                        REFERENCES organization_units(id),
                    FOREIGN KEY(project_id) REFERENCES projects(id),
                    FOREIGN KEY(task_id) REFERENCES tasks(id),
                    FOREIGN KEY(agent_id) REFERENCES agents(id)
                )
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS workspace_preferences (
                    id INTEGER PRIMARY KEY,
                    workspace_key VARCHAR(100) NOT NULL UNIQUE,
                    theme VARCHAR(32) NOT NULL DEFAULT 'arctic-light',
                    scene_preferences JSON NOT NULL DEFAULT '{}',
                    window_state JSON NOT NULL DEFAULT '{}',
                    updated_at DATETIME NOT NULL
                )
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS organization_unit_dependencies (
                    id INTEGER PRIMARY KEY,
                    source_unit_id INTEGER NOT NULL,
                    target_unit_id INTEGER NOT NULL,
                    relation_type VARCHAR(32) NOT NULL DEFAULT 'depends_on',
                    description TEXT,
                    active BOOLEAN NOT NULL DEFAULT 1,
                    created_at DATETIME NOT NULL,
                    UNIQUE(source_unit_id, target_unit_id, relation_type),
                    FOREIGN KEY(source_unit_id) REFERENCES organization_units(id),
                    FOREIGN KEY(target_unit_id) REFERENCES organization_units(id)
                )
                """
            )
        )

        indexes = {
            "ix_agents_agent_key": "agents (agent_key)",
            "ix_agents_name": "agents (name)",
            "ix_agents_kind": "agents (kind)",
            "ix_agents_active": "agents (active)",
            "ix_agents_created_at": "agents (created_at)",
            "ix_agents_updated_at": "agents (updated_at)",
            "ix_alerts_organization_unit_id": "alerts (organization_unit_id)",
            "ix_alerts_project_id": "alerts (project_id)",
            "ix_alerts_task_id": "alerts (task_id)",
            "ix_alerts_agent_id": "alerts (agent_id)",
            "ix_alerts_severity": "alerts (severity)",
            "ix_alerts_status": "alerts (status)",
            "ix_alerts_title": "alerts (title)",
            "ix_alerts_source": "alerts (source)",
            "ix_alerts_created_at": "alerts (created_at)",
            "ix_alerts_acknowledged_at": "alerts (acknowledged_at)",
            "ix_alerts_resolved_at": "alerts (resolved_at)",
            "ix_workspace_preferences_workspace_key":
                "workspace_preferences (workspace_key)",
            "ix_workspace_preferences_updated_at":
                "workspace_preferences (updated_at)",
            "ix_organization_unit_dependencies_source":
                "organization_unit_dependencies (source_unit_id)",
            "ix_organization_unit_dependencies_target":
                "organization_unit_dependencies (target_unit_id)",
            "ix_organization_unit_dependencies_active":
                "organization_unit_dependencies (active)",
        }

        for index_name, target in indexes.items():
            connection.execute(
                text(
                    f"CREATE INDEX IF NOT EXISTS {index_name} ON {target}"
                )
            )


def migrate_legacy_organization_os_taxonomy(engine: Engine) -> None:
    """Przenosi pierwszy, tymczasowy układ działów do kanonicznej taksonomii.

    Migracja działa wyłącznie na niezmienionych rekordach startowych. Dzięki
    temu późniejsza ręczna edycja nazwy lub struktury przez właściciela nie
    zostanie nadpisana przy kolejnym starcie aplikacji.
    """
    tables = set(inspect(engine).get_table_names())
    if "organization_units" not in tables:
        return

    domain_by_key = {
        domain["key"]: domain
        for domain in ORGANIZATION_OS_DOMAINS
    }
    legacy_titles = {
        "strategy": "Strategia",
        "engineering": "Inżynieria",
        "research": "Research & Intelligence",
        "product": "Produkt",
        "customer-success": "Customer Success",
        "infrastructure": "Infrastruktura",
        "sales": "Sprzedaż",
        "legal": "Prawo & Compliance",
        "operations": "Operacje",
        "marketing": "Marketing",
        "finance": "Finanse",
        "people": "People & Culture",
    }

    with engine.begin() as connection:
        for sort_order, (legacy_key, canonical_key) in enumerate(
            LEGACY_DOMAIN_KEYS.items(),
            start=1,
        ):
            domain = domain_by_key[canonical_key]
            status = "active" if canonical_key == "platform" else "planned"
            connection.execute(
                text(
                    """
                    UPDATE organization_units
                    SET os_key = :canonical_key,
                        name = :name,
                        weight = :weight,
                        sort_order = :sort_order,
                        icon = :icon,
                        color = :color,
                        status = :status
                    WHERE os_key = :legacy_key
                      AND name = :legacy_name
                    """
                ),
                {
                    "canonical_key": canonical_key,
                    "name": domain["title"],
                    "weight": domain["weight"],
                    "sort_order": sort_order,
                    "icon": domain["icon"],
                    "color": domain["color"],
                    "status": status,
                    "legacy_key": legacy_key,
                    "legacy_name": legacy_titles[legacy_key],
                },
            )


def seed_organization_os(engine: Engine) -> None:
    """
    Tworzy minimalną, idempotentną strukturę początkową Organization OS.

    Nie modyfikuje istniejących jednostek. Dodaje wyłącznie rekordy
    rozpoznawane po stabilnym os_key lub agent_key.
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO agents (
                    agent_key, name, kind, description, active,
                    capabilities, metadata_json, created_at, updated_at
                ) VALUES (
                    'owner-core', 'Owner Core', 'owner',
                    'Centrum decyzji strategicznych, finansów i priorytetów.',
                    1, '["strategy","approval","risk"]', '{}', :now, :now
                )
                """
            ),
            {"now": now},
        )
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO agents (
                    agent_key, name, kind, description, active,
                    capabilities, metadata_json, created_at, updated_at
                ) VALUES (
                    'brain-core', 'Brain Core', 'brain',
                    'Niezależny orkiestrator operacyjny i analityczny.',
                    1, '["analysis","delegation","next_move"]', '{}', :now, :now
                )
                """
            ),
            {"now": now},
        )

        owner_id = connection.execute(
            text("SELECT id FROM agents WHERE agent_key = 'owner-core'")
        ).scalar_one()

        brain_id = connection.execute(
            text("SELECT id FROM agents WHERE agent_key = 'brain-core'")
        ).scalar_one()

        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO organization_units (
                    name, unit_type, description, parent_id, manager_agent,
                    active, os_key, status, weight, sort_order, icon, color,
                    owner_agent_id, brain_agent_id, created_at, updated_at
                ) VALUES (
                    'AI Company', 'organization',
                    'Nadrzędna struktura Organization OS.',
                    NULL, 'owner-core', 1, 'ai-company', 'active',
                    100, 0, 'orbit', '#0284C7', :owner_id, :brain_id,
                    :now, :now
                )
                """
            ),
            {
                "owner_id": owner_id,
                "brain_id": brain_id,
                "now": now,
            },
        )

        organization_id = connection.execute(
            text(
                """
                SELECT id
                FROM organization_units
                WHERE os_key = 'ai-company'
                """
            )
        ).scalar_one()

        for order, domain in enumerate(
            ORGANIZATION_OS_DOMAINS,
            start=1,
        ):
            status = "active" if domain["key"] == "platform" else "planned"
            connection.execute(
                text(
                    """
                    INSERT OR IGNORE INTO organization_units (
                        name, unit_type, description, parent_id, manager_agent,
                        active, os_key, status, weight, sort_order, icon, color,
                        owner_agent_id, brain_agent_id, created_at, updated_at
                    ) VALUES (
                        :name, :unit_type, NULL, :parent_id, 'brain-core',
                        1, :os_key, :status, :weight, :sort_order, :icon, :color,
                        :owner_id, :brain_id, :now, :now
                    )
                    """
                ),
                {
                    "name": domain["title"],
                    "unit_type": "division",
                    "parent_id": organization_id,
                    "os_key": domain["key"],
                    "status": status,
                    "weight": domain["weight"],
                    "sort_order": order,
                    "icon": domain["icon"],
                    "color": domain["color"],
                    "owner_id": owner_id,
                    "brain_id": brain_id,
                    "now": now,
                },
            )

            domain_id = connection.execute(
                text(
                    """
                    SELECT id FROM organization_units
                    WHERE os_key = :os_key
                    """
                ),
                {"os_key": domain["key"]},
            ).scalar_one()

            for child_order, (key, name, weight) in enumerate(
                domain["children"],
                start=1,
            ):
                connection.execute(
                    text(
                        """
                        INSERT OR IGNORE INTO organization_units (
                            name, unit_type, description, parent_id,
                            manager_agent, active, os_key, status, weight,
                            sort_order, icon, color, owner_agent_id,
                            brain_agent_id, created_at, updated_at
                        ) VALUES (
                            :name, 'department', NULL, :parent_id,
                            'brain-core', 1, :os_key, 'planned', :weight,
                            :sort_order, :icon, :color, :owner_id, :brain_id,
                            :now, :now
                        )
                        """
                    ),
                    {
                        "name": name,
                        "parent_id": domain_id,
                        "os_key": f"{domain['key']}.{key}",
                        "weight": weight,
                        "sort_order": child_order,
                        "icon": domain["icon"],
                        "color": domain["color"],
                        "owner_id": owner_id,
                        "brain_id": brain_id,
                        "now": now,
                    },
                )

        organization_os_unit_id = connection.execute(
            text(
                """
                SELECT id FROM organization_units
                WHERE os_key = 'platform.organization-os'
                """
            )
        ).scalar_one()
        connection.execute(
            text(
                """
                UPDATE projects
                SET organization_unit_id = :organization_os_unit_id
                WHERE name = 'Organization OS — fundamenty'
                  AND organization_unit_id IS NOT NULL
                """
            ),
            {"organization_os_unit_id": organization_os_unit_id},
        )

        dependencies = (
            ("platform", "strategy", "depends_on", "Platforma realizuje priorytety strategiczne."),
            ("ai-automation", "platform", "depends_on", "Automatyzacje AI korzystają ze wspólnej platformy."),
            ("web-platforms", "platform", "depends_on", "Produkty webowe korzystają z komponentów platformy."),
            ("quality-security", "platform", "depends_on", "Kontrola jakości i bezpieczeństwa obejmuje platformę."),
            ("operations", "quality-security", "depends_on", "Operacje stosują standardy niezawodności i bezpieczeństwa."),
            ("client-services", "business-marketing", "depends_on", "Usługi dla klientów zależą od pozyskania i oferty."),
            ("client-services", "operations", "depends_on", "Dostarczenie usług wymaga gotowych operacji."),
            ("client-services", "finance-legal", "depends_on", "Zlecenia wymagają zasad finansowych i prawnych."),
            ("knowledge-community", "strategy", "depends_on", "Wiedza organizacyjna realizuje decyzje strategiczne."),
        )
        for source_key, target_key, relation_type, description in dependencies:
            connection.execute(
                text(
                    """
                    INSERT OR IGNORE INTO organization_unit_dependencies (
                        source_unit_id, target_unit_id, relation_type,
                        description, active, created_at
                    ) VALUES (
                        (SELECT id FROM organization_units WHERE os_key = :source_key),
                        (SELECT id FROM organization_units WHERE os_key = :target_key),
                        :relation_type, :description, 1, :now
                    )
                    """
                ),
                {
                    "source_key": source_key,
                    "target_key": target_key,
                    "relation_type": relation_type,
                    "description": description,
                    "now": now,
                },
            )

        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO workspace_preferences (
                    workspace_key, theme, scene_preferences, window_state,
                    updated_at
                ) VALUES (
                    'default', 'arctic-light', '{}', '{}', :now
                )
                """
            ),
            {"now": now},
        )
