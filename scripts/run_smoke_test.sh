#!/usr/bin/env bash
# Protocol smoke test: run the tiny fixture pool through the DHD runtime against
# an OpenAI-compatible model API. Skips gracefully when no endpoint is
# configured. No credentials are printed.
#
# The interpreter is $PYTHON if set, else `python3`. Set PYTHON explicitly when
# you have not activated your virtual environment:
#     PYTHON=.venv/bin/python bash scripts/run_smoke_test.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"

if ! "${PYTHON}" -c 'import yaml' >/dev/null 2>&1; then
  echo "ERROR: ${PYTHON} cannot import yaml (PyYAML)." >&2
  echo "       Activate your environment, or point PYTHON at the right" >&2
  echo "       interpreter:  PYTHON=.venv/bin/python bash $0" >&2
  echo "       Interpreter in use: $(${PYTHON} -V 2>&1) at $(command -v "${PYTHON}" || echo "${PYTHON}")" >&2
  exit 1
fi

if [ "$#" -ge 1 ]; then
  "${PYTHON}" "${HERE}/scripts/run_smoke_test.py" --output-dir "$1"
else
  "${PYTHON}" "${HERE}/scripts/run_smoke_test.py"
fi
