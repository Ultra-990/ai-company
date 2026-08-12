from sqlalchemy import create_engine, inspect

from app.core.database import Base
from app.models.organization import OrganizationUnit


def test_organization_units_table_is_created():
    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    inspector = inspect(engine)
    assert "organization_units" in inspector.get_table_names()

    columns = {
        column["name"]
        for column in inspector.get_columns("organization_units")
    }

    assert {"id", "name", "parent_id"} <= columns


def test_organization_unit_parent_children_relationship():
    parent = OrganizationUnit(name="Firma", unit_type="owner")
    child = OrganizationUnit(
        name="Pion techniczny",
        unit_type="manager",
        parent=parent,
    )

    assert child.parent is parent
    assert child in parent.children
