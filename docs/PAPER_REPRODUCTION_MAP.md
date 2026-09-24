# Paper reproduction map

One row for every figure and table in arXiv:2608.14375 -- **38 items, 10 figures
and 28 tables**, enumerated from `\begin{figure}` / `\begin{table}` and
`\label{fig:|tab:}` across the paper source.

Each row carries exactly one status:

| Status | Meaning | Count |
|---|---|---|
| `OFFLINE-DETERMINISTIC` | Reproducible here, now, from data in this repository, with no model call. Deterministic. | **12** |
| `REQUIRES-LIVE-INFERENCE` | The generator is here and runs, but producing the numbers needs calls to a live endpoint. Values will not match ours exactly. | **2** |
| `REQUIRES-PRIVATE-DATA` | The generator is here and runs, but its inputs (raw replay shards, or licensed benchmark text) are not published. | **8** |
| `UNPROVEN` | No generator was identified, or the link between a shipped file and the table is not established. Stated as unknown rather than guessed. | **16** |

Total: **38**.

A status is about *this repository*, not about the paper's correctness. An
`UNPROVEN` row means nobody has shown how to regenerate it from what is
published here -- several are appendix tables that `REPRODUCE.md` has always
said are stated inline or need the raw release root.

Three findings worth reading before you use this table:

* **`tab:compound_evaluator` and `fig:verifier_agreement` rest on a
  16,724-submission cross-evaluator set that two independent searches failed to
  locate.** Both are marked `UNPROVEN` for that reason, not because a script is
  missing.
* **`tab:component_masking`'s condition naming is unresolved.** Both halves of
  the generator are ported and runnable, but the paper describes six conditions
  and 880 outcomes where this code implements five and consumes four effects
  (550). The obvious mapping is plausible and unrecorded. Do not report this
  table as reproduced.
* **`fig:main_trace_examples` cannot be regenerated at all** from anything here:
  it quotes verbatim agent message text, which is not published, and the
  shortlisting script's outputs embed benchmark question text this repository
  deliberately excludes on licensing grounds.


## OFFLINE-DETERMINISTIC (12)

| Kind | Label | What it shows | Generator | How to run | Notes |
|---|---|---|---|---|---|
| figure | `fig:dhd-protocol` | The DHD protocol: recruiter assigns five roles | - | - | Hand-drawn schematic PDF in the arXiv source; not data-driven, no generator. Nothing to reproduce. |
| figure | `fig:loo-replay` | Two replay mechanisms: in-pool LOO and single-message | - | - | Hand-drawn schematic PDF; not data-driven. |
| figure | `fig:correctness_flip_direction` | Direction of in-pool LOO effects among correctness flips | `figures/make_correctness_flip_direction.py` | `bash scripts/reproduce_analysis.sh` | Source CSV manifest-listed and checksum-validated. 8 rows; note the gate checks only the 4 In-pool LOO rows. |
| figure | `fig:prompt_interface` | Compact DHD prompt surfaces | `configs/paper/dhd_config.yaml` | - | Prompt text rendered inline in LaTeX from the config. Read the config; nothing is plotted. |
| figure | `fig:generation_integration_gap_models` | Candidate availability and integration outcomes across model families | `figures/make_generation_integration_gap.py` | `bash scripts/reproduce_analysis.sh` | Two-panel float; both source CSVs shipped and manifest-listed. |
| figure | `fig:cross_benchmark_trajectory_value` | Off-diagonal in-pool LOO outcomes across benchmarks and model families | `figures/make_cross_benchmark_trajectory_value.py` | `bash scripts/reproduce_analysis.sh` | Headline taxonomy figure; 20-row source CSV shipped. |
| figure | `fig:loo_by_k_appendix` | Per-message LOO rates by K and benchmark | `figures/make_loo_by_k_appendix.py` | `bash scripts/reproduce_analysis.sh` | 80-row source CSV shipped. |
| table | `tab:twobythree` | Exact proposal-correctness x observed-replay-effect counts | `scripts/reproduce_analysis.py` | `bash scripts/reproduce_analysis.sh` | Headline taxonomy cells, compared against data/manifests/expected_summaries.json. Exact at the aggregated-cell level. |
| table | `tab:matched_sensitivity` | Matched sensitivity over 20 frozen problems per benchmark | `scripts/recompute_signal_tables.py` | `bash scripts/reproduce_analysis.sh` | Recomputed from per-signal records BELOW the aggregated cells (3 x 500 rows) and compared to expected_signal_tables.json. Point estimates only; the paper's bootstrap CIs are not recomputed. |
| table | `tab:app_decoding` | Role-specific decoding settings shared by both model families | `configs/paper/dhd_config.yaml` | `python scripts/dry_run.py` | Transcription of the shipped configs. dry_run.py prints the same values as resolved for your run. See docs/MODEL_DEPENDENCIES.md. |
| table | `tab:cross_fitted_one_removal` | Micro-pooled accuracy on held-out replay block, cross-fitted one-removal | `scripts/recompute_signal_tables.py` | `bash scripts/reproduce_analysis.sh` | Recomputed from 9,995 per-fold records and compared to expected_signal_tables.json (oss gain 1.68pp n=5000; gemma 2.61pp n=4995). |
| table | `tab:cross_fitted_one_removal_by_benchmark` | Cross-fitted accuracy gain by benchmark | `scripts/recompute_signal_tables.py` | `bash scripts/reproduce_analysis.sh` | Same records, split by benchmark; expected values in the manifest. |

