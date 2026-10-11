"""Compatibility import for historical pilots; implementation lives in app services."""
from app.services.filewise_application_provider import (  # noqa: F401
    CONTEXT_MARGIN_BYTES, FILES, FILE_REQUIREMENTS, FILE_TYPES, MAX_FILE_BYTES,
    SCHEMA, TARGET_CHARACTERS, FilewiseApplicationProvider,
)

__all__ = ["CONTEXT_MARGIN_BYTES", "FILES", "FILE_REQUIREMENTS", "FILE_TYPES",
           "MAX_FILE_BYTES", "SCHEMA", "TARGET_CHARACTERS", "FilewiseApplicationProvider"]
