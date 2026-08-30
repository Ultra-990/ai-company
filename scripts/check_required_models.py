from pathlib import Path
import ast

REQUIRED = {
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

locations: dict[str, list[str]] = {name: [] for name in REQUIRED}

for path in Path("app").rglob("*.py"):
    if "backups" in path.parts:
        continue

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        continue

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name in REQUIRED:
            locations[node.name].append(str(path))

print("MODEL;STATUS;LOCATIONS")

for name in sorted(REQUIRED):
    found = locations[name]
    status = "FOUND" if found else "MISSING"
    print(f"{name};{status};{', '.join(found) or '-'}")
