# Reproduction Guide

All commands are run from the artifact root. Paths are relative; the artifact
requires no private infrastructure and no absolute paths.

## 0. Environment

```bash
python -m venv .venv && source .venv/bin/activate   # Python 3.11-3.13
python -m pip install -r requirements.lock
```

The floor is **3.11**, set by the pins rather than the source: `numpy==2.4.4`
declares `requires_python >= 3.11`, so the install fails on 3.10. Verified on
CPython 3.13.0. See `ENVIRONMENT.md`.

If your environment is not activated, name the interpreter when using the shell
wrappers: `PYTHON=.venv/bin/python bash scripts/reproduce_analysis.sh`.

## 1. Unit tests

```bash
python -m pytest
```

This runs:

- runtime tests for boxed-answer extraction, evaluator-verdict parsing,
  trajectory-value label computation, hypotheses-block key construction, replay
  aggregation, and the operational-failure-vs-scientific-outcome separation;
- the analysis unit test for problem-blocked multiplicity corrections;
- unit tests for the three replay analyses in `analysis/replay/`, exercised on
  synthetic records so they run without the raw shards;
- the model-identity suite (`tests/test_model_identity.py`), which fails if a
  role's emitted model diverges from its configuration, if a required endpoint
  is missing silently, if a credential could be printed, or if an author
  endpoint is selectable as a default. It carries its own positive control, so
  it cannot pass by being permissive.

Expected: `55 passed`.

Release hygiene is checked separately, not by pytest:

```bash
python tools/portability_audit.py --self-test   # prove every pattern can fire
python tools/portability_audit.py               # then scan
```

## 2. Analysis reproduction (exact, no model calls)

```bash
bash scripts/reproduce_analysis.sh            # outputs to ./reproduced
# or choose an output directory:
bash scripts/reproduce_analysis.sh /tmp/out
```

This performs two steps:

1. **Figures + headline cells.** Regenerates the six data-driven paper figures
   (PDF/PNG/SVG) from the source CSVs in `figures/`, recomputes the headline
   correctness/trajectory-value taxonomy cell counts and helpful-share
   statistics, and compares them against `data/manifests/expected_summaries.json`.
2. **Robustness tables below the aggregated cells.** Recomputes the
   matched-sensitivity table (`tab:matched_sensitivity`) and the cross-fitted
   one-removal tables (`tab:cross_fitted_one_removal` and its by-benchmark
   companion) from the per-signal and per-fold records in
   `data/derived/signal_labels/`, and compares the point estimates against
   `data/manifests/expected_signal_tables.json`.

Expected final lines:

```
PASS: recomputed headline summary matches expected manifest.
PASS: recomputed matched-sensitivity and cross-fitted tables match expected manifest (below-cell reconstruction).
```

The recomputed taxonomy exhibits the paper's central off-diagonal cells
(non-zero wrong-helpful and correct-harmful counts for both model families), and
the robustness tables reproduce the paper's mean-shift, sign-agreement, and
cross-fitted gain point estimates from records below the aggregated cells.

### Scope of the analysis-reproduction claim

This reproduces the outputs enumerated in `ARTIFACT_MANIFEST.json` (the six
figures, the headline taxonomy cells, and the matched-sensitivity and
cross-fitted one-removal tables).

**Two coverage limits, measured.** `reproduce_analysis.py:62` skips every row
whose `metric` is not `"In-pool LOO"` -- 4 of the 8 rows in the flip source are
checked and 4 are not. `recompute_signal_tables.py` reads 7 columns
(`reference_sign`, `sensitivity_sign`, `trajectory_value_delta`, `full_value`,
`selector_value`, `model`, `benchmark`) out of the 13 and 20 that those records
carry. Rows and columns outside those sets ship but are not recomputed, so a
change to one can leave the PASS lines intact. `validate_inputs.py` still
catches any byte change by checksum. Treat the PASS lines as "these specific
estimates were rebuilt from below-cell records and matched", not as
"the released data is validated".

It does **not** regenerate every table in the paper: several appendix tables are stated inline or depend on the full raw
release root and are not included. The recorded outputs of the heavier analysis
scripts (majority diagnostic, offline reviewer-closure, repeated-effect,
problem-blocked multiplicity) ship under `data/derived/` for inspection, and the
scripts that produce them are under `analysis/`, but they require the raw release
root to recompute and are therefore not part of the no-model-call exact claim.

