#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-.}"
REPORT_DIR="$ROOT/reports/domain-audit"

rm -rf "$REPORT_DIR"
mkdir -p "$REPORT_DIR"

echo "== Audyt domeny: $(date -u +%FT%TZ) ==" | tee "$REPORT_DIR/summary.txt"

{
  echo
  echo "## Pliki aplikacji"
  find "$ROOT/app" -type f -name '*.py' -print | sort

  echo
  echo "## Definicje klas i enumów"
  rg -n --glob '*.py' \
    '^[[:space:]]*(class |class .*Enum|enum )' \
    "$ROOT/app" || true

  echo
  echo "## Modele Pydantic, SQLAlchemy i dataclass"
  rg -n --glob '*.py' \
    'BaseModel|DeclarativeBase|Mapped\[|mapped_column|@dataclass|dataclass\(' \
    "$ROOT/app" || true

  echo
  echo "## Statusy, approval, risk, decision, audit i memory"
  rg -n --glob '*.py' \
    'status|approval|risk|decision|audit|memory|execution' \
    "$ROOT/app" || true

  echo
  echo "## Potencjalne luźne słowniki"
  rg -n --glob '*.py' \
    'dict(\[|[:space:]]|$)|Dict\[|dict\[str, Any\]|Any\]|payload\[|data\[|metadata\[' \
    "$ROOT/app" || true

  echo
  echo "## Bezpośrednia modyfikacja statusu"
  rg -n --glob '*.py' \
    '\.status[[:space:]]*=|[["'\'']status["'\'']][[:space:]]*=' \
    "$ROOT/app" || true

  echo
  echo "## Dozwolone modele domenowe"
  for model in Task Agent Department Manager Tool ApprovalRequest Risk Report Decision AuditEvent MemoryRecord; do
    printf '%-20s ' "$model"
    if rg -l --glob '*.py' "\bclass[[:space:]]+$model\b|\b$model\b" "$ROOT/app" >/dev/null 2>&1; then
      echo "FOUND"
    else
      echo "MISSING"
    fi
  done
} | tee "$REPORT_DIR/full-audit.txt"

echo
echo "Raport zapisano w: $REPORT_DIR/full-audit.txt"
