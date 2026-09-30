# Wrong but Useful: Trajectory Value Beyond Answer Correctness in Multi-Agent Messages

### Measuring whether a message helps the reasoning that follows, not just whether its answer is right

[![Project page](https://img.shields.io/badge/Project-Page-1f6f5c)](https://chihhsuan-yang.github.io/AAAI_Wrong-but-Useful/)
[![arXiv](https://img.shields.io/badge/arXiv-2608.14375-b31b1b)](https://arxiv.org/abs/2608.14375)
[![PDF](https://img.shields.io/badge/Paper-PDF-333333)](https://arxiv.org/pdf/2608.14375)
[![HF dataset](https://img.shields.io/badge/%F0%9F%A4%97%20Dataset-Card-ffcc4d)](https://huggingface.co/datasets/AgentsSci/AAAI_Wrong-but-Useful)
[![No model](https://img.shields.io/badge/Model-none%20released-9e9e9e)](docs/MODEL_DEPENDENCIES.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![CI](https://github.com/ChihHsuan-Yang/AAAI_Wrong-but-Useful/actions/workflows/ci.yml/badge.svg)](https://github.com/ChihHsuan-Yang/AAAI_Wrong-but-Useful/actions/workflows/ci.yml)

Chih-Hsuan Yang¹\*, Anjir Ahmed Chowdhury², Cheng-Hau Yang¹, Weijian Zheng¹, Fernando Llorente³, Xiaolong Ma¹, Xinyang Li², Eliu A. Huerta¹⁴, Ian T. Foster⁴¹, Rajeev Thakur¹
¹ Argonne National Laboratory · ² University of Houston · ³ Brookhaven National Laboratory · ⁴ University of Chicago · \* bellayang@anl.gov

---

Multi-agent systems decide which messages shape a final answer using agreement,
confidence, or automated scores. That assumes a message likely to be *correct* is
also worth *keeping*. This paper separates the two: **proposal correctness** asks
whether a message's own answer is right; **trajectory value** asks whether making
the whole message available helps or harms the reasoning that follows. They come
apart in both directions — **wrong proposals can be helpful**, and **correct
proposals can be harmful**.

## Key findings

| | Result | Detail |
|---|---|---|
| 🟢 | **41.9%** (OSS) · **45.3%** (Gemma) | Of leave-one-out replays where a wrong-answer message *changes* final correctness, this share moves it in the **helpful** direction. Pooled per model, not per benchmark. |
| 🟢 | **10 / 10** benchmark–model cells | Wrong-helpful messages appear in every benchmark under both model families. |
| 🔵 | **p = 0.0002** | Controlled repeats show the count of repeatable message effects is unlikely to arise from replay variation alone. |
| 🟠 | Gemma only | After multiplicity control, wrong-helpful cases are recovered for **Gemma but not OSS**. |
| ⬜ | Open question | The complete message works best, and retaining its reasoning preserves more success than retaining only its answer — but **the source of that advantage remains open**. |

## Resources

| Artifact | Contents | Terms | Link |
|---|---|---|---|
| **Paper** | Full text, appendix, ancillary reproducibility artifact | arXiv | [abs](https://arxiv.org/abs/2608.14375) · [PDF](https://arxiv.org/pdf/2608.14375) |
| **Project page** | Findings, protocol, reproduction summary | — | [chihhsuan-yang.github.io](https://chihhsuan-yang.github.io/AAAI_Wrong-but-Useful/) |
| **Code** | DHD implementation, analysis pipeline, bundled derived data, tests | MIT | [this repository](https://github.com/ChihHsuan-Yang/AAAI_Wrong-but-Useful) |
| **Dataset** | Trajectory-value measurements, hypotheses, interventions, replay labels, registry | ⚠️ **non-commercial**; **no training on LAB-Bench** | [🤗 dataset card](https://huggingface.co/datasets/AgentsSci/AAAI_Wrong-but-Useful) |
| **Model** | *None — no checkpoint was trained for this paper* | n/a | [why, and what to configure instead](docs/MODEL_DEPENDENCIES.md) |

### Benchmarks

| Benchmark | Domain and format | Problems | Upstream terms | Source |
|---|---|--:|---|---|
| Omni-MATH-2 | Open-answer competition mathematics | 4,181 | Apache-2.0 † | [🤗](https://huggingface.co/datasets/martheballon/Omni-MATH-2) |
| JEEBench | Mixed-choice and numeric exam science | 515 | MIT | [GitHub](https://github.com/dair-iitd/jeebench) |
| SciBench | Numeric and short-answer college science | 580 | MIT | [GitHub](https://github.com/mandyyyyii/scibench) |
| LAB-Bench | Long-evidence multiple-choice biology | 741 | ⚠️ CC BY-SA 4.0 · **do not train** | [🤗](https://huggingface.co/datasets/futurehouse/lab-bench) |
| MaScQA | Mixed-format materials science | 649 ‡ | ⚠️ CC BY-NC-SA 4.0 | [GitHub](https://github.com/M3RG-IITD/MaScQA) |

† The dataset registry records Apache-2.0 while the authors' own `DATA.md` disagrees; treat as unsettled.
‡ MaScQA ships 650 raw rows; one is an exact duplicate, so analyses use 649 unique problems.

### Models

| Model | Role in this paper | Decoding | Upstream |
|---|---|---|---|
| `gpt-oss-120b` | **Actor** ("OSS") **and** the shared evaluator for both families | hypothesizer T=0.7; recruiter/integrator/evaluator T=0 | [🤗](https://huggingface.co/openai/gpt-oss-120b) |
| `gemma-4-31B-it` | **Actor** ("Gemma") | same role-specific settings | [🤗](https://huggingface.co/google/gemma-4-31b-it) |
| `Meta-Llama-3.1-70B-Instruct` | *Evaluator only* — cross-evaluator agreement check | T=0 | [🤗](https://huggingface.co/meta-llama/Llama-3.1-70B-Instruct) |
| `gemma-3-27b-it` | *Evaluator only* — cross-evaluator agreement check | T=0 | [🤗](https://huggingface.co/google/gemma-3-27b-it) |

> **This work does not release a paper-specific trained model. Experiments use
> openly available upstream model families through inference endpoints.**
> No checkpoint, adapter, or fine-tune exists for this paper. The upstream
> families, their per-role decoding settings, and what can and cannot be pinned
> about them are in [`docs/MODEL_DEPENDENCIES.md`](docs/MODEL_DEPENDENCIES.md).

---

## Reproduce *Wrong but Useful* from a clean machine

Read this section before running anything. It is written to be accurate about
what each step proves, including where the verification is narrower than it
looks.

### What you can and cannot reproduce

There are four levels, and they are not equally available to you.

| Level | What it does | Needs | Available to a newcomer? |
|---|---|---|---|
| **1. Offline** | install, unit tests, checksum validation, figure + table regeneration from bundled data | Python >= 3.11 | **Yes.** Fully. This is the reproduction path. |
| **2. Live protocol** | run the DHD protocol on the bundled fixture against **your own** endpoint | Level 1 + an OpenAI-compatible endpoint you control | **Yes**, if you bring an endpoint. |
| **3. Component masking** | the five matched masking arms on pools **you** generate | Level 2 + cached pools | Yes in mechanism; see the naming caveat below. |
| **4. Full regeneration** | the paper's full five-benchmark, two-family campaign | benchmark licenses, HPC-scale inference, weeks | **No**, realistically. |

**Level 1 is the reproduction path, and it uses the data in this repository.**
You do not need `hf download` for Level 1: the derived data it uses is bundled
here. The full dataset is public, but it carries usage restrictions (below).

### Requirements

**Python >= 3.11 to install the pinned set. `pyproject.toml` declares >= 3.10,
and that is true of the source but not of the pins.** Measured, not assumed:

| Pin | `requires_python` | Consequence |
|---|---|---|
| `numpy==2.4.4` | `>=3.11` | **The binding constraint.** `pip install -r requirements.lock` fails outright on 3.10: *"No matching distribution found for numpy==2.4.4"*. |
| `matplotlib==3.10.9` | `>=3.10` | Rules out 3.9. |
| `pytest==9.1.1` | `>=3.10` | Rules out 3.9. |
| `PyYAML==6.0.3`, `zstandard==0.23.0` | `>=3.8` | Not binding. |

So: **3.9 cannot work, and 3.10 cannot install the lockfile.** Use 3.11 or
newer. The full workflow below was verified here on **CPython 3.13.0**, in a
fresh venv in a temp directory with project variables unset; the upstream
artifact was produced under 3.13.0 as well.

The source itself is more permissive than the pins -- it compiles and imports
under 3.9 -- but that is not a supported configuration, because the analysis
then dies with `ModuleNotFoundError`. If you must run on 3.10, you would have to
relax the numpy pin yourself, and you would no longer be running the pinned set.

Five pinned packages, all pure-analysis: matplotlib, numpy, PyYAML, pytest, and
`zstandard` (needed only by the two analyses that read compressed shards). The
protocol runtime in `src/dhd/` uses **only the standard library** -- the model
client is `urllib`, so no HTTP dependency is required to run the protocol.

No GPU. No cluster. Level 1 needs about 1.3 MB of repository data and finishes
in well under a minute.

### Level 1 -- install, test, reproduce (no model calls)

```bash
git clone https://github.com/ChihHsuan-Yang/AAAI_Wrong-but-Useful.git
cd AAAI_Wrong-but-Useful
python3 -m venv .venv && source .venv/bin/activate      # python must be >= 3.11
python -m pip install -r requirements.lock
```

Then, in order:

```bash
python -m pytest
```
> Expected: `55 passed`. Runtime tests for boxed-answer extraction, evaluator
> verdict parsing, trajectory-value labels, hypotheses-block construction, replay
> aggregation, and the operational-failure-vs-scientific-outcome separation;
> the multiplicity-correction unit test; the ported tests for the three replay
> analyses; and the model-identity suite described under
> [Model identity](#model-identity-is-resolved-per-role-and-audited). About 3 s.

```bash
python scripts/validate_inputs.py
```
> Expected: `PASS: validated 25 data objects against the manifest.` Checks every
> file listed in `ARTIFACT_MANIFEST.json` for existence, SHA-256, and (for CSVs)
> row count. Under a second.

```bash
bash scripts/reproduce_analysis.sh            # writes ./reproduced
# or: bash scripts/reproduce_analysis.sh /tmp/out
```
> Expected: 20 files in the output directory -- PDF, PNG and SVG for each of six
> figures, plus two JSON summaries -- and **both** of these
> lines:
> ```
> PASS: recomputed headline summary matches expected manifest.
> PASS: recomputed matched-sensitivity and cross-fitted tables match expected manifest (below-cell reconstruction).
> ```
> About 10 s. Regenerates `fig_correctness_flip_direction`,
> `fig_cross_benchmark_trajectory_value`, `fig_generation_integration_gap`,
> `fig_generation_integration_gap_gemma`, `fig_loo_by_k_appendix`, and
> `fig_evaluator_agreement`; recomputes the headline taxonomy cells; and rebuilds
> `tab:matched_sensitivity`, `tab:cross_fitted_one_removal`, and its by-benchmark
> companion from *per-signal and per-fold records below the aggregated cells*.

```bash
python tools/portability_audit.py --self-test && python tools/portability_audit.py
```
> Expected: `PASS: all 17 patterns matched their positive control...` then
> `PASS: 17 patterns, all positive-controlled, 0 findings...`. Not a
> reproduction step -- a release check you can run yourself, described under
> [Portability audit](#portability-audit).

### What the analysis gate does *not* verify

**The reproduction gate's coverage is narrower than the data this repository
ships.** This is a measured property of the scripts, not a guess:

* `scripts/reproduce_analysis.py:62` skips every row whose `metric` is not
  `"In-pool LOO"`. The figure source it reads has 8 rows; **4 are checked and 4
  are not** -- the `Single-hypothesis` rows pass through unverified.
* `scripts/recompute_signal_tables.py` reads **7 columns**: `reference_sign`,
  `sensitivity_sign`, `trajectory_value_delta`, `full_value`, `selector_value`,
  `model`, `benchmark`. The matched-sensitivity records carry 13 columns and the
  per-fold records carry 20. The rest are shipped but not recomputed.

So: a change to a non-`In-pool LOO` row, or to a column outside those seven,
can leave `reproduce_analysis.sh` passing. Integrity is still covered --
`validate_inputs.py` checksums every manifest-listed file byte-for-byte, and a
single appended line to any of them fails it -- but **"the analysis gate
validates the released data" would overstate what the PASS lines mean.** They
mean the headline taxonomy cells and the point estimates of three robustness
tables were recomputed from below-cell records and matched.

Several paper tables are not regenerated here at all. Per-artifact status for
all 38 figures and tables is in
[`docs/PAPER_REPRODUCTION_MAP.md`](docs/PAPER_REPRODUCTION_MAP.md), with each row
marked OFFLINE-DETERMINISTIC, REQUIRES-PRIVATE-DATA, REQUIRES-LIVE-INFERENCE, or
UNPROVEN.

### Level 2 -- the protocol against your own endpoint

The smoke test runs two fixture problems through the full-pool and five
leave-one-out conditions and scores each with the evaluator prompt.

Copy `.env.example`, fill it in, and **dry-run before you spend anything**:

```bash
cp .env.example .env         # .env is gitignored; never commit it
# edit .env, then export the variables into your shell, e.g.:
set -a && . ./.env && set +a

python scripts/dry_run.py
```

`dry_run.py` makes **no network call**. It prints, per role: provider,
sanitized endpoint (host only -- never userinfo, path, or query), the model slot
the config declares, the identifier that resolves and which variable supplied
it, the identifier that *will be emitted*, temperature, max tokens, whether a
credential is present and from which variable (never its value), seed behaviour,
config SHA-256, code commit, benchmark, requested sample ids, expected role-call
count, and the output path. Paste its output when reporting a problem; it
contains no secret.

Then:

```bash
bash scripts/run_smoke_test.sh
```
> With nothing configured: prints `SKIP: model API is not configured for
> role(s): ...` and exits **0**. That is intended -- the repository is
> inspectable without credentials.
>
> Configured: per fixture problem, `scientific=6 failures=0 signals=5`
> (1 full pool + 5 removals; 5 derived labels), then
> `[smoke] emitted model identity matches configuration for role(s): evaluator, integrator`.
> Writes `smoke_results.json` under `$DHD_OUTPUT_DIR/smoke_output/`.

**Generated text will not be byte-identical to ours, and cannot be.** The
integrator and the evaluator are stochastic calls to a hosted service. The
upstream endpoints used for the paper did not expose weight-revision hashes, the
service version and sampler are outside anyone's control, and the
OpenAI-compatible surface used here exposes no seed parameter. What reproduces
is the *procedure*: prompt contract, pool rendering, matched full/removal
conditions, labelling. The exact-value guarantee belongs to Level 1 only.

#### Model identity is resolved per role, and audited

The published ancillary artifact had a defect worth naming, because the fix is
the main structural change in this repository. It read one environment variable,
`MODEL_API_MODEL`, and sent that single identifier for **both** the integrator
and the evaluator, while the protocol YAML declared two different model slots.
Measured against a recording mock, all 24 outbound requests carried the same
model id. `protocol.py` parsed the per-agent `model` field and nothing read it.

That is not only untidy. The paper's design requires a separate evaluator --
*"Both gpt-oss-120b and gemma-4-31B-it model families use a separate
gpt-oss-120b evaluator"* -- so with one global variable the Gemma arm, where a
Gemma actor must be scored by an OSS evaluator, **cannot be enacted at all**.

Here, `src/dhd/config.py` resolves identity per role (recruiter, hypothesizer,
integrator, evaluator), and:

* two roles declaring **different** model slots that resolve to the **same**
  identifier is an error -- the collapse fails closed;
* two roles declaring the **same** slot that resolve to **different**
  identifiers is an error;
* `DHD_EXPECT_<ROLE>_MODEL`, if set, must match exactly or the run aborts (this
  is the `declared != loaded` guard from the authors' replay runner);
* the identifier that reached the wire is recorded in `smoke_results.json` under
  `model_identity.emitted_models_by_role`, and a run whose emitted identity
  differs from its configuration **exits 1**.

`tests/test_model_identity.py` fails if any of that regresses. It includes an
explicit positive control (`test_collapse_detector_is_not_vacuous`) that feeds
the detector the defective configuration and requires rejection, then feeds it a
correct one and requires acceptance -- so the suite cannot pass by being
permissive, and cannot pass by being uniformly strict either.

### Level 3 -- the component-masking diagnostic

Whole-message removal cannot say *which part* of a message carries value. The
masking arms hold slot position and word count fixed while separating the
proposed answer from the reasoning:

```bash
python scripts/run_content_control.py \
    --source POOLS.jsonl --control-manifest TARGETS.jsonl --out-dir RUN
python analysis/replay/content_control_analyze.py --run_dir RUN
```

`POOLS.jsonl` is one row per problem (`problem_id`, `problem`, `reference`,
`hypotheses[5]`); `TARGETS.jsonl` names one `hypothesis_index` per problem. The
runner writes `replay_events.jsonl`, `RUN_META.json`, and `validation.json`;
the analyzer computes per-condition signed effects with a cluster bootstrap.

> **Unresolved naming caveat.** The paper's masking table describes **six**
> conditions -- these five plus a byte-identical repeat and a same-position
> approximate-length neutral replacement -- and 22 x 5 x 8 = 880 outcomes. This
> code implements five, and its analyzer consumes four effects
> (22 x 5 x 5 = 550). `semantic_mask` plausibly *is* the neutral replacement and
> `original_full` run twice plausibly *is* the repeat, but no manifest states
> that mapping, so it is **UNPROVEN**. The mechanism runs; the claim that it
> reproduces the paper's table does not yet hold. See
> `docs/PAPER_REPRODUCTION_MAP.md`.

### Level 4 -- full regeneration, honestly

The paper's campaign is five benchmarks (Omni-MATH-2 4,181 problems; JEEBench
515; SciBench 580; LAB-Bench 741; MaScQA 649) across two model families, with
role recruitment, five hypothesizers per problem, integration, leave-one-out
replay at K=2..5, repeated replay, and evaluator scoring. Order-of-magnitude
per full pass: **millions of model calls**, cluster-scale inference over weeks,
and raw records in the hundreds of gigabytes before sanitization. It is not a
laptop workload and this repository does not pretend to script it.

Three separate things stand between you and it: the benchmark text (each from
its own upstream source under its own license -- see `DATA.md`), the compute,
and the fact that **newly generated text will differ from ours** for the reasons
in Level 2. Aggregate counts can be compared against the derived records here;
strings cannot.

Two analyses in `analysis/replay/` belong to this level because they read raw
per-benchmark shards (`raw/<benchmark>/dhd/<model>/layer_a/part-00000.jsonl.zst`)
that are not published:

* `offline_routing_analysis.py` -- the only generator anywhere for
  `tab:app_single_full_2x2`. Runs with `--release_root`; its logic is unit-tested
  on synthetic records so you can read and verify it without the shards.
* `trace_example_report.py` -- shortlists behind `fig:main_trace_examples`. Needs
  both the shards and the original benchmark question text. **Its outputs are not
  redistributable**: they embed verbatim LAB-Bench (CC-BY-SA-4.0, carries a
  canary) and MaScQA (CC-BY-NC-SA-4.0) question text that this repository
  deliberately excludes. Run it locally; do not republish what it writes.

---

## Repository layout

```
README.md                      This file
REPRODUCE.md                   Step-by-step reproduction detail
DATA.md                        Data provenance and benchmark licensing
ENVIRONMENT.md                 Interpreter and dependency notes
LICENSE                        MIT
THIRD_PARTY_NOTICES.md         Upstream notices and dataset attributions
CITATION.cff / citation.bib    Citation metadata
ARTIFACT_MANIFEST.json         Machine-readable map: output -> inputs -> command
SHA256SUMS                     Checksums for every shipped file
requirements.lock              Pinned dependencies
pyproject.toml                 Package + pytest configuration
.env.example                   Configuration template (never commit .env)

src/dhd/                       Protocol runtime, standard library only
  config.py                      THE config layer: per-role model identity
  model_api.py                   OpenAI-compatible client + RoleRouter
  protocol.py                    Prompt construction from the paper configs
  replay.py                      Matched full-pool vs leave-one-out replay
  labels.py                      Boxed-answer extraction, trajectory-value labels
  content_control.py             The five matched masking arms
configs/paper/                 Exact paper prompts and protocol configuration
configs/smoke/                 Reduced config for the fixture smoke test
scripts/                       Entry points (all documented commands live here)
  dry_run.py                     Print what a live run would do; no network call
  run_smoke_test.py / .sh        Level 2 protocol smoke test
  run_content_control.py         Level 3 masking runner
  reproduce_analysis.py / .sh    Level 1 figures + headline cells
  recompute_signal_tables.py     Level 1 below-cell robustness tables
  validate_inputs.py             Checksum + row-count validation
analysis/                      Paper-facing analyses from the arXiv artifact
analysis/replay/               The three analyses the artifact lacked
figures/                       Figure scripts and their source CSVs
data/derived/                  Derived records (counts, summaries)
data/derived/signal_labels/    Per-signal / per-fold robustness records
data/fixtures/                 Tiny synthetic fixture for the smoke test
data/manifests/                Expected numeric summaries for verification
tests/                         Unit tests, including the model-identity suite
tools/portability_audit.py     Release check: paths, URLs, credentials, names
docs/                          Model dependency card, paper reproduction map
release_notes/                 Provenance and the changes made vs the sources
.github/workflows/             CI: tests + portability audit
```

## Configuration

Everything resolves through one layer, `src/dhd/config.py`. Full template in
[`.env.example`](.env.example). **No author endpoint is ever a default** -- every
connection value defaults to empty, and an unconfigured run skips rather than
pointing somewhere private.

Most specific wins: `DHD_<ROLE>_*` > `DHD_ACTOR_*` (recruiter + hypothesizer +
integrator) > `MODEL_API_*`. The `MODEL_API_BASE` / `MODEL_API_MODEL` /
`MODEL_API_KEY` names from the published artifact still work as the global
fallback, so existing instructions keep working -- but on their own they are the
collapsed single-model configuration, which this repository now **rejects** for
configs that declare two slots. Set the evaluator explicitly.

| Group | Variables |
|---|---|
| Per role | `DHD_{RECRUITER,HYPOTHESIZER,INTEGRATOR,EVALUATOR}_{BASE_URL,API_KEY,MODEL}` |
| Actor lane | `DHD_ACTOR_BASE_URL`, `DHD_ACTOR_API_KEY`, `DHD_ACTOR_MODEL` |
| Legacy fallback | `MODEL_API_BASE`, `MODEL_API_KEY`, `MODEL_API_MODEL`, `MODEL_API_TIMEOUT_S` |
| Assertions | `DHD_EXPECT_{ROLE}_MODEL` -- abort if the resolved id differs |
| Paths | `DHD_DATA_ROOT`, `DHD_CACHE_DIR`, `DHD_OUTPUT_DIR`, `DHD_ANALYSIS_INPUT_DIR`, `DHD_ANALYSIS_OUTPUT_DIR` |
| Run | `DHD_DATASET_ID`, `DHD_BENCHMARK`, `DHD_SAMPLE_LIMIT`, `DHD_REPLICATES`, `DHD_SEED` |
| Transport | `DHD_CONCURRENCY`, `DHD_MAX_RETRIES`, `DHD_RETRY_BACKOFF_S`, `DHD_TIMEOUT_S` |
| Decoding override | `DHD_TEMPERATURE_OVERRIDE`, `DHD_MAX_TOKENS_OVERRIDE` |

Every path default is repository-relative. `.env`, `*.key`, `*.pem`, and token
files are gitignored.

## Data

The Hugging Face dataset
[`AgentsSci/AAAI_Wrong-but-Useful`](https://huggingface.co/datasets/AgentsSci/AAAI_Wrong-but-Useful)
is **public**, but it redistributes third-party benchmark content and therefore
carries usage restrictions that this repository does not:

- **The dataset as a whole is NON-COMMERCIAL.** It includes MaScQA content under
  CC-BY-NC-SA-4.0 (`commercial_use = not_allowed`). Exclude
  `benchmark_id = mascqa` for a commercially usable subset.
- **Do not train on the LAB-Bench subset.** LAB-Bench (CC-BY-SA-4.0) carries an
  upstream do-not-train request. Note that the enforcing canary string is
  **absent** from those files (measured, 0 of 1,542 rows), so an automated
  contamination filter will not catch it for you -- filter
  `benchmark_id = labbench` explicitly.

Read the dataset card before downloading. You do **not** need the dataset for
Level 1: the derived data and figure source CSVs bundled in this repository are
what Level 1 uses, and they are sufficient for it.

This repository ships **no benchmark question text**, by design. Derived records
carry integer counts, rates, intervals, public benchmark and model labels, and
anonymized problem keys. The one exception is
`data/derived/integrator_uptake_audit.csv`, which carries short JEEBench answer
labels (MIT, permission notice reproduced in `THIRD_PARTY_NOTICES.md`) and
author-written paraphrases. LAB-Bench (CC-BY-SA-4.0, canary) and MaScQA
(CC-BY-NC-SA-4.0) content is deliberately excluded. Redistribution permission is
never inferred from public availability. Full decisions per benchmark: `DATA.md`.

## Portability audit

`tools/portability_audit.py` fails the build on author paths, private URLs,
credential literals, stale internal repository names, and review-anonymity
language.

It is built to be a real check rather than a reassuring one.

**Every pattern carries a positive control.** `python tools/portability_audit.py
--self-test` runs each pattern against a string that must match and one that
must not; a pattern matching neither is reported as BROKEN rather than clean, so
"0 findings" can never come from a dead regex.

**The scanner has no self-exemption.** Its patterns and its control strings are
assembled from fragments, so it contains none of the literals it forbids and is
scanned like every other file. Exempting it by path -- the obvious alternative
-- would have exempted everything in it, including a violation added later.

**The allowlist is keyed on the SHA-256 of an exact line**, not on a path and
not on a substring. Both weaker designs were tried and both were caught by the
control: a planted copyright line was exempted by a genuine, unrelated line in
the same file that happened to contain the same words. A line digest has no such
slack. Each entry carries a written justification, and an entry that stops
matching is reported so stale exemptions get removed rather than accumulate.

**CI proves the audit can fail before trusting that it passed.** It copies the
repository to a scratch tree, plants one violation of each of the five classes
*inside the allowlisted file*, and requires the audit to exit non-zero and name
all five. A clean scan is only reported after that control passes. Reproduce it
locally by appending a fake author path or key to a scratch copy.

Only `release_notes/PROVENANCE.md` is allowlisted, and only six specific lines
in it: the ones recording exactly which private strings were replaced. A
substitution you cannot see is a substitution you cannot check.

## Troubleshooting

**`SKIP: model API is not configured`** -- expected without configuration. Run
`python scripts/dry_run.py` to see which role is unset and which variable would
supply it.

**`ModelBindingError: ... both resolved to '<id>'`** -- you set only
`MODEL_API_MODEL`, so the integrator and the evaluator collapsed onto one model.
Set `DHD_EVALUATOR_MODEL` (and its base URL) explicitly. This is the guard
described above, working.

**`No matching distribution found for numpy==2.4.4`** -- your Python is older
than 3.11. Check `python -V`. This is the real floor, not 3.10.

**`ModuleNotFoundError: matplotlib` when a wrapper script runs** -- the `.sh`
wrappers call `python3`, which resolves against `PATH` and can miss an
unactivated venv. Either activate it, or name the interpreter:
`PYTHON=.venv/bin/python bash scripts/reproduce_analysis.sh`. The wrappers check
for the imports up front and say this rather than failing deep inside a
subprocess.

**`model_api_call_failed:HTTPError`** -- deliberately generic. The client never
puts headers, URLs, or credentials into an exception. Check your endpoint with
`curl` directly, and confirm the host with `scripts/dry_run.py`.

**`model_api_empty_content` / `unparseable_evaluator_verdict`** -- the endpoint
returned nothing usable, or the evaluator did not emit `Correctness: 0|1` or
`Verdict: PASS|FAIL`. Both are recorded as *operational failures* and are never
scored as wrong answers. Some endpoints need a larger `max_tokens` (override
with `DHD_MAX_TOKENS_OVERRIDE`) or reject `temperature=0` -- known
incompatibilities are listed in `docs/MODEL_DEPENDENCIES.md`.

**A run died partway** -- Level 1 is idempotent; just rerun it. Level 2 rewrites
`smoke_results.json` from scratch. Level 3 writes `validation.json` with
`complete: false` and a per-arm count; rerun with the same `--out-dir` to start a
fresh attempt, or analyze the partial run with
`content_control_analyze.py --allow_incomplete`.

**The audit fails on a file you added** -- read the `why:` line it prints. If
the string genuinely belongs, add an allowlist entry in
`tools/portability_audit.py` with a justification; do not broaden the pattern.

## Known limitations

From the paper, and they qualify everything above: trajectory-value labels
describe a message-pool-integrator context, not an intrinsic property of text,
and individual signs can change even with fixed problems and messages.
Repetition reduces but does not eliminate that uncertainty. Leave-one-out hides
a whole message in one fixed prompt order; the masking diagnostic only begins to
separate reasoning from its answer field, and *the source of the complete-message
advantage remains open*. Nested K prefixes are not randomized agent additions,
and one model family fills all reasoning roles within a run. Results may not
transfer to interactive debate, heterogeneous agent models, frontier models, or
tasks without a stable ground-truth answer.

Repository-specific, measured: the analysis gate's coverage is narrower than the
shipped data (above); 16 of 38 paper artifacts are marked UNPROVEN in
`docs/PAPER_REPRODUCTION_MAP.md` -- for most of them no generator was identified,
and for the rest the link between a shipped file and the table is not established; the 16,724-submission cross-evaluator set behind
`tab:compound_evaluator` was searched for and **not located**; and the
component-masking condition naming map is unresolved.

## Citation

```bibtex
@misc{yang2026wrongbutuseful,
  title         = {Wrong but Useful: Trajectory Value Beyond Answer Correctness in Multi-Agent Messages},
  author        = {Yang, Chih-Hsuan and Chowdhury, Anjir Ahmed and Yang, Cheng-Hau and Zheng, Weijian and Llorente, Fernando and Ma, Xiaolong and Li, Xinyang and Huerta, Eliu A. and Foster, Ian T. and Thakur, Rajeev},
  year          = {2026},
  eprint        = {2608.14375},
  archivePrefix = {arXiv},
  primaryClass  = {cs.AI},
  url           = {https://arxiv.org/abs/2608.14375}
}
```

Also cite the upstream benchmarks under their own licenses (see
`THIRD_PARTY_NOTICES.md`).

## License and contact

MIT (`LICENSE`). Third-party notices and per-benchmark attribution requirements
in `THIRD_PARTY_NOTICES.md`. Benchmark redistribution decisions in `DATA.md`.

Corresponding author: Chih-Hsuan Yang, Argonne National Laboratory --
bellayang@anl.gov. For reproduction problems, please open an issue and include
the output of `python scripts/dry_run.py` (it contains no credentials).

## Project resources and navigation

**This is the navigation hub for the whole project.** Public artifacts are linked; private and
HPC-only artifacts are named with their exact paths and the reason they are not published.

> **Scope note for anyone who is not the author.** This repository is the public artifact. The
> review-preparation workspace described below is **private** and not distributed: it contains
> mock-review material and reviewer-response drafts, which should not be public while the paper is
> under review at AAAI-27. Paths into it are recorded here so the project is resumable, not because
> the contents are downloadable.

### Public resources

| Resource | Link | Contents |
|---|---|---|
| **Code (this repo)** | [`ChihHsuan-Yang/AAAI_Wrong-but-Useful`](https://github.com/ChihHsuan-Yang/AAAI_Wrong-but-Useful) · branch **`main`** | DHD implementation, analysis pipeline, bundled derived data, tests |
| **Paper** | [arXiv:2608.14375](https://arxiv.org/abs/2608.14375) · [PDF](https://arxiv.org/pdf/2608.14375) | Public version of the submitted manuscript |
| **Project page** | [chihhsuan-yang.github.io/AAAI_Wrong-but-Useful](https://chihhsuan-yang.github.io/AAAI_Wrong-but-Useful/) | Findings, protocol, reproduction summary |
| **Dataset** | [🤗 `AgentsSci/AAAI_Wrong-but-Useful`](https://huggingface.co/datasets/AgentsSci/AAAI_Wrong-but-Useful) | Trajectory-value measurements, hypotheses, interventions, replay labels, registry. ⚠️ **non-commercial; no training on LAB-Bench** |
| **Model** | none released — see [`docs/MODEL_DEPENDENCIES.md`](docs/MODEL_DEPENDENCIES.md) | No checkpoint is published by this work |

**Which dataset version this paper uses.** The analyses here read the **bundled derived data in
this repository**, not a live download, so results do not move when an upstream card changes. The
Hugging Face dataset is the same derived data republished for convenience. Integrity is pinned by
[`SHA256SUMS`](SHA256SUMS) (CI-enforced) and [`ARTIFACT_MANIFEST.json`](ARTIFACT_MANIFEST.json);
verify with `sha256sum -c SHA256SUMS`. Upstream benchmarks and model cards are listed with their
own licenses in [`DATA.md`](DATA.md) and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
**Inference-time model identity cannot be pinned by hash:** the endpoints used for the paper do not
expose weight-revision hashes — see the caveat in [`ENVIRONMENT.md`](ENVIRONMENT.md).

**Where the code lives in this repository**

| What | Path |
|---|---|
| DHD implementation | [`src/dhd/`](src/dhd/) |
| Analysis pipeline | [`analysis/`](analysis/) — incl. [`analysis/replay/`](analysis/replay/), [`analysis/robustness/`](analysis/robustness/) |
| One-command reproduction | [`scripts/reproduce_analysis.sh`](scripts/reproduce_analysis.sh), [`scripts/reproduce_analysis.py`](scripts/reproduce_analysis.py) |
| Smoke test / dry run | [`scripts/run_smoke_test.sh`](scripts/run_smoke_test.sh), [`scripts/dry_run.py`](scripts/dry_run.py) |
| Masking (content-control) runner | [`scripts/run_content_control.py`](scripts/run_content_control.py), [`src/dhd/content_control.py`](src/dhd/content_control.py) |
| Paper→code→result map | [`docs/PAPER_REPRODUCTION_MAP.md`](docs/PAPER_REPRODUCTION_MAP.md) |
| Reproduction guide / environment | [`REPRODUCE.md`](REPRODUCE.md), [`ENVIRONMENT.md`](ENVIRONMENT.md) |

### Manuscript (Overleaf) — FROZEN

- **Overleaf project:** <https://www.overleaf.com/project/6a418ef00e035ab06ad30d5c>
  (git remote `https://git.overleaf.com/6a418ef00e035ab06ad30d5c`), branch **`main`**.
  The project is private: that URL returns **403** to anyone not shared on it (a non-existent
  project returns 404, so 403 confirms it exists and is access-controlled, not a dead link).
- **Manuscript:** `main.tex`, `main.pdf` at the Overleaf project root.
- **Rebuttal documentation mirror inside Overleaf:** `rebuttal/` at the project root — the same
  documentation tree as the private local workspace, so co-authors can read it without a checkout.
  Documentation only: no large raw data and no experiment outputs are mirrored there.
- **Frozen, verified by git blob identity** (stronger than hashing a copy):
  `main.tex` = `ac113bbbb7ff2785515dd106b58fb2df91c84873`,
  `main.pdf` = `921124cc4187692d2c0625e07740750ffd00e3c9`.
  Restored in Overleaf commit `fd4c2c6` — a **forward revert**, no history rewrite — byte-identical
  to the pre-edit baseline `a4a41cb`. Re-check with `git rev-parse HEAD:main.tex`; **if it differs,
  someone has edited the manuscript.** No proposed change has been applied to it.

### Private local workspace (not published)

- **Project root:** `/Users/bellayang/Documents/note/projects/AAAI-WBU`
- **Pre-rebuttal workspace:** `/Users/bellayang/Documents/note/projects/AAAI-WBU/rebuttal`
- **Restart point — open this first:** `rebuttal/HANDOFF.md`
- **Overleaf clone:** `paper/overleaf/` · **public-repo clone:**
  `release_orchestration_2026-09-23/staging/public_repo/`

### HPC / remote data (ALCF)

Large replay trees and per-run sensitivity outputs are **not in git** because of size. The derived
data bundled here is sufficient to reproduce every figure and table; these paths matter only for
re-deriving from raw runs.

| Filesystem | Exact path | Contents | Reachable from |
|---|---|---|---|
| `eagle` | `/lus/eagle/projects/AuroraGPT/bellayang/dhd_results` | Gemma results; `sensitivity/prompt_order/` holds `_cohort_ids` and `gemma` (**no `oss/` arm**) | **Crux, Polaris, Sophia** (shared mount) |
| `flare` | `/lus/flare/projects/AuroraGPT/bellayang/dhd_results` | OSS results, incl. OSS prompt-order data certified by the run's own `validation.json` | **Aurora only** (sole flare mount) |

ALCF login is **OTP-only**: a batch-mode SSH probe can never succeed, so a failed non-interactive
test is not evidence that a host is down. Test with a real interactive command.

**Do not rerun without a reason** (all complete; rerunning costs HPC time and risks a library
version silently changing a published number): the sensitivity campaign (two of three arms are
already published as `tab:matched_sensitivity`); the masking/statistics analyses (method now pinned
— an unpinned rerun *will* disagree); the literature search; the prompt-order extraction (data
already pulled and hash-verified); the router (future work); any endpoint campaign.

---

## AAAI pre-rebuttal status

**Status: pre-rebuttal work complete (2026-09-30). Manuscript frozen. Awaiting the actual reviews.**
Nothing is running: no jobs, no agents, no endpoint campaigns.

Preparation was driven by **internal AI-generated mock reviews**, not by real AAAI reviews, which
had not been received. Work was confined to the private workspace; **the manuscript was not edited**,
and every proposed change is held as an unapplied patch.

- **Workspace (local):** `/Users/bellayang/Documents/note/projects/AAAI-WBU/rebuttal`
- **Workspace (Overleaf mirror):** `rebuttal/` in the Overleaf project above
- **Entry point:** `rebuttal/HANDOFF.md`

### Workspace map

| Path (under `rebuttal/`) | Contents |
|---|---|
| `HANDOFF.md` | **Restart point.** Self-contained: status, freeze proof, findings, full file map, how to resume |
| `REBUTTAL_PLAN.md` | Master issue table — one row per concern: reviewer, priority, status, evidence, result location, code location, implication, remaining action |
| `DRAFT_RESPONSE.md` | Current rebuttal draft (~4,150 words): per-reviewer responses, preamble, concessions |
| `REBUTTAL_STORYLINE.md` | Framing and storyline, incl. §6b five-question audit per analysis |
| `TODO.md` | Task board (all closed) |
| `issues/I01_actionability_upper_bound.md`–`I15` | One self-contained document per concern, `I01_...` through `I15_...` (14 files) |
| `results/` | Completed result reports (14 files) + `T4_sensitivity_raw/`, `logs/` |
| `results/*_COORDINATOR_VERIFICATION.md` | Independent second-pass verification of each task |
| `experiments/` | Analysis scripts (9) written for the rebuttal |
| `experiments/router/` | **Future work** — router pipeline, `STATUS: FUTURE WORK` banner |
| `evidence/VERIFIED_FACTS_FOR_REBUTTAL.md` | Facts checked by inspection (V1–V18) — read before believing any reviewer claim |
| `evidence/ASSET_INVENTORY.md` | Where every asset lives |
| `proposed_paper_changes/` | **Unapplied** manuscript patches (8) + 3 wording notes |
| `proposed_paper_changes/figures/` | Candidate Figure 2: `fig2_A_submitted_CURRENT.{pdf,png}` (as submitted), `fig2_C_redrawn_candidate.{pdf,png}` (proposed), `make_fig2_candidate.py` (source) |
| `plan/CONCERN_MAP.md`, `plan/concerns.csv` | De-duplicated concern map across all mock rounds |
| `mock_reviews/round2_2026-07-26/`, `round3_2026-09-27/` | The mock reviews themselves |

**Superseded — do not use:** `plan/REBUTTAL_PLAN.SUPERSEDED.md` (replaced by the top-level
`REBUTTAL_PLAN.md`). `results/PRE_REBUTTAL_RESULTS.md` is a **chronological log**, useful for *why*
something happened in a given order; the `issues/` files are the authoritative per-concern record.
Retracted passages inside `results/T17_unblock_report.md` and `results/T17_COORDINATOR_VERIFICATION.md`
are **struck through rather than deleted**, so a claim that circulated stays readable — do not quote
struck text as a finding.

### What the outcomes were

**Positive — defend these.** Statistical-dependence CIs extracted for both model families, with
pooled figures reproducing the paper exactly (I02). The masking design is larger than reviewers
assumed: 22 messages / 10 anchors / 880 outcomes, with condition naming proven by an 18/18 exact-rate
cross-match (I08). The compound-evaluator table reproduces exactly: 140 → 0.6714 → 67.1 (I12). The
renderable-signal filter retains 98.3% / 98.4%, and dropped records have **no direction by
construction** (I13).

**Two reviewer claims are demonstrably false.** "Figure 3 contains unparsed placeholders" — it
renders; the reviewer opened a `.txt` (I06). "The models are fictional" — both cards return HTTP 200,
with a fabricated id returning 401 as a negative control (I07).

**Mixed / boundary — present as scope, not failure.** Actionability is a *same-problem* opportunity
and an upper bound, not unseen-problem generalization (I01). Cross-integrator transfer is weak.
The router detects **problem/pool-level opportunity** but **not which message to select** (future work).

**Corrections found against our own claims** — recorded because a rebuttal repeating a withdrawn
number is worse than one conceding:
1. **Masking significance.** Previously reported p = 0.0496. The value is scipy-method dependent and
   straddles 0.05 (`approx` 0.0496 / `exact` zeros-dropped 0.0508 / **`exact` 0.0547**). Honest
   status: **suggestive, not significant**; the method is now pinned. The frozen manuscript makes no
   significance claim here, so nothing published is wrong.
2. **Related work** — a mischaracterization; corrected in `proposed_paper_changes/T5_related_work_correction.md`.
   The novelty delta **survives**.
3. **Self-citation trap.** arXiv:2511.10687 shares this paper's first and last authors, proposes
   message-level credit, and is **absent from `references.bib`** — low as a novelty threat, high as
   an omission, and a double-blind identity risk if cited. Decide deliberately.
4. **The supplement three reviewers penalized belongs to a different paper** (a separate ICLR
   submission), verified by token absence *with a positive control* plus a 496-file / 344.5 MB
   inventory match. **Corollary:** that audit can no longer be cited as validation of *our*
   supplement — the draft was corrected in three places.

**Future work, not current-paper work.** The router (`rebuttal/experiments/router/`). Bring it into
a rebuttal **only** if a real reviewer asks for actionability or routing.

### Mock review history

Three rounds of internal AI mock review. **Round 3** (2026-09-27, files in
`rebuttal/mock_reviews/round3_2026-09-27/`) produced five reviews — R1 gpt5.6-sol (technical, score
5), R2 inkling (empirical, 5), R3 claude-opus-4.8 (novelty, 6), R4 gemini-4.8-fast (consistency, 4),
R5 claude-sonnet-4.6 (generalist, 6) — mean **5.2**, with every reviewer stating a conditional
post-repair score of 6–7. **Round 2** (2026-07-26, `rebuttal/mock_reviews/round2_2026-07-26/`) is
five earlier reviews plus a summary. The de-duplicated map across both rounds is
`rebuttal/plan/CONCERN_MAP.md` (19 concerns, C1–C19).

| Concern | Raised by | Pri | Issue doc | Status | Evidence |
|---|---|---|---|---|---|
| Actionability: no demonstrated payoff | R3 P0, R5; **round-2 #1** | P0 | `issues/I01_actionability_upper_bound.md` | **Partially resolved** — scientific decision pending | Cross-fitted one-removal audited: +1.68 [0.88, 2.50] / +2.61 [1.76, 3.54], 10/10 cells |
| Statistical dependence / CIs | R1 P0, R2 P0 | P0 | `issues/I02_dependence_units_ci.md` | **Resolved** | Problem-clustered CIs, both families; pooled reproduces paper |
| Abstract over-promises | R5 P0, R3, R4 | P0 | `issues/I05_abstract_calibration.md` | **Resolved (prepared)** | Absolute rates 6.3% / 3.2% derived from source |
| Supplement unreachable | **all five** | P0 | `issues/I04_supplement_packaging.md` | **Resolved by reframing** | Archive belongs to a different submission; 496-file / 344.5 MB match |
| Masking scope + confounds | R2 P0; R1, R3, R5 | P0 | `issues/I08_masking_scope.md` | **Resolved**; CIs optional | 22 msgs / 10 anchors / 880 outcomes; naming proven 18/18 |
| ❌ "Figure 3 has placeholders" | R4 P0 | P0 | `issues/I06_reviewer_error_figure3.md` | **Resolved — claim is FALSE** | Figure renders; 0 regex hits in both PDFs; positive control fires |
| ❌ "Models are fictional" | R4 P1.1 | P1 | `issues/I07_reviewer_error_model_identity.md` | **Resolved — claim is FALSE** | Both cards HTTP 200; fabricated id 401 |
| k/K notation drift | R4 P1.3 | P1 | `issues/I03_figure2_notation.md` | **Resolved (prepared)** | Confirmed in artwork text; `main.tex` already clean |
| Novelty differentiation | R3 P1-1 | P1 | `issues/I09_novelty_differentiation.md` | **Partially resolved** — framing decision | Comparison table; 3-part delta (unit / cross-classification / conditioning) |
| Evaluator agreement placement | R5 P1-2 | P1 | `issues/I11_evaluator_agreement_placement.md` | **Resolved (prepared)** | 67.1 / 77.7 verified at source |
| Cross-evaluator reproducibility | R1 P1.3 | P1 | `issues/I12_compound_evaluator_reproduced.md` | **Resolved** | `tab:compound_evaluator` reproduces exactly; the 16,724 set is absent after 4 controlled passes |
| Renderable-signal filter drop | pre-emptive | P2 | `issues/I13_filter_retention.md` | **Resolved (prepared)** | 98.3% / 98.4% retention; dropped records have no direction by construction |
| Figure 2 editable source | operational | P2 | `issues/I14_figure2_source_search.md` | **Resolved — source does not exist** | Exhaustive search incl. Overleaf history; redraw is feasible |
| Audit of "already satisfied" (C10, C15, C17–C19) | various | — | `issues/I15_already_satisfied_audit.md` | **Resolved with evidence** | Per-concern checks; C17 withdrawn by R2 |

Reviewer-contingent / deliberately not done: regenerating the 16,724-submission verifier set (the
data does not exist), compute-matched baselines, and any retrain or rerun.

### Task → code → result → issue → draft

Scripts marked **local-only** are in the private workspace, not this repository: they read absolute
HPC paths or private replay trees and would not run for an outside reader.

| Task | Code | Raw data | Result report | Issue | Draft section |
|---|---|---|---|---|---|
| **T1** masking exact binomial CI | `rebuttal/experiments/t1_masking_exact_binomial_ci.py` *(local-only)*; public mechanism: [`src/dhd/content_control.py`](src/dhd/content_control.py) | Masking pilot, eagle `_priorityD_pilot_20260725` | `rebuttal/results/T1_T2_T3_statistics.md` | `issues/I08_masking_scope.md` | masking scope |
| **T2** rendered-filter drop reconstruction | `rebuttal/experiments/t2_rendered_filter_drop_reconstruction.py` *(local-only)* | Replay records (HPC) | `rebuttal/results/T1_T2_T3_statistics.md` | `issues/I13_filter_retention.md` | filter retention |
| **T3** correct-class pooled CI | `rebuttal/experiments/t3_correct_class_pooled_ci.py` *(local-only)* | `SIGNAL_DIRECTION_ROBUSTNESS.json` (eagle + flare) | `rebuttal/results/T1_T2_T3_statistics.md` | `issues/I02_dependence_units_ci.md` | dependence + CIs |
| **T4** sensitivity campaign | `rebuttal/experiments/t4_sensitivity_extract.py`, `t4_prompt_order_analyze.py` *(local-only)* | eagle/flare `sensitivity/` | `rebuttal/results/T4_sensitivity_campaign.md`, `T4_sensitivity_raw/` | `issues/I15_already_satisfied_audit.md` | robustness |
| **T5** novelty validation | none (literature) | arXiv | `rebuttal/results/T5_novelty_validation.md` | `issues/I09_novelty_differentiation.md` | novelty delta |
| **T8/T9** router | `rebuttal/experiments/router/` *(local-only, future work)* | `router/build/router_rows_k5.parquet` (62,445 × 45) | `rebuttal/results/T8_router_dataset.md`, `T9_router_training.md`, `router/RESULTS.md` | — | not used unless asked |
| **T12** OSS prompt order | `rebuttal/experiments/t17_extract_oss_prompt_order_remote.py`, `t17_prompt_order_analyze_param.py` *(local-only)* | flare `sensitivity/prompt_order/oss` | `rebuttal/results/T17_unblock_report.md` | `issues/I15_already_satisfied_audit.md` | robustness |
| **T13** signal-direction CIs | `rebuttal/experiments/pull_signal_direction_ci.py` *(local-only)*; public summarizer: [`analysis/robustness/summarize_signal_direction.py`](analysis/robustness/summarize_signal_direction.py) | `SIGNAL_DIRECTION_ROBUSTNESS.json` | `rebuttal/results/T17_unblock_report.md` | `issues/I02_dependence_units_ci.md` | dependence + CIs |
| **T17** coordinator verification | n/a | n/a | `rebuttal/results/T17_COORDINATOR_VERIFICATION.md` | — | method notes |

### Methodological lesson from the closeout

The closeout audit surfaced **five false nulls in one run**, each an *instrument's own limit* read as
a fact about the world: a Hugging Face page-size truncation; an arXiv HTTP 429 with an empty body; a
`find -maxdepth 8` against a depth-9 file; a "control" that moved the search root *and* the depth
bound together; and a control job that returned nothing because it had been killed during a sweep
for stale processes.

> **Absence claims must be tested directly, with controls that hold all but one variable fixed, in
> the environment where the failure occurred.**

Corollaries: hold one variable (a "failure to reproduce" that changes file, filesystem and root at
once tests nothing); run it where it broke (BSD `find` on macOS certifies nothing about GNU `find`
on Aurora); make the control fail on purpose before trusting it to pass; and a job is not finished
until you read its output — read a process's full command line before killing it, since age in `ps`
is not evidence of staleness.

### How to resume when the real reviews arrive

1. Re-verify the freeze: `git rev-parse HEAD:main.tex` must be `ac113bbb…`. If not, stop and ask.
2. Map each real concern onto the existing `I01`–`I15` rows in `REBUTTAL_PLAN.md` — most are already
   answered, with evidence, result and code locations per row.
3. Open a new `issues/I16…` only for genuinely new concerns; do not edit a closed one.
4. Adapt `DRAFT_RESPONSE.md` to the real reviewer numbering — it is written for mock R1–R5 and that
   mapping will not survive contact.
5. Apply patches from `proposed_paper_changes/` **only after the freeze is lifted.**

---

## Review status and maintenance

**This repository is public. The paper is under review at AAAI-27.** The code, data and documented
results here are the submitted artifact and are **frozen** for the review period: the manuscript is
unchanged, and no result in this repository has been revised since submission.

Review-preparation materials (reviewer-response drafts, per-concern analyses and unapplied
manuscript patches) are kept in a private workspace and are intentionally **not** published here,
to avoid pre-empting the review. Two things from that work do belong in the public record now,
because they concern how a reader should interpret what is in this repository:

- **The component-masking contrast is suggestive, not significant.** For `reasoning_masked` vs
  `full`, the paired Wilcoxon p-value depends on which method SciPy selects, and it straddles 0.05:
  `approx` 0.0496, `exact` with zeros dropped 0.0508, **`exact` 0.0547**. Our analysis code now pins
  the method explicitly rather than relying on `method="auto"`, whose choice varies with SciPy
  version when zeros are present. **The paper makes no significance claim for this contrast**, and
  none should be inferred from it. If you reproduce this number and get 0.0496, check your pinning.
- **Headline rates are pooled per model, not per benchmark.** Per-benchmark cells range 23.6%–49.6%.
  A sentence of the form "four in ten in every benchmark" is not supported.

Reproduction problems and errors are welcome as issues during the review period; we will correct
factual errors in the repository. Larger revisions wait for the review outcome.

Large intermediate artifacts (full replay trees, per-run sensitivity outputs) live on ALCF storage
rather than in git, because of size. The published derived data and the analysis code in
`analysis/` are sufficient to reproduce every figure and table; see `REPRODUCE.md` and `DATA.md`.

## Acknowledgments

This research used resources of the Argonne Leadership Computing Facility, a
U.S. Department of Energy (DOE) Office of Science user facility at Argonne
National Laboratory (ANL) operated under Contract No. DE-AC02-06CH11357. The
work was also supported under the same contract by the DOE Office of Science's
Advanced Scientific Computing Research Program and by Laboratory Directed
Research and Development (LDRD) funding from ANL, provided by the Director, DOE
Office of Science.
