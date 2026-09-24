# What changed versus the sources, and why

Read `release_notes/PROVENANCE.md` first for the lineage. This file is the
diff-level record: what was modified, what was rebuilt, what was left alone, and
what was deliberately not brought across.

## Unchanged

Most of the repository is the arXiv ancillary artifact byte-for-byte:
`src/dhd/{protocol,labels}.py`, all of `analysis/` except `analysis/replay/`,
all of `figures/`, `configs/`, `data/`, `scripts/{reproduce_analysis.py,
reproduce_analysis.sh,recompute_signal_tables.py,validate_inputs.py}`,
`requirements.lock`, `THIRD_PARTY_NOTICES.md`, `DATA.md`, `ENVIRONMENT.md`, and
six of the test modules. Nothing about the analysis semantics was touched. The
figures, the headline cells, and the below-cell robustness tables reproduce from
the same inputs, by the same code, to the same expected manifests.

## Changed: model identity is resolved per role (the substantive fix)

**The defect.** The published artifact read one environment variable,
`MODEL_API_MODEL`, and sent that identifier for every role. Measured against a
recording mock, all 24 outbound requests of a smoke run carried the same model
id while the protocol YAML declared two distinct model slots. `protocol.py`
parsed each agent's `model` field and nothing ever read it. The emitted id was
not written to any output, so a reader could not tell after the fact what had
run.

**Why it is scientific, not cosmetic.** The paper specifies a separate
evaluator: *"Both gpt-oss-120b and gemma-4-31B-it model families use a separate
gpt-oss-120b evaluator."* The secondary arm needs a Gemma actor scored by an OSS
evaluator. One global model variable cannot express that, so the artifact as
published could not enact the paper's own protocol for that arm.

**The fix.**

| New or changed | What it does |
|---|---|
| `src/dhd/config.py` (new) | The single config layer. Resolves endpoint, credential, model, and decoding per role; refuses contradictory bindings; records a credential-free audit block. |
| `src/dhd/model_api.py` (rewritten) | Adds `RoleRouter`, which holds one binding per role and records every `(role, model)` pair it actually sent. The original `ClientConfig` / `load_client_config` / `chat_completion` surface still works, and now also recognises the `DHD_ACTOR_*` names. |
| `src/dhd/replay.py` (2-line semantic change) | Passes `role=` to generators that accept it, so the evaluator call can go out under the evaluator's model. Generators written against the original three-argument signature are detected and called unchanged -- the existing tests pass untouched. |
| `scripts/run_smoke_test.py` (rewritten) | Uses the router, prints the resolved identity per role, writes `model_identity` into `smoke_results.json`, and **exits 1** if emitted differs from configured. |
| `scripts/dry_run.py` (new) | Prints the full picture with no network call and no credential. |
| `tests/test_model_identity.py` (new, 17 tests) | Fails when emitted differs from configured, when a required endpoint is silently missing, when a credential could be printed, or when an author endpoint is selectable as a default. Includes a positive control that feeds the detector the defective configuration and requires rejection. |

The guard at the heart of it is the one that already existed in the authors'
replay runner -- raise on `declared != loaded` -- generalised from a single
assertion into a structural rule: two roles declaring different model slots may
not resolve to one identifier, and two roles declaring the same slot may not
resolve to different ones.

## Changed: one configuration layer, no author defaults

Everything the runtime needs now resolves in `src/dhd/config.py`. Every
connection value defaults to the empty string; there is no fallback endpoint
anywhere in the repository, and `tests/test_model_identity.py` walks the tree to
assert it. Every path default is repository-relative. `.env.example` ships,
`.env` is gitignored, and the credential-shaped-file check runs in CI.

The artifact's `MODEL_API_*` names still work as the global fallback, so
existing instructions do not break. They are documented as legacy, with the
caveat that on their own they are the collapsed configuration the runtime now
rejects.

## Changed: de-anonymization

`LICENSE` copyright line, the `artifact` field in `ARTIFACT_MANIFEST.json`, and
the `name`/`description` in `pyproject.toml`. Still MIT; no relicensing. The
exact former strings are recorded in `release_notes/PROVENANCE.md` so the
substitution is checkable.

## Replaced: the upstream review-era self-check became a portability audit

The artifact shipped `tests/test_artifact_anonymity.py`, which scanned for six
base64-encoded infrastructure terms. That property mattered under double-blind
review; it is not the property to enforce on a published repository. `tools/portability_audit.py` replaces it and checks five classes --
author paths, private URLs, credentials, stale internal names, review-anonymity
language -- across 17 patterns, each with a positive control.

Three design choices came directly from the control catching this build's own
mistakes, and are worth recording because each looked fine until tested:

1. The first version stored its control strings as literals and exempted itself
   by path. Scanning a copy showed the exemption hid a genuine class of hits;
   worse, a path exemption covers everything in the file forever. Fixed by
   assembling every pattern and control from fragments and deleting the
   self-exemption.
