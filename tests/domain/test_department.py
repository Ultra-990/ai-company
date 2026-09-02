import pytest

from app.domain.contracts.department import Department


def test_department_is_serializable():
    department = Department(
        id="technical",
        name="Technical",
        description="Engineering department",
    )

    assert department.to_dict() == {
        "id": "technical",
        "name": "Technical",
        "description": "Engineering department",
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {"id": "", "name": "Technical"},
        {"id": "technical", "name": ""},
    ],
)
def test_department_rejects_empty_required_fields(kwargs):
    with pytest.raises(ValueError):
        Department(**kwargs)
