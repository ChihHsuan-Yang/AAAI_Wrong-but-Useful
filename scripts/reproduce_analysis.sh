#!/usr/bin/env bash
# Analysis reproduction: regenerate the figures enumerated in the manifest and
# recompute the robustness tables from below-cell signal records, verifying both
# against their expected summaries. No model calls are made.
#
# The interpreter is $PYTHON if set, else `python3`. Set PYTHON explicitly when
# you have not activated your virtual environment -- a bare `python3` resolves
# against PATH and can pick up a system interpreter that lacks the pinned
# dependencies:
#     PYTHON=.venv/bin/python bash scripts/reproduce_analysis.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
OUT="${1:-${HERE}/reproduced}"

if ! "${PYTHON}" -c 'import matplotlib, numpy, yaml' >/dev/null 2>&1; then
  echo "ERROR: ${PYTHON} cannot import matplotlib, numpy, and yaml." >&2
  echo "       Activate your environment, or point PYTHON at the right" >&2
  echo "       interpreter:  PYTHON=.venv/bin/python bash $0" >&2
  echo "       Interpreter in use: $(${PYTHON} -V 2>&1) at $(command -v "${PYTHON}" || echo "${PYTHON}")" >&2
  exit 1
fi

"${PYTHON}" "${HERE}/scripts/reproduce_analysis.py" --output-dir "${OUT}"
"${PYTHON}" "${HERE}/scripts/recompute_signal_tables.py" --output-dir "${OUT}"
