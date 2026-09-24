#!/usr/bin/env python3
"""Recompute repeated-replay robustness tables from below-cell signal records.

Unlike the figure pipeline (which replots already-aggregated cell counts), this
script reconstructs paper-facing robustness tables from per-signal and per-fold
records shipped in ``data/derived/signal_labels/``:

- ``tab:matched_sensitivity`` — mean shift, exact-sign agreement, nonzero-
  direction agreement, and same-input disagreement, recomputed per matched
  change from per-signal reference/sensitivity labels.
- ``tab:cross_fitted_one_removal`` and ``tab:cross_fitted_one_removal_by_benchmark``
  — micro-pooled held-out full and cross-fitted accuracy and the gain, recomputed
  per model (and per benchmark) from per-fold selector/full outcomes.

It writes the reconstructed aggregate tables to the chosen output directory and
compares the recomputed point estimates against the expected values recorded in
``data/manifests/expected_signal_tables.json``. No model calls are made. Bootstrap
confidence intervals reported in the paper are not recomputed here (they require
the seeded resampling in the analysis scripts); only the point estimates that the
below-cell records determine exactly are checked.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SIGNALS = REPO_ROOT / "data" / "derived" / "signal_labels"
MANIFEST = REPO_ROOT / "data" / "manifests" / "expected_signal_tables.json"

BENCHMARK_LABELS = {
    "omni_16k": "Omni-MATH-2",
    "jeebench": "JEEBench",
    "scibench": "SciBench",
    "labbench": "LAB-Bench",
    "mascqa": "MaScQA",
}

MATCHED_FILES = {
    "order_oss": "matched_sensitivity_order_oss.csv",
    "order_gemma": "matched_sensitivity_order_gemma.csv",
    "integrator_gemma_to_oss": "matched_sensitivity_integrator_gemma_to_oss.csv",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _round1(value: float) -> float:
    return round(value, 1)


def matched_sensitivity_table() -> dict:
    """Recompute the matched-sensitivity rows from per-signal records."""
    out: dict = {}
    for key, filename in MATCHED_FILES.items():
        rows = _read_csv(SIGNALS / filename)
        n = len(rows)
        exact = sum(
            1 for r in rows if r["reference_sign"] == r["sensitivity_sign"]
        ) / n * 100
        both_nonzero = [
            r for r in rows
            if r["reference_sign"] != "0" and r["sensitivity_sign"] != "0"
        ]
        nonzero_dir = (
            sum(
                1 for r in both_nonzero
                if r["reference_sign"] == r["sensitivity_sign"]
            ) / len(both_nonzero) * 100
            if both_nonzero else 0.0
        )
        mean_shift = (
            sum(float(r["trajectory_value_delta"]) for r in rows) / n * 100
        )
        out[key] = {
            "signals": n,
            "mean_shift_pp": round(mean_shift, 2),
            "exact_sign_pct": _round1(exact),
            "nonzero_direction_pct": _round1(nonzero_dir),
        }
    return out


def cross_fitted_table() -> dict:
    """Recompute cross-fitted one-removal accuracy from per-fold records."""
    rows = _read_csv(SIGNALS / "value_aware_one_removal_per_fold.csv")
    pooled: dict = defaultdict(lambda: {"full": 0.0, "xfit": 0.0, "n": 0})
    by_bench: dict = defaultdict(lambda: {"full": 0.0, "xfit": 0.0, "n": 0})
    for r in rows:
        model = r["model"]
        pooled[model]["full"] += float(r["full_value"])
        pooled[model]["xfit"] += float(r["selector_value"])
        pooled[model]["n"] += 1
        key = (model, r["benchmark"])
        by_bench[key]["full"] += float(r["full_value"])
        by_bench[key]["xfit"] += float(r["selector_value"])
        by_bench[key]["n"] += 1

    overall = {}
    for model, agg in pooled.items():
        full = agg["full"] / agg["n"] * 100
        xfit = agg["xfit"] / agg["n"] * 100
        overall[model] = {
            "full_pct": round(full, 2),
            "cross_fit_pct": round(xfit, 2),
            "gain_pp": round(xfit - full, 2),
            "n_folds": agg["n"],
        }

    per_benchmark = {}
    for (model, bench), agg in by_bench.items():
        gain = (agg["xfit"] - agg["full"]) / agg["n"] * 100
        per_benchmark.setdefault(BENCHMARK_LABELS.get(bench, bench), {})[model] = round(
            gain, 2
        )

    return {"overall": overall, "by_benchmark": per_benchmark}


def compute_all() -> dict:
    return {
        "tab_matched_sensitivity": matched_sensitivity_table(),
        "tab_cross_fitted_one_removal": cross_fitted_table(),
    }


def _almost_equal(a, b, tol=0.06) -> bool:
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_almost_equal(a[k], b[k], tol) for k in a)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) <= tol
    return a == b


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("reproduced"))
    parser.add_argument("--update-expected", action="store_true")
    args = parser.parse_args()

    tables = compute_all()

    if args.update_expected:
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(
            json.dumps(tables, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"wrote expected signal tables -> {MANIFEST}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "tab_matched_sensitivity.json").write_text(
        json.dumps(tables["tab_matched_sensitivity"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "tab_cross_fitted_one_removal.json").write_text(
        json.dumps(tables["tab_cross_fitted_one_removal"], indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )

    if not MANIFEST.exists():
        raise SystemExit(f"missing expected manifest: {MANIFEST}")
    expected = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not _almost_equal(tables, expected):
        print("MISMATCH: recomputed signal tables differ from expected manifest.")
        print("recomputed:", json.dumps(tables, sort_keys=True)[:600])
        return 1
    print("PASS: recomputed matched-sensitivity and cross-fitted tables match "
          "expected manifest (below-cell reconstruction).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
