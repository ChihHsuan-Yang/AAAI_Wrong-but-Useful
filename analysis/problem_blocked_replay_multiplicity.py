#!/usr/bin/env python3
"""Problem-blocked randomization tests for repeated DHD replay effects.

Each problem contributes two identical-input full-pool outcomes and five
leave-one-out outcomes in every replay block. The five message effects therefore
share the same full-pool outcomes and are not independent. This analysis first
tests a problem-level maximum statistic under within-block slot exchangeability,
then applies BH or BY correction across problems.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np


BENCHMARKS = ("omni_16k", "jeebench", "scibench", "labbench", "mascqa")
FAMILIES = ("wrong_helpful", "correct_harmful", "off_diagonal", "any_effect")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Malformed JSON at {path}:{line_number}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"Non-object JSON at {path}:{line_number}")
            rows.append(row)
    return rows


def adjust_pvalues(pvalues: list[float], method: str) -> list[float]:
    if method not in {"BH", "BY"}:
        raise ValueError(method)
    count = len(pvalues)
    if not count:
        return []
    order = np.argsort(np.asarray(pvalues, dtype=np.float64))
    ordered = np.asarray(pvalues, dtype=np.float64)[order]
    factor = float(sum(1.0 / index for index in range(1, count + 1))) if method == "BY" else 1.0
    adjusted_ordered = np.empty(count, dtype=np.float64)
    running = 1.0
    for reverse_index in range(count - 1, -1, -1):
        rank = reverse_index + 1
        candidate = ordered[reverse_index] * count * factor / rank
        running = min(running, candidate)
        adjusted_ordered[reverse_index] = min(1.0, running)
    adjusted = np.empty(count, dtype=np.float64)
    adjusted[order] = adjusted_ordered
    return adjusted.tolist()


def canonical_null_histograms(
    success_counts: tuple[int, ...],
    wrong_count: int,
    *,
    permutations: int,
    seed: int,
    batch_size: int,
) -> dict[str, np.ndarray]:
    """Sample null maximum-statistic histograms for one problem pattern.

    Statistics are stored on the integer scale
    ``2 * n_blocks * trajectory_value``.
    """

    if all(count in (0, 7) for count in success_counts):
        histograms = {}
        for family in FAMILIES:
            histogram = np.zeros(21, dtype=np.int64)
            histogram[10] = permutations
            histograms[family] = histogram
        return histograms

    rng = np.random.default_rng(seed)
    histograms = {
        family: np.zeros(21, dtype=np.int64)
        for family in FAMILIES
    }
    completed = 0
    while completed < permutations:
        current = min(batch_size, permutations - completed)
        delta_sums = np.zeros((current, 5), dtype=np.int16)
        for successes in success_counts:
            if successes == 0:
                outcomes = np.zeros((current, 7), dtype=np.int8)
            elif successes == 7:
                outcomes = np.ones((current, 7), dtype=np.int8)
            else:
                random_values = rng.random((current, 7))
                selected = np.argpartition(
                    random_values,
                    kth=successes - 1,
                    axis=1,
                )[:, :successes]
                outcomes = np.zeros((current, 7), dtype=np.int8)
                np.put_along_axis(outcomes, selected, 1, axis=1)
            full_sum = outcomes[:, 0] + outcomes[:, 1]
            delta_sums += full_sum[:, None] - 2 * outcomes[:, 2:]

        any_effect = np.abs(delta_sums).max(axis=1)
        if wrong_count:
            wrong_helpful = delta_sums[:, :wrong_count].max(axis=1)
        else:
            wrong_helpful = np.full(current, -10, dtype=np.int16)
        if wrong_count < 5:
            correct_harmful = (-delta_sums[:, wrong_count:]).max(axis=1)
        else:
            correct_harmful = np.full(current, -10, dtype=np.int16)
        off_diagonal = np.maximum(wrong_helpful, correct_harmful)

        values_by_family = {
            "wrong_helpful": wrong_helpful,
            "correct_harmful": correct_harmful,
            "off_diagonal": off_diagonal,
            "any_effect": any_effect,
        }
        for family, values in values_by_family.items():
            histograms[family] += np.bincount(values + 10, minlength=21)
        completed += current
    return histograms


def collect_problems(model_root: Path, model: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    problems = []
    provenance = {"files": {}, "incomplete_problems": []}
    for benchmark in BENCHMARKS:
        path = model_root / f"{benchmark}.replay_events.jsonl"
        if not path.exists():
            raise FileNotFoundError(path)
        provenance["files"][benchmark] = {
            "path": str(path),
            "sha256": file_sha256(path),
        }
        by_problem: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in load_jsonl(path):
            if row.get("valid") is not True or row.get("correct") not in (0, 1):
                raise ValueError(f"Invalid scientific row in {path}")
            by_problem[str(row["problem_id"])].append(row)

        for problem_id, rows in sorted(by_problem.items()):
            full: dict[int, list[int]] = defaultdict(list)
            removals: dict[int, dict[int, int]] = defaultdict(dict)
            correctness: dict[int, int] = {}
            for row in rows:
                replicate = int(row["replicate_id"])
                if row["condition"] == "full":
                    full[replicate].append(int(row["correct"]))
                elif row["condition"] == "removal":
                    index = int(row["removed_h_index"])
                    removals[replicate][index] = int(row["correct"])
                    label = int(row["proposal_correctness"])
                    if index in correctness and correctness[index] != label:
                        raise ValueError(
                            f"Inconsistent proposal label for {problem_id}, h{index}"
                        )
                    correctness[index] = label

            replicates = sorted(set(full) & set(removals))
            complete = (
                len(replicates) == 5
                and len(correctness) == 5
                and all(
                    len(full[replicate]) == 2
                    and len(removals[replicate]) == 5
                    for replicate in replicates
                )
            )
            if not complete:
                provenance["incomplete_problems"].append(
                    {
                        "model": model,
                        "benchmark": benchmark,
                        "problem_id": problem_id,
                        "replicates": len(replicates),
                        "full_counts": {
                            str(key): len(value) for key, value in sorted(full.items())
                        },
                        "removal_counts": {
                            str(key): len(value)
                            for key, value in sorted(removals.items())
                        },
                    }
                )
                continue

            wrong_indices = sorted(index for index, label in correctness.items() if label == 0)
            correct_indices = sorted(index for index, label in correctness.items() if label == 1)
            ordered_indices = wrong_indices + correct_indices
            delta_sums = np.zeros(5, dtype=np.int16)
            success_counts = []
            for replicate in replicates:
                full_sum = sum(full[replicate])
                success_counts.append(full_sum + sum(removals[replicate].values()))
                for canonical_index, source_index in enumerate(ordered_indices):
                    delta_sums[canonical_index] += (
                        full_sum - 2 * removals[replicate][source_index]
                    )

            wrong_count = len(wrong_indices)
            wrong_helpful = (
                int(delta_sums[:wrong_count].max()) if wrong_count else None
            )
            correct_harmful = (
                int((-delta_sums[wrong_count:]).max())
                if wrong_count < 5
                else None
            )
            off_diagonal_candidates = [
                value
                for value in (wrong_helpful, correct_harmful)
                if value is not None
            ]
            problems.append(
                {
                    "model": model,
                    "benchmark": benchmark,
                    "problem_id": problem_id,
                    "success_counts": tuple(sorted(success_counts)),
                    "wrong_count": wrong_count,
                    "statistics": {
                        "wrong_helpful": wrong_helpful,
                        "correct_harmful": correct_harmful,
                        "off_diagonal": max(off_diagonal_candidates),
                        "any_effect": int(np.abs(delta_sums).max()),
                    },
                    "trajectory_values": [
                        float(value / (2 * len(replicates)))
                        for value in delta_sums
                    ],
                    "canonical_source_indices": ordered_indices,
                }
            )
    return problems, provenance


def empirical_pvalue(histogram: np.ndarray, observed: int, permutations: int) -> float:
    start = max(0, observed + 10)
    count_greater_equal = int(histogram[start:].sum())
    return (1.0 + count_greater_equal) / (1.0 + permutations)


def add_adjustments(rows: list[dict[str, Any]], *, q: float) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for scope_name, scope_rows in (
        ("global", rows),
        *(
            (model, [row for row in rows if row["model"] == model])
            for model in sorted({row["model"] for row in rows})
        ),
    ):
        summary[scope_name] = {}
        for family in FAMILIES:
            eligible = [
                row
                for row in scope_rows
                if row["statistics"][family] is not None
            ]
            pvalues = [float(row["pvalues"][family]) for row in eligible]
            bh = adjust_pvalues(pvalues, "BH")
            by = adjust_pvalues(pvalues, "BY")
            for row, bh_value, by_value in zip(eligible, bh, by):
                row.setdefault("adjusted", {}).setdefault(scope_name, {})[family] = {
                    "BH": bh_value,
                    "BY": by_value,
                }
            summary[scope_name][family] = {
                "eligible_problems": len(eligible),
                "raw_p_le_0_05": sum(value <= 0.05 for value in pvalues),
                "BH_discoveries_q_0_05": sum(value <= q for value in bh),
                "BY_discoveries_q_0_05": sum(value <= q for value in by),
                "minimum_raw_p": min(pvalues) if pvalues else None,
            }
    return summary


def selected_discoveries(
    rows: list[dict[str, Any]],
    *,
    q: float,
) -> dict[str, Any]:
    selected: dict[str, Any] = {}
    for scope in ("global", "oss", "gemma"):
        selected[scope] = {}
        for family in FAMILIES:
            family_rows = []
            for row in rows:
                adjusted = (
                    row.get("adjusted", {})
                    .get(scope, {})
                    .get(family)
                )
                if adjusted is None or adjusted["BH"] > q:
                    continue
                family_rows.append(
                    {
                        "model": row["model"],
                        "benchmark": row["benchmark"],
                        "problem_id": row["problem_id"],
                        "statistic_integer": row["statistics"][family],
                        "trajectory_value_scale": "divide statistic by 10",
                        "raw_p": row["pvalues"][family],
                        "BH_adjusted_p": adjusted["BH"],
                        "BY_adjusted_p": adjusted["BY"],
                    }
                )
            selected[scope][family] = family_rows
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--staged-root",
        type=Path,
        required=True,
        help="Directory with oss/ and gemma/ benchmark replay JSONL files",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--detail-output",
        type=Path,
        help="Optional private output containing every problem-level record",
    )
    parser.add_argument("--permutations", type=int, default=100_000)
    parser.add_argument("--batch-size", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260726)
    parser.add_argument("--q", type=float, default=0.05)
    args = parser.parse_args()
    if args.permutations < 1_000:
        raise ValueError("--permutations must be at least 1000")

    all_problems = []
    provenance = {}
    for model in ("oss", "gemma"):
        model_problems, model_provenance = collect_problems(
            args.staged_root / model,
            model,
        )
        all_problems.extend(model_problems)
        provenance[model] = model_provenance

    patterns = sorted(
        {
            (row["success_counts"], row["wrong_count"])
            for row in all_problems
        }
    )
    nulls = {}
    for index, (success_counts, wrong_count) in enumerate(patterns):
        pattern_seed = int(
            hashlib.sha256(
                f"{args.seed}|{success_counts}|{wrong_count}".encode()
            ).hexdigest()[:16],
            16,
        )
        nulls[(success_counts, wrong_count)] = canonical_null_histograms(
            success_counts,
            wrong_count,
            permutations=args.permutations,
            seed=pattern_seed,
            batch_size=args.batch_size,
        )

    for row in all_problems:
        histograms = nulls[(row["success_counts"], row["wrong_count"])]
        row["pvalues"] = {
            family: (
                empirical_pvalue(
                    histograms[family],
                    row["statistics"][family],
                    args.permutations,
                )
                if row["statistics"][family] is not None
                else None
            )
            for family in FAMILIES
        }
        row["success_counts"] = list(row["success_counts"])

    summary = add_adjustments(all_problems, q=args.q)
    compact_provenance = {
        model: {
            "source_sha256": {
                benchmark: details["sha256"]
                for benchmark, details in provenance[model]["files"].items()
            },
            "incomplete_problems": provenance[model]["incomplete_problems"],
        }
        for model in ("oss", "gemma")
    }
    payload = {
        "analysis": "problem_blocked_repeated_replay_multiplicity",
        "design": {
            "unit": "problem",
            "within_problem_statistic": (
                "maximum directional or absolute repeated full-minus-removal "
                "effect across the five messages"
            ),
            "randomization": (
                "within each matched replay block, the two full and five "
                "removal outcomes are exchangeable under the global no-effect null"
            ),
            "multiplicity": (
                "the maximum statistic handles five dependent messages within "
                "a problem; BH and BY are then applied across problem-level tests"
            ),
            "permutations": args.permutations,
            "seed": args.seed,
            "q": args.q,
            "trajectory_value_scale": (
                "stored integer statistic divided by 2 * 5 replay blocks"
            ),
        },
        "coverage": {
            model: {
                "complete_problems": sum(
                    row["model"] == model for row in all_problems
                ),
                "incomplete_problems": len(
                    provenance[model]["incomplete_problems"]
                ),
            }
            for model in ("oss", "gemma")
        },
        "summary": summary,
        "selected_discoveries": selected_discoveries(
            all_problems,
            q=args.q,
        ),
        "provenance": compact_provenance,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if args.detail_output:
        args.detail_output.parent.mkdir(parents=True, exist_ok=True)
        args.detail_output.write_text(
            json.dumps(
                {
                    **payload,
                    "source_paths": provenance,
                    "problems": all_problems,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
    print(json.dumps({"coverage": payload["coverage"], "summary": summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