2. The allowlist was first keyed on `(path, pattern)`, then on
   `(path, pattern, substring)`. The positive control planted a fake copyright
   line inside the allowlisted file and it was **exempted** -- a real,
   unrelated line elsewhere in that file contained the same words and satisfied
   the key. Fixed by keying on the SHA-256 of the exact stripped line.
3. An allowlist entry that no longer matches is now reported as stale, so
   exemptions get removed rather than silently accumulating.

The final control plants one violation of each class inside the allowlisted file
and requires all five to be reported: 8 plants, 8 findings, exit 1.

## Rebuilt: the component-masking runner

The upstream runner (`dhd_replay_stability.py`, plus its uncommitted diff)
**was not ported**. It reaches the model through the authors' internal agent
framework -- `TaskSolving.from_config_path`, `rule._integrate`,
`rule.evaluator.astep`, `AGENT_TYPES` -- which a reader cannot install. Shipping
it would have shipped a script that cannot run.

What was ported is the *mechanism*, into two standard-library modules:

* `src/dhd/content_control.py` -- the five matched arms, the word-count-matched
  masking, the interleaved schedule, the control-manifest loader, the pool word
  count. Logic preserved exactly; the upstream unit tests pass against it.
* `scripts/run_content_control.py` -- a runner that reaches the model through
  `src/dhd` instead, and writes the same `replay_events.jsonl` / `RUN_META.json`
  / `validation.json` schema the analyzer consumes.

**What that preserves**: the arms, the masking semantics, the length control,
the interleaving, the matched-within-replicate comparison, the
scientific-versus-operational separation, and the schema.

**What it does not preserve**: the upstream runner's resume-with-lock behaviour,
its per-invocation token accounting, its `--stratify_tier` sampling, its
K=2..5 leave-one-out and null-arm schedules, and its evaluator's richer
verdict-mode handling. Those served the authors' cluster campaign, not the
mechanism. `tab:repeated_replay`, which depends on them, is marked
REQUIRES-LIVE-INFERENCE and explicitly not claimed.

## Ported: three analyses, decoupled

| Here | Change |
|---|---|
| `analysis/replay/offline_routing_analysis.py` | Import unchanged (it never depended on the framework). Added: a clear error when the optional `zstandard` dependency is absent, a clear error naming the expected shard layout when a shard is missing, and a docstring stating it is the only generator for `tab:app_single_full_2x2`. |
| `analysis/replay/content_control_analyze.py` | Logic unchanged. Added: how to produce a run directory with the new runner, and the unresolved 5-vs-6 condition-naming caveat. |
| `analysis/replay/trace_example_report.py` | **Import fixed**: it imported its sibling via a monorepo-absolute path (`scripts.critique_intervention....`) that does not exist here. Now imports by name from the same directory. **Hard-coded author benchmark paths removed** and replaced by `DEFAULT_BENCHMARK_LAYOUT` plus a `--benchmark_layout` override; a missing file is skipped with a warning, and an empty result raises a message that says what to supply. Docstring now states that its inputs are unpublished and **its outputs are not redistributable**. |

Their upstream unit tests came across with only the import lines rewritten, and
all pass.

## Not brought across

* **`jobs/*.sh` and `jobs/*.pbs`** (~10 files). Absolute cluster paths including
  a third party's account name, and 22 occurrences of
  `export HTTP_PROXY="${HTTP_PROXY:-<private proxy>}"` -- a `:-` default, so an
  unset variable would silently route a reader's traffic through a private
  network rather than failing. No sanitized HPC examples were written in their
  place: an untested job script is a liability, and nothing in this repository
  needs one.
* **The cluster README** (live inference endpoint; two named accounts, one of
  them a third party's).
* **`use_alcf.sh`, `inference_auth_token.py`** (site-specific authentication).
* **Any generated `trace_candidates.json` / `trace_shortlists.*`** -- these embed
  verbatim LAB-Bench (CC-BY-SA-4.0, canary) and MaScQA (CC-BY-NC-SA-4.0)
  question text that `DATA.md` deliberately excludes. The script is here; its
  outputs must not be republished.

None of this is scientifically load-bearing. The arXiv artifact never contained
any of it and reproduces without it.

## Documentation

`README.md` was rewritten around a four-level reproduction path and now states
plainly that the analysis gate's coverage is narrower than the shipped data
(`metric == "In-pool LOO"` only -- 4 of 8 rows -- and 7 of 13/20 columns), that
the Python floor is 3.10 because of the pins rather than the source, and that
the dataset is access-controlled so the public path is the bundled data.
`REPRODUCE.md` carries the same caveats at step level. `docs/MODEL_DEPENDENCIES.md`
and `docs/PAPER_REPRODUCTION_MAP.md` are new; the map assigns one of four honest
statuses to each of the paper's 38 figures and tables, of which 16 are UNPROVEN.
