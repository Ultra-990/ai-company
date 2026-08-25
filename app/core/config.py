from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "settings.yaml"

ALLOWED_ENVIRONMENTS = {"development", "test", "production"}
ALLOWED_AUTONOMY_LEVELS = {"A0", "A1", "A2", "A3"}
ALLOWED_FINANCE_MODES = {"simulation", "live"}
ALLOWED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class ConfigurationError(RuntimeError):
    """Błąd brakującej, nieprawidłowej lub niebezpiecznej konfiguracji."""


@dataclass(frozen=True)
class SystemSettings:
    name: str
    version: str
    environment: str
    language: str
    owner: str


@dataclass(frozen=True)
class ServerSettings:
    host: str
    port: int
    reload: bool


@dataclass(frozen=True)
class AgentSettings:
    enabled: bool
    default_autonomy_level: str
    maximum_autonomy_level: str
    allow_agent_creation: bool
    require_owner_approval: bool
    maximum_task_depth: int
    provider: str = "mock"
    model: str = "test"
    base_url: str | None = None
    timeout_seconds: float = 30.0


@dataclass(frozen=True)
class SafetySettings:
    emergency_stop: bool
    external_actions_enabled: bool
    financial_actions_enabled: bool
    publishing_enabled: bool
    network_access_enabled: bool
    audit_logging_enabled: bool


@dataclass(frozen=True)
class FinanceSettings:
    mode: str
    currency: str
    maximum_single_cost: float
    maximum_project_budget: float


@dataclass(frozen=True)
class DatabaseSettings:
    url: str


@dataclass(frozen=True)
class MemorySettings:
    persistent_memory_enabled: bool
    project_memory_enabled: bool
    experience_memory_enabled: bool
    owner_approval_for_permanent_changes: bool


@dataclass(frozen=True)
class LoggingSettings:
    level: str
    directory: str
    audit_file: str


@dataclass(frozen=True)
class Settings:
    system: SystemSettings
    server: ServerSettings
    agents: AgentSettings
    safety: SafetySettings
    finance: FinanceSettings
    database: DatabaseSettings
    memory: MemorySettings
    logging: LoggingSettings


def _require_section(data: dict[str, Any], section: str) -> dict[str, Any]:
    value = data.get(section)

    if not isinstance(value, dict):
        raise ConfigurationError(
            f"Brak wymaganej sekcji konfiguracji: {section}"
        )

    return value


def _build_settings(data: dict[str, Any]) -> Settings:
    try:
        settings = Settings(
            system=SystemSettings(**_require_section(data, "system")),
            server=ServerSettings(**_require_section(data, "server")),
            agents=AgentSettings(**_require_section(data, "agents")),
            safety=SafetySettings(**_require_section(data, "safety")),
            finance=FinanceSettings(**_require_section(data, "finance")),
            database=DatabaseSettings(**_require_section(data, "database")),
            memory=MemorySettings(**_require_section(data, "memory")),
            logging=LoggingSettings(**_require_section(data, "logging")),
        )
    except TypeError as exc:
        raise ConfigurationError(
            f"Nieprawidłowa struktura konfiguracji: {exc}"
        ) from exc

    return settings


def _validate(settings: Settings) -> None:
    if settings.system.environment not in ALLOWED_ENVIRONMENTS:
        raise ConfigurationError("Nieprawidłowe środowisko systemu.")

    if not 1 <= settings.server.port <= 65535:
        raise ConfigurationError("Port musi mieścić się w zakresie 1–65535.")

    if (
        settings.agents.default_autonomy_level
        not in ALLOWED_AUTONOMY_LEVELS
    ):
        raise ConfigurationError("Nieprawidłowy domyślny poziom autonomii.")

    if (
        settings.agents.maximum_autonomy_level
        not in ALLOWED_AUTONOMY_LEVELS
    ):
        raise ConfigurationError("Nieprawidłowy maksymalny poziom autonomii.")

    default_level = int(settings.agents.default_autonomy_level[1])
    maximum_level = int(settings.agents.maximum_autonomy_level[1])

    if default_level > maximum_level:
        raise ConfigurationError(
            "Domyślna autonomia nie może przekraczać maksymalnej."
        )

    if not 1 <= settings.agents.maximum_task_depth <= 10:
        raise ConfigurationError(
            "Maksymalna głębokość zadań musi mieścić się w zakresie 1–10."
        )

    if not settings.agents.provider.strip():
        raise ConfigurationError(
            "Dostawca agenta nie może być pusty."
        )

    if not settings.agents.model.strip():
        raise ConfigurationError(
            "Model agenta nie może być pusty."
        )

    if settings.agents.timeout_seconds <= 0:
        raise ConfigurationError(
            "Timeout klienta agenta musi być większy od zera."
        )

    if settings.agents.enabled and settings.agents.provider != "mock":
        raise ConfigurationError(
            "Włączony jest obecnie wyłącznie provider mock."
        )

    if settings.finance.mode not in ALLOWED_FINANCE_MODES:
        raise ConfigurationError("Nieprawidłowy tryb finansowy.")

    if settings.finance.maximum_single_cost < 0:
        raise ConfigurationError("Limit pojedynczego kosztu nie może być ujemny.")

    if settings.finance.maximum_project_budget < 0:
        raise ConfigurationError("Budżet projektu nie może być ujemny.")

    if not settings.database.url.startswith("sqlite:///"):
        raise ConfigurationError(
            "W wersji lokalnej dozwolona jest wyłącznie baza SQLite."
        )

    if settings.logging.level not in ALLOWED_LOG_LEVELS:
        raise ConfigurationError("Nieprawidłowy poziom logowania.")

    if (
        settings.system.environment == "development"
        and settings.finance.mode == "live"
    ):
        raise ConfigurationError(
            "Tryb finansowy live jest zabroniony w środowisku development."
        )

    if (
        settings.safety.financial_actions_enabled
        and settings.finance.mode != "live"
    ):
        raise ConfigurationError(
            "Operacje finansowe wymagają trybu finansowego live."
        )

    if (
        settings.agents.enabled
        and settings.safety.emergency_stop
    ):
        raise ConfigurationError(
            "Agenci nie mogą być uruchomieni podczas Emergency Stop."
        )


def load_settings(path: Path | str = DEFAULT_CONFIG_PATH) -> Settings:
    config_path = Path(path)

    if not config_path.is_file():
        raise ConfigurationError(
            f"Nie znaleziono pliku konfiguracji: {config_path}"
        )

    try:
        with config_path.open("r", encoding="utf-8") as file:
            raw_data = yaml.safe_load(file)
    except yaml.YAMLError as exc:
        raise ConfigurationError(
            f"Nieprawidłowa składnia YAML: {exc}"
        ) from exc
    except OSError as exc:
        raise ConfigurationError(
            f"Nie można odczytać konfiguracji: {exc}"
        ) from exc

    if not isinstance(raw_data, dict):
        raise ConfigurationError(
            "Główny element konfiguracji musi być mapą YAML."
        )

    settings = _build_settings(raw_data)
    _validate(settings)

    return settings
