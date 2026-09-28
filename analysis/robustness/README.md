# Robustness summaries

## `summarize_signal_direction.py`

Reads a `SIGNAL_DIRECTION_ROBUSTNESS.json` record and prints, per benchmark and proposal class:
changing vs eligible observation counts, the helpful share, the **problem-clustered bootstrap 95%
confidence interval**, the number of unique problem–hypothesis pairs, and the number of problems
exhibiting both help and harm. It then pools across benchmarks.

These are the dependence-aware statistics behind the paper's headline shares. The three nested units
matter and the script keeps them distinct:

```
observation  ->  unique problem-hypothesis pair  ->  problem
```

The confidence interval resamples **problems**, not observations, because five messages from one
problem share a full-pool outcome.

### Usage

```bash
python3 summarize_signal_direction.py <path-to-SIGNAL_DIRECTION_ROBUSTNESS.json> <label>
```

### Reproducing the paper's pooled numbers

The input records are part of the run archives and are not redistributed in this repository (they
sit under the authors' ALCF result trees). Running the script against them yields:

| arm | changing | eligible | helpful | share | published pooled 95% CI |
|---|---:|---:|---:|---:|---|
| OSS, wrong proposal | 3,874 | 25,837 | 1,623 | 41.89% | [39.5, 44.3] |
| Gemma, wrong proposal | 3,531 | 49,425 | 1,601 | 45.34% | [42.6, 48.1] |

which reproduce the shares reported in the paper.

### A caveat the script cannot fix for you

The two model families were summarised by **different analysis versions**:

- OSS: `dhd_signal_direction_v1`, proposal classes `{correct, wrong}`
- Gemma: `dhd_signal_direction_v2_tristate_proposals`, classes `{correct, wrong, null}`

Only the two shared classes are comparable. Presenting all classes side by side as if the schemas
matched would misstate the comparison.
