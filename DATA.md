# Data and Licensing

This artifact is designed so that **no third-party benchmark question text is
redistributed**. The included data objects are:

1. **Derived aggregate records** — per-benchmark and pooled counts of the
   correctness / trajectory-value taxonomy, plus the numeric summaries that back
   each table and figure. With the single exception noted below, these contain
   only integer counts, rates, confidence intervals, and public benchmark/model
   labels — no problem text, no answers, no author/user/host/account fields, and
   no file-system paths.
2. **One qualitative mechanism record** — `data/derived/integrator_uptake_audit.csv`
   is the paper's ten-case integrator-uptake study, drawn entirely from
   **JEEBench (MIT-licensed)**. It contains short answer labels (e.g. `ACD`,
   numeric values), JEEBench problem identifiers, and brief author-written
   `evidence_summary` paraphrases of the reasoning. This is redistribution-safe
   under JEEBench's MIT license. No other benchmark contributes text or answers,
   and no LAB-Bench, MaScQA, SciBench, or Omni-MATH-2 question text or answers
   appear anywhere in the artifact.
3. **Release-safe signal-level records** (`data/derived/signal_labels/`) — per-signal
   and per-fold label tables that let the matched-sensitivity and cross-fitted
   one-removal robustness tables be recomputed *below* the already-aggregated
   cells (see `REPRODUCE.md`). Each row carries only a public benchmark label, a
   **stable anonymized problem key** (a one-way hash, not the benchmark-native
   identifier), integer indices, numeric trajectory-value/accuracy values, and
   categorical labels. Missing / null / operational-failure states are preserved
   as explicit values and are never converted into incorrect answers. These files
   contain no question text, agent/message text, reference answers, accounts,
   machine names, or file-system paths.
4. **A tiny synthetic fixture** (`data/fixtures/smoke_pool.jsonl`) — two
   hand-written toy problems with fabricated hypothesis pools, used only by the
   protocol smoke test. It is original content created for this artifact and is
   covered by this artifact's license.

Some derived records (e.g. per-item multiplicity results) reference stable
benchmark *problem identifiers* for traceability. Identifiers and aggregate
statistics are not the licensed question content; no question text or answers are
included for LAB-Bench, MaScQA, SciBench, or Omni-MATH-2. The `signal_labels/`
records go further and use anonymized problem keys rather than native
identifiers.

The only upstream benchmark content reproduced verbatim is the short JEEBench
answer labels in `integrator_uptake_audit.csv`; JEEBench is MIT-licensed and its
required copyright and permission notice is reproduced in
`THIRD_PARTY_NOTICES.md`.

Because raw questions are never included, running the full protocol on the real
benchmarks requires acquiring each dataset from its upstream source under that
dataset's own license (see the table below), then generating hypothesis pools
with a compatible model API.

## Benchmark license and redistribution decisions

| Benchmark | Domain | Upstream license | Redistribute question text here? | What this artifact ships |
|---|---|---|---|---|
| Omni-MATH-2 | Competition mathematics | Upstream math-competition source terms | No | Derived aggregate counts only |
| JEEBench | Exam physics / chemistry / math | MIT | No question text | Derived aggregates; short answer labels and author paraphrases in the uptake audit |
| SciBench | College science reasoning | MIT | Not shipped (not needed) | Derived aggregate counts only |
| LAB-Bench | Biology protocol QA | CC-BY-SA-4.0 (copyleft + canary) | No | Derived aggregate counts only |
| MaScQA | Materials-science QA | CC-BY-NC-SA-4.0 (non-commercial, share-alike) | **Intentionally not included** | Derived aggregate counts only |

Decision rationale:

- **MIT** (JEEBench, SciBench) would permit redistribution with attribution, but
  this artifact does not need raw questions for either the analysis reproduction
  or the protocol smoke test, so none are included.
- **CC-BY-SA-4.0** (LAB-Bench) is copyleft and carries a canary string; to avoid
  any share-alike or canary-propagation obligation, no LAB-Bench text is
  included.
- **CC-BY-NC-SA-4.0** (MaScQA) is non-commercial and share-alike. Its content is
  **intentionally not included** here to avoid propagating the non-commercial and
  share-alike redistribution obligations into this general-purpose artifact; only
  aggregate statistics about the dataset are reported, not the dataset itself.

Redistribution permission is **not** inferred from public availability; each
decision above is based on the dataset's stated license.

## Acquiring the raw datasets (for full protocol reproduction)

To reproduce the measurement protocol on real data rather than the fixture:

1. Obtain each dataset from its official upstream release under that dataset's
   license and record the version/revision you downloaded.
2. Apply the paper's eligibility filter: keep one row per problem, and drop
   hypotheses with no renderable content in any integrator-visible field
   (`proposed_answer`, `reasoning_direction`, `key_idea`, `critical_assumption`,
   `what_to_check`, `confidence`). This mirrors the signal-eligibility rule used
   for the headline matrices.
3. Generate five independent hypotheses per problem with the recruiter and
   hypothesizer prompts in `configs/paper/dhd_config.yaml`, using a compatible
   model API (see `REPRODUCE.md`).
4. Run the matched full-pool and leave-one-out integration conditions and score
   each output with the evaluator prompt.

## Expected coverage (for verification without raw text)

The derived records in `data/derived/` and `figures/` encode the eligible-signal
counts per benchmark, pool size `K`, and proposal-correctness cell. Anyone
regenerating the pipeline on licensed raw data can compare their recomputed
counts against these included aggregates to confirm alignment, without this
artifact ever exposing the underlying questions.

## Attribution

If you use the derived statistics, cite the corresponding upstream benchmarks
under their respective licenses (MIT for JEEBench and SciBench; CC-BY-SA-4.0 for
LAB-Bench, preserving attribution and canary; CC-BY-NC-SA-4.0 for MaScQA; the
upstream terms for Omni-MATH-2).
