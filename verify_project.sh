#!/usr/bin/env bash
set -euo pipefail

echo "== Python version =="
python --version

echo "== Repository status =="
git status --short

echo "== Compile =="
python -m compileall -q app tests

echo "== Domain tests =="
pytest -q tests/domain/

echo "== Full test suite =="
pytest -q

echo "== Final status =="
git status --short

echo "Weryfikacja zakończona pomyślnie."