## REQUIRES-LIVE-INFERENCE (2)

| Kind | Label | What it shows | Generator | How to run | Notes |
|---|---|---|---|---|---|
| table | `tab:repeated_replay` | Controlled repeated replay at K=5, 200 problems per benchmark | - | - | The upstream repeated-replay runner is NOT ported: it reached the model through the authors' internal agent framework. Only its content-control arms were rebuilt here (scripts/run_content_control.py). Regenerating this table requires a full repeated-replay campaign against live endpoints; the recorded run outputs are not published. |
| table | `tab:component_masking` | Integrator success in the component-masking diagnostic (22 cases x 5 reps x 8 outcomes) | `scripts/run_content_control.py + analysis/replay/content_control_analyze.py` | `python scripts/run_content_control.py --source P --control-manifest T --out-dir RUN && python analysis/replay/content_control_analyze.py --run_dir RUN` | Both halves are ported and runnable against your own endpoint; the summary JSON of the paper's run ships (data/derived/component_masking_pilot_summary.json) and its rates match the table. BUT the condition naming map is UNPROVEN: the paper describes 6 conditions and 880 outcomes (22x5x8); this code implements 5 and consumes 4 effects (22x5x5=550). semantic_mask is PLAUSIBLY the neutral replacement and a repeated original_full PLAUSIBLY the byte-identical repeat, but nothing on record states it. Do not claim this reproduces the table until that is confirmed. |

## REQUIRES-PRIVATE-DATA (8)

| Kind | Label | What it shows | Generator | How to run | Notes |
|---|---|---|---|---|---|
| figure | `fig:main_trace_examples` | Example trace records for two real OSS five-message LOO events | `analysis/replay/trace_example_report.py` | `python analysis/replay/trace_example_report.py --release_root R --data_root D --output_dir O` | Hand-typeset LaTeX; the script produces the shortlist the examples were drawn from. Needs raw replay shards AND benchmark question text, neither published. Outputs embed LAB-Bench/MaScQA text and are NOT redistributable. The figure itself quotes verbatim message text and cannot be regenerated from anything in this repository. |
| table | `tab:app_majority` | Pooled offline K=5 majority diagnostic | `analysis/run_majority_diagnostic.py` | `python analysis/run_majority_diagnostic.py --release_root R` | Recorded OUTPUT ships (data/derived/majority_diagnostic.{csv,json}) and is checksum-validated; recomputing needs the raw release root. Requires zstandard. |
| table | `tab:repeated_effect_by_correctness` | Mean repeated trajectory-value estimate for OSS by proposal correctness | `analysis/analyze_repeated_effect_by_correctness.py` | `python analysis/analyze_repeated_effect_by_correctness.py --release_root R` | Recorded output ships (data/derived/repeated_effect_by_correctness.json); recompute needs the raw release root. |
| table | `tab:problem_blocked_multiplicity` | Problem-blocked multiplicity check for repeatable wrong-helpful effects | `analysis/problem_blocked_replay_multiplicity.py` | `python analysis/problem_blocked_replay_multiplicity.py --release_root R` | Recorded output ships; recompute needs the raw release root. Has its own unit test (analysis/test_problem_blocked_replay_multiplicity.py) which DOES run offline in `pytest`. |
| table | `tab:app_single_full_2x2` | Single-message success crossed with K=5 integration success by benchmark | `analysis/replay/offline_routing_analysis.py` | `python analysis/replay/offline_routing_analysis.py --release_root R --output_dir O` | The ONLY generator anywhere for these cells (shared success / observable interference / observable synergy / shared failure); absent from the arXiv artifact entirely. Ported and standalone here, but needs raw per-benchmark layer_a shards, which are not published. Its logic IS unit-tested offline on synthetic records. |
| table | `tab:app_routing` | Pooled recorded-outcome budget-one diagnostic | `analysis/run_offline_review_closure.py` | `python analysis/run_offline_review_closure.py --release_root R` | The artifact script is authoritative: the paper's table has 5 policies including Answer consensus, which the ported worktree script does not implement. Recorded output ships (data/derived/offline_policy_bootstrap.csv); recompute needs the raw release root + zstandard. |
| table | `tab:app_routing_bootstrap` | Paired problem-bootstrap contrasts (95% percentile CIs) | `analysis/run_offline_review_closure.py` | `python analysis/run_offline_review_closure.py --release_root R` | Recorded output ships and matches the paper exactly (OSS correctness-minus-random 4.63 [4.25, 5.00] vs CSV 4.627 / 4.25 / 5.004). Recompute needs the raw release root. |
| table | `tab:app_regret_sources` | Sources of the proposal-correctness gap vs best recorded outcome | `analysis/run_offline_review_closure.py` | `python analysis/run_offline_review_closure.py --release_root R` | Recorded output ships and reconciles with the paper (OSS wrong-only route 246+91=337 problems, 2.541+1.365=3.906 -> 3.91). Recompute needs the raw release root. |

