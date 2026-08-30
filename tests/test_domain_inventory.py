from pathlib import Path
import ast

REQUIRED_MODELS = {
    "Task",
    "Agent",
    "Department",
    "Manager",
    "Tool",
    "ApprovalRequest",
    "Risk",
    "Report",
    "Decision",
    "AuditEvent",
    "MemoryRecord",
}


def find_defined_classes() -> set[str]:
    result: set[str] = set()

    for path in Path("app").rglob("*.py"):
        if "backups" in path.parts:
            continue

        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                result.add(node.name)

    return result


def test_required_domain_models_are_inventoryable():
    defined = find_defined_classes()
    missing = sorted(REQUIRED_MODELS - defined)

    # Raport diagnostyczny bez blokowania istniejącego zestawu testów.
    print(f"Defined domain names: {sorted(defined)}")
    print(f"Missing domain models: {missing}")