## 3. Input validation

```bash
python scripts/validate_inputs.py
```

Verifies that every data object listed in `ARTIFACT_MANIFEST.json` exists,
matches its recorded SHA-256, and (for CSVs) has the recorded row count.

Expected: `PASS: validated N data objects against the manifest.`

## 4. Protocol smoke test (procedure, not byte-identical text)

The smoke test runs the tiny fixture pool (`data/fixtures/smoke_pool.jsonl`)
through the full-pool and leave-one-out integration conditions using an
OpenAI-compatible model API, then scores each output with the evaluator prompt.

Configure **per role** -- the actor lane and the evaluator are separate, because
the paper scores every actor family with a separate evaluator:

```bash
cp .env.example .env            # .env is gitignored
# fill it in, then:
set -a && . ./.env && set +a

python scripts/dry_run.py       # no network call; prints what would run
bash scripts/run_smoke_test.sh  # outputs under $DHD_OUTPUT_DIR/smoke_output
```

Minimum: `DHD_ACTOR_BASE_URL` + `DHD_ACTOR_MODEL` and `DHD_EVALUATOR_BASE_URL` +
`DHD_EVALUATOR_MODEL`. The artifact's original `MODEL_API_BASE` /
`MODEL_API_MODEL` / `MODEL_API_KEY` still work as a global fallback, but on
their own they collapse the integrator and the evaluator onto one model, which
this runtime now rejects for a config that declares two slots.

If nothing is configured, the test **skips gracefully** with a clear message and
exit code 0, so the repository can be inspected without credentials. Credentials
and authorization headers are never printed; endpoints are shown host-only.

The identifier actually sent for each role is recorded in
`smoke_results.json` under `model_identity.emitted_models_by_role`, and a run
whose emitted identity differs from its configuration exits 1. See
`docs/MODEL_DEPENDENCIES.md`.

For each fixture problem the runner reports the number of scientific outcomes
(1 full pool + 5 leave-one-out removals), the number of operational failures
(kept separate from scientific outcomes), and the derived single-draw and
repeated trajectory-value labels.

### Why the protocol claim is "procedure, not exact text"

The integrator and evaluator are stochastic language-model calls. Different model
deployments — even nominally deterministic ones — can produce different text.
The artifact reproduces the *procedure* (prompt contract, pool rendering,
matched full/removal conditions, labeling), not the exact generated strings. The
exact-reproduction guarantee applies only to the analysis in step 2, which uses
the included derived records and makes no model calls.

## 5. Component-masking diagnostic

Separates a message's proposed answer from its reasoning while holding slot
position and word count fixed:

```bash
python scripts/run_content_control.py \
    --source POOLS.jsonl --control-manifest TARGETS.jsonl --out-dir RUN
python analysis/replay/content_control_analyze.py --run_dir RUN
```

`POOLS.jsonl`: one row per problem with `problem_id`, `problem`, `reference`,
`hypotheses[5]`. `TARGETS.jsonl`: one `problem_id` + `hypothesis_index` per row.

**Caveat, unresolved.** The paper's table describes six conditions and 880
outcomes; this code implements five and consumes four effects (550). The
plausible mapping is unproven, so do not report this as reproducing that table.
See `docs/PAPER_REPRODUCTION_MAP.md`.

## 6. Full protocol on real benchmarks

This repository ships no benchmark question text (see `DATA.md`). To run the
protocol on real data, acquire each dataset from its upstream source under that
dataset's license, apply the eligibility filter described in `DATA.md`, generate
five hypotheses per problem with the recruiter/hypothesizer prompts in
`configs/paper/dhd_config.yaml`, and run the matched conditions with the
integrator and evaluator prompts. The secondary-actor variant in
`configs/paper/dhd_config_secondary_actor.yaml` differs only in the actor model
family.

Two analyses under `analysis/replay/` also belong here because they read raw
per-benchmark shards this repository does not publish:
`offline_routing_analysis.py` (the only generator for `tab:app_single_full_2x2`)
and `trace_example_report.py` (whose outputs embed benchmark question text and
are **not** redistributable). See the README's Level 4.