## UNPROVEN (16)

| Kind | Label | What it shows | Generator | How to run | Notes |
|---|---|---|---|---|---|
| figure | `fig:protocol` | DHD protocol prompt/role description | - | - | A LaTeX float with no includegraphics and a caption near-identical to fig:dhd-protocol. Possibly a stale duplicate label; UNPROVEN whether a graphic was intended. |
| figure | `fig:verifier_agreement` | Pairwise agreement among three LLM evaluators (N=16724) | `figures/make_evaluator_agreement.py` | `bash scripts/reproduce_analysis.sh` | The 3-row source CSV regenerates a figure, but NAME MISMATCH: the manifest calls it fig_evaluator_agreement, the paper includes fig_verifier_agreement.pdf. Almost certainly the same figure renamed, but not confirmed. Separately, the N=16,724 cross-evaluator submission set behind it was searched for and NOT LOCATED by two independent passes. |
| table | `tab:measurement_summary` | Final accuracy for K=0 independent and K=5 integration | - | - | No generator identified; not in the manifest's tables list. Stated inline in the paper. |
| table | `tab:datasets` | Five-benchmark suite with N unique problems | `figures/benchmark_properties_source.csv` | - | The 5-row CSV is shipped and checksum-validated and is a plausible source, but no manifest entry maps it to this table. Linkage UNPROVEN. |
| table | `tab:loo_otherbench` | Signed LOO outcomes at K=5 across benchmarks (OSS) | - | - | No generator identified; not in the manifest's tables list. |
| table | `tab:app_analysis_scope` | Gemma protocol and LOO analysis samples | - | - | No generator identified. |
| table | `tab:app_k_accuracy` | Accuracy for nested DHD pools K=0..5 | - | - | No generator identified. |
| table | `tab:app_single_hypothesis_by_dataset` | Dataset drill-down for single-message replay (OSS) | - | - | No generator identified. |
| table | `tab:wrong_effect_direction` | Direction of correctness flips from wrong proposed answers K=2-5 | - | - | No generator identified. |
| table | `tab:app_loo_by_dataset` | Dataset drill-down for LOO replay pooled over K=2-5 | - | - | No generator identified. |
| table | `tab:repeated_cross_model_calibration` | Cross-model calibration of repeated K=5 effects | `data/derived/gemma_repeated_benchmark_summary.json` | - | The JSON is shipped and manifest-listed but no table entry maps it here. Linkage UNPROVEN. |
| table | `tab:original_repeated_alignment` | Alignment between original W+ observations and controlled repeated replay | - | - | No generator identified. |
| table | `tab:compound_evaluator` | Cross-evaluator agreement on balanced triplets | - | - | No generator identified, and the underlying 16,724-submission cross-evaluator set was independently NOT LOCATED by two search passes. Not reproducible from anything known to exist locally. |
| table | `tab:app_protocol_matrix` | System-level final accuracy for four protocols x five benchmarks x two families | - | - | No generator identified. 40 protocol cells across four protocols x five benchmarks x two families. |
| table | `tab:app_protocol_cost` | Accuracy and inference effort on the 4181-problem Omni-MATH-2 OSS run | - | - | No generator identified. |
| table | `tab:cross_fitted_placebos` | Sensitivity of cross-fitted gain to replicate and shuffled controls | - | - | value_aware_one_removal_per_fold.csv is a plausible source, but the placebo and shuffle arms are not in expected_signal_tables.json and the table is not in the manifest's tables list. Linkage UNPROVEN. |

## How this was assigned

Statuses come from a clean-room audit of the arXiv ancillary artifact and the
authors' working tree, cross-checked against the paper source. Where a shipped
file's *numbers* were reconciled against the paper's printed values, the row
says so -- for example `tab:app_regret_sources` (246+91=337 problems,
2.541+1.365=3.906 -> 3.91) and `tab:app_routing_bootstrap` (4.627 / 4.25 /
5.004 -> 4.63 [4.25, 5.00]). Where the link is only plausible, the row says
UNPROVEN rather than assuming.

The `OFFLINE-DETERMINISTIC` rows are the ones CI runs on every push. Note the
coverage limit described in `README.md`: the analysis gate checks the
`In-pool LOO` rows and seven columns, not every row and column of the data it
ships.

## Note on MaScQA: 650 raw rows vs N = 649

`figures/benchmark_properties_source.csv` lists **650** rows for MaScQA, while the paper's
`tab:datasets` and every analysis in this repository use **649**. Both are correct and they are
different quantities. The paper states it directly: *"MaScQA contains 650 raw rows; one row is an
exact duplicate, so all analyses collapse it to 649 unique problems."* Use 649 as the analysis N.

