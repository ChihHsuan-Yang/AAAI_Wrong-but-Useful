# Environment

## Interpreter

Verified with **CPython 3.13.0** in a fresh virtual environment.

`pyproject.toml` declares `requires-python = ">=3.10"`, which is accurate for
the *source* (it uses `X | Y` unions and `list[...]` generics). It is **not**
accurate for the *pinned dependency set*: `numpy==2.4.4` declares
`requires_python >= 3.11`, so `pip install -r requirements.lock` fails on 3.10
with *"No matching distribution found for numpy==2.4.4"*. `matplotlib==3.10.9`
and `pytest==9.1.1` independently rule out 3.9.

**Use Python >= 3.11.** To run on 3.10 you would have to relax the numpy pin,
and would no longer be running the pinned set.

## Dependencies

Install the pinned set:

```bash
python -m pip install -r requirements.lock
```

| Package | Version | `requires_python` | Needed for |
|---|---|---|---|
| matplotlib | 3.10.9 | >= 3.10 | Figure regeneration |
| numpy | 2.4.4 | **>= 3.11** | Analysis bootstraps and permutation tests |
| PyYAML | 6.0.3 | >= 3.8 | Loading protocol configs |
| pytest | 9.1.1 | >= 3.10 | Test suite |
| zstandard | 0.23.0 | >= 3.8 | Analyses that read compressed raw shards |

The numpy pin sets the effective floor at 3.11.

## Shell wrappers and the interpreter they pick

`scripts/reproduce_analysis.sh` and `scripts/run_smoke_test.sh` call `$PYTHON`
if set and `python3` otherwise. A bare `python3` resolves against `PATH` and can
find a system interpreter without the pinned packages, so if your environment is
not activated, name it:

```bash
PYTHON=.venv/bin/python bash scripts/reproduce_analysis.sh
```

Both wrappers check the imports up front and print that advice rather than
failing deep inside a subprocess.

## What each layer requires

- **Protocol runtime (`src/dhd/`)**: standard library only. The generic model
  API client uses `urllib`, so the smoke test needs no third-party HTTP library.
- **Analysis reproduction (`scripts/reproduce_analysis.py`, `figures/`)**:
  matplotlib and numpy.
- **Protocol smoke test**: a reachable OpenAI-compatible model API, configured
  via `MODEL_API_BASE`, `MODEL_API_MODEL`, and optionally `MODEL_API_KEY`.

## Determinism notes

- Figure and table regeneration is deterministic given the included CSVs.
- Analysis bootstraps and permutation tests use fixed seeds recorded in each
  script and in the derived records.
- The protocol smoke test calls a stochastic model API; its generated text is
  not expected to be byte-identical across deployments.
