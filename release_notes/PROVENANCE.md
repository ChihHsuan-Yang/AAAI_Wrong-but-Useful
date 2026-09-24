# Where this repository came from

This file records the lineage of every file here, including the strings that
were deliberately changed. It is the one place in the repository where the
original private names appear: a substitution you cannot see is a substitution
you cannot check, so the portability audit allowlists exactly these lines, each
with a written justification, and nowhere else.

## Two sources

### 1. The arXiv ancillary reproducibility artifact (the spine)

```
arXiv:2608.14375  ancillary file  reproducibility_artifact.zip
sha256  432fa40096ff141b935831727c7342eb8a1948195334ced11c80a0f55095694a
70 files, one top-level directory, 69/69 entries verified against its own SHA256SUMS
```

Everything in `src/dhd/` (except `config.py` and `content_control.py`),
`analysis/` (except `analysis/replay/`), `figures/`, `configs/`, `data/`,
`scripts/reproduce_analysis.*`, `scripts/recompute_signal_tables.py`,
`scripts/validate_inputs.py`, `ARTIFACT_MANIFEST.json`, `requirements.lock`,
`THIRD_PARTY_NOTICES.md`, and the `tests/test_{labels,protocol,replay,
model_api,reproduce_analysis,signal_tables}.py` suite comes from that zip.

This artifact was chosen as the spine because it already reproduces from a
clean machine. Independent verification in an isolated temp directory, with
project environment variables unset and the tree relocated twice, recorded exit
0 for the pinned install, the full test suite, `reproduce_analysis.sh` with both
documented PASS lines, and `validate_inputs.py` across 25 data objects. The
gates were also shown able to *fail*: perturbing an In-pool LOO count, a
trajectory-value delta, a selector value, or any manifest-listed file each
produced exit 1.

### 2. Four analyses the artifact does not contain

The artifact is not a superset of the paper's final code. Three generators
behind reported results were absent from it. They are present here, under
`analysis/replay/` and `scripts/run_content_control.py`, ported from the
authors' working tree.

| Here | Upstream | Paper artifact it serves |
|---|---|---|
| `analysis/replay/offline_routing_analysis.py` | `scripts/critique_intervention/dhd_offline_routing_analysis.py` (untracked) | `tab:app_single_full_2x2` -- the only generator anywhere |
| `analysis/replay/content_control_analyze.py` | `scripts/critique_intervention/dhd_content_control_analyze.py` (untracked) | `tab:component_masking` (analysis half) |
| `analysis/replay/trace_example_report.py` | `scripts/critique_intervention/dhd_trace_example_report.py` (untracked) | shortlists behind `fig:main_trace_examples` |
| `src/dhd/content_control.py` + `scripts/run_content_control.py` | the uncommitted diff to `scripts/critique_intervention/dhd_replay_stability.py` | `tab:component_masking` (generation half) |

Upstream branch `AAAI-WBU` at commit `99d13cf7e65200fe689135105bb15f465b58fca5`
(2026-07-22). The four upstream files were uncommitted working-tree state dated
2026-07-23; they were read from a verified byte-identical read-only snapshot and
the working tree was never modified. Per-file detail, including what was changed
and why, is in `release_notes/PORTABILITY_CHANGES.md` and in the release
provenance CSV kept with the release records.

## Strings that were changed

| Was | Is | Why |
|---|---|---|
| top directory `anonymous_reproducibility/` | repository root | Double-blind review name; the paper is published. |
| `Copyright (c) 2026 Anonymous Authors` (LICENSE) | the ten named authors | The license must name its holders. Still MIT; no relicensing. |
| `"artifact": "anonymous_reproducibility"` (manifest) | `"artifact": "AAAI_Wrong-but-Useful"` | Same reason. |
| `description = "Anonymous reproducibility artifact ..."` | the paper's title | Same reason. |
| `tests/test_artifact_anonymity.py` (an anonymity self-scan) | `tools/portability_audit.py` | Anonymity is no longer the property to enforce; portability and privacy are. The replacement checks five classes, not one, and each of its patterns carries a positive control. |

## What was deliberately excluded

Nothing from the upstream `jobs/` layer is here. Those scripts carry absolute
cluster paths (including a third party's account name), a live institutional
inference endpoint, and -- worst for a reader -- `export HTTP_PROXY="${HTTP_PROXY:-...}"`
pointing at a private proxy, which would silently route a reader's traffic
through a network they have no relationship with. `use_alcf.sh`,
`inference_auth_token.py`, and the cluster README are excluded for the same
reasons. None of it is scientifically load-bearing: the arXiv artifact never
contained any of it and reproduces without it.

The upstream replay runner itself is also not here. It reached the model through
the authors' internal `agentverse` framework, which a reader cannot install; see
`release_notes/PORTABILITY_CHANGES.md` for what was rebuilt in its place and
what that does and does not preserve.
