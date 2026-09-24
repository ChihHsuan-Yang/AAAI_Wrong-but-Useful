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

## Acknowledgments

This research used resources of the Argonne Leadership Computing Facility, a
U.S. Department of Energy (DOE) Office of Science user facility at Argonne
National Laboratory (ANL) operated under Contract No. DE-AC02-06CH11357. The
work was also supported under the same contract by the DOE Office of Science's
Advanced Scientific Computing Research Program and by Laboratory Directed
Research and Development (LDRD) funding from ANL, provided by the Director, DOE
Office of Science.
