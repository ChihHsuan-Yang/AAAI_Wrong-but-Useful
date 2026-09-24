#!/usr/bin/env python3
"""Reproduce every paper-facing table and figure from included sanitized inputs.

This performs the **analysis reproduction** guarantee: using only the sanitized
derived records shipped in this artifact and no model calls, it

1. regenerates all paper figures from their source CSVs into a fresh output
   directory, and
2. recomputes the paper's headline correctness/trajectory-value count tables and
   compares them against the expected numeric summaries in
   ``data/manifests/expected_summaries.json``.

Exit code is non-zero on any mismatch or missing figure output.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIGURES_DIR = REPO_ROOT / "figures"
MANIFEST = REPO_ROOT / "data" / "manifests" / "expected_summaries.json"

# figure script -> (source csv, output basename, extra args)
FIGURE_JOBS = [
    ("make_correctness_flip_direction.py",
     "fig_correctness_flip_direction_source.csv",
     "fig_correctness_flip_direction", []),
    ("make_cross_benchmark_trajectory_value.py",
     "fig_cross_benchmark_trajectory_value_source.csv",
     "fig_cross_benchmark_trajectory_value", []),
    ("make_generation_integration_gap.py",
     "fig_generation_integration_gap_source.csv",
     "fig_generation_integration_gap", []),
    ("make_generation_integration_gap.py",
     "fig_generation_integration_gap_gemma_source.csv",
     "fig_generation_integration_gap_gemma", ["--panel-title", "Gemma"]),
    ("make_loo_by_k_appendix.py",
     "fig_loo_by_k_appendix_source.csv",
     "fig_loo_by_k_appendix", []),
    ("make_evaluator_agreement.py",
     "evaluator_agreement_source.csv",
     "fig_evaluator_agreement", []),
]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def compute_headline_summary() -> dict:
    """Recompute the taxonomy counts and shares from the figure source CSVs."""
    flip = _read_csv(FIGURES_DIR / "fig_correctness_flip_direction_source.csv")
    summary: dict = {"loo_taxonomy": {}, "helpful_share_among_flips_pct": {}}
    for row in flip:
        if row["metric"] != "In-pool LOO":
            continue
        key = f"{row['model']}|{row['proposal_correctness']}"
        helpful = int(row["helpful_count"])
        harmful = int(row["harmful_count"])
        neutral = int(row["neutral_count"])
        summary["loo_taxonomy"][key] = {
            "helpful": helpful,
            "neutral": neutral,
            "harmful": harmful,
            "eligible": int(row["eligible_count"]),
        }
        summary["helpful_share_among_flips_pct"][key] = round(
            100.0 * helpful / (helpful + harmful), 4
        )

    cross = _read_csv(FIGURES_DIR / "fig_cross_benchmark_trajectory_value_source.csv")
    # Pooled OSS/Gemma LOO totals summed across benchmarks (sanity cross-check).
    pooled: dict = {}
    for row in cross:
        key = f"{row['model']}|{row['proposal_correctness']}"
        bucket = pooled.setdefault(key, {"helpful": 0, "neutral": 0, "harmful": 0})
        bucket["helpful"] += int(row["helpful_count"])
        bucket["neutral"] += int(row["neutral_count"])
        bucket["harmful"] += int(row["harmful_count"])
    summary["cross_benchmark_pooled"] = pooled
    return summary


def regenerate_figures(output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    produced: list[str] = []
    for script, source, out_base, extra in FIGURE_JOBS:
        cmd = [
            sys.executable,
            str(FIGURES_DIR / script),
            "--source", str(FIGURES_DIR / source),
            "--output-base", str(output_dir / out_base),
            *extra,
        ]
        subprocess.run(cmd, check=True, cwd=str(REPO_ROOT))
        for suffix in (".pdf", ".png"):
            path = output_dir / f"{out_base}{suffix}"
            if not path.exists():
                raise SystemExit(f"figure not produced: {path}")
            produced.append(path.name)
    return produced


def _almost_equal(a, b, tol=1e-6) -> bool:
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_almost_equal(a[k], b[k], tol) for k in a)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) <= tol
    return a == b


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("reproduced"))
    parser.add_argument(
        "--update-expected",
        action="store_true",
        help="Write the computed summary to the manifest instead of comparing.",
    )
    args = parser.parse_args()

    summary = compute_headline_summary()

    if args.update_expected:
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"wrote expected summary -> {MANIFEST}")

    figures = regenerate_figures(args.output_dir)
    print(f"regenerated {len(figures)} figure outputs into {args.output_dir}")

    if not MANIFEST.exists():
        raise SystemExit(f"missing expected summary manifest: {MANIFEST}")
    expected = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not _almost_equal(summary, expected):
        print("MISMATCH between recomputed summary and expected manifest.")
        print("recomputed:", json.dumps(summary, sort_keys=True)[:400])
        return 1

    print("PASS: recomputed headline summary matches expected manifest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
