from datetime import datetime, timezone

import pytest

from app.domain.contracts.memory import MemoryRecord


def test_memory_record_is_serializable():
    created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    record = MemoryRecord(
        id="memory-1",
        content="Important decision",
        memory_type="decision",
        metadata={"source": "test"},
        created_at=created_at,
    )

    result = record.to_dict()

    assert result["id"] == "memory-1"
    assert result["content"] == "Important decision"
    assert result["memory_type"] == "decision"
    assert result["metadata"] == {"source": "test"}
    assert result["created_at"] == created_at.isoformat()


def test_memory_record_rejects_empty_content():
    with pytest.raises(ValueError):
        MemoryRecord(id="memory-1", content="")
