"""Declarative local-model routing with an explicit promotion gate.

Routes describe which trained artifact a service *could* use.  They do not
load weights or change the live Ollama configuration.  A route is only
executable when its provider is the bounded Ollama provider and it is marked
enabled; experimental HF adapters therefore remain visible for evaluation
without being selected accidentally.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelRoute:
    service_key: str
    provider: str
    model: str | None
    adapter_id: str | None
    enabled: bool
    evidence: str


ROUTES: dict[str, ModelRoute] = {
    "default": ModelRoute(
        "default", "ollama", "qwen3.8:27b", None, True,
        "bounded local Ollama route; no service-specific parity claim",
    ),
    "restaurant_branding": ModelRoute(
        "restaurant_branding", "hf_adapter", None, "brand-text-sft-1f0a_7s5", False,
        "cross-family 3/3 holdout improvement; deployment adapter is not an Ollama model",
    ),
}


def route_for_service(service_key: str | None) -> ModelRoute:
    """Return a stable route; unknown or omitted services stay on default."""
    key = service_key.strip() if isinstance(service_key, str) else ""
    return ROUTES.get(key, ROUTES["default"])


def route_for_packet(packet: dict[str, Any]) -> ModelRoute:
    """Resolve only an explicit packet service key, never from free-form prose."""
    return route_for_service(packet.get("service_key"))


def executable(route: ModelRoute) -> bool:
    """Whether the route may be handed to the current bounded runtime."""
    return route.enabled and route.provider == "ollama" and route.model is not None

