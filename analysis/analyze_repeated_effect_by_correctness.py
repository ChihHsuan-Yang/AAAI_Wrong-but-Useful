#!/usr/bin/env python3
"""Aggregate repeated replay effects by proposal correctness.

The hierarchical bootstrap resamples problems within each benchmark and then
resamples matched replay blocks within each selected problem. All five signals
from a problem use the same sampled block indices, preserving their shared full
integration outcome. The pooled estimate also preserves benchmark sizes instead
of treating signals or benchmarks as independent observations.
"""

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


BENCHMARK_LABELS = {
    "omni_16k": "Omni-MATH-2",
    "jeebench": "JEEBench",
    "scibench": "SciBench",
    "labbench": "LAB-Bench",
    "mascqa": "MaScQA",
}


def load_rows(root):
    rows = []
    for directory, label in BENCHMARK_LABELS.items():
        path = root / directory / "effect_estimates.csv"
        if not path.exists():
            path = root / directory / "analysis" / "effect_estimates.csv"
        if not path.exists():
            raise FileNotFoundError(path)
        with path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                correctness = int(row["proposal_correctness"])
                if correctness not in (0, 1):
                    continue
                rows.append(
                    {
                        "benchmark": label,
                        "problem_id": row["problem_id"],
                        "hypothesis_index": int(row["hypothesis_index"]),
                        "proposal_correctness": correctness,
                        "trajectory_value": float(row["trajectory_value"]),
                        "stability_label": row["stability_label"],
                        "block_deltas": [
                            float(value)
                            for value in json.loads(row["block_deltas_json"])
                        ],
                    }
                )
    return rows


def summarize(rows):
    by_correctness = defaultdict(list)
    stable = defaultdict(Counter)
    for row in rows:
        correctness = row["proposal_correctness"]
        by_correctness[correctness].append(row["trajectory_value"])
        stable[correctness][row["stability_label"]] += 1

    wrong_mean = float(np.mean(by_correctness[0]))
    correct_mean = float(np.mean(by_correctness[1]))
    return {
        "wrong": wrong_mean,
        "correct": correct_mean,
        "correct_minus_wrong": correct_mean - wrong_mean,
        "n_wrong": len(by_correctness[0]),
        "n_correct": len(by_correctness[1]),
        "stable_wrong": dict(stable[0]),
        "stable_correct": dict(stable[1]),
    }


def prepare_benchmark(rows):
    by_problem = defaultdict(list)
    for row in rows:
        by_problem[row["problem_id"]].append(row)
    correctness = []
    block_deltas = []
    signal_counts = set()
    for problem_id in sorted(by_problem):
        problem_rows = sorted(
            by_problem[problem_id],
            key=lambda row: row["hypothesis_index"],
        )
        signal_counts.add(len(problem_rows))
        correctness.append(
            [row["proposal_correctness"] for row in problem_rows]
        )
        problem_block_counts = {
            len(row["block_deltas"]) for row in problem_rows
        }
        if len(problem_block_counts) != 1:
            raise ValueError(
                f"Inconsistent replay-block counts for problem {problem_id}: "
                f"{sorted(problem_block_counts)}"
            )
        block_deltas.append([row["block_deltas"] for row in problem_rows])
    if len(signal_counts) != 1:
        raise ValueError(
            f"Inconsistent signal counts across problems: {sorted(signal_counts)}"
        )
    all_block_counts = {
        len(deltas)
        for problem_deltas in block_deltas
        for deltas in problem_deltas
    }
    if len(all_block_counts) != 1:
        raise ValueError(
            f"Inconsistent replay-block counts: {sorted(all_block_counts)}"
        )
    return {
        "correctness": np.asarray(correctness, dtype=np.int8),
        "block_deltas": np.asarray(block_deltas, dtype=np.float64),
        "n_blocks": all_block_counts.pop(),
    }


def bootstrap(rows, iterations, seed):
    by_benchmark = defaultdict(list)
    for row in rows:
        by_benchmark[row["benchmark"]].append(row)
    benchmark_arrays = [
        prepare_benchmark(benchmark_rows)
        for benchmark_rows in by_benchmark.values()
    ]

    rng = np.random.default_rng(seed)
    samples = defaultdict(list)
    for _ in range(iterations):
        sums = {0: 0.0, 1: 0.0}
        counts = {0: 0, 1: 0}
        for arrays in benchmark_arrays:
            n_problems = arrays["correctness"].shape[0]
            sampled_problems = rng.integers(
                0, n_problems, size=n_problems
            )
            sampled_deltas = arrays["block_deltas"][sampled_problems]
            sampled_blocks = rng.integers(
                0,
                arrays["n_blocks"],
                size=(n_problems, arrays["n_blocks"]),
            )
            replay_deltas = np.take_along_axis(
                sampled_deltas,
                sampled_blocks[:, None, :],
                axis=2,
            ).mean(axis=2)
            sampled_correctness = arrays["correctness"][sampled_problems]
            for correctness in (0, 1):
                mask = sampled_correctness == correctness
                sums[correctness] += float(replay_deltas[mask].sum())
                counts[correctness] += int(mask.sum())
        wrong_mean = sums[0] / counts[0]
        correct_mean = sums[1] / counts[1]
        samples["wrong"].append(wrong_mean)
        samples["correct"].append(correct_mean)
        samples["correct_minus_wrong"].append(correct_mean - wrong_mean)

    return {
        key: [
            float(np.quantile(values, 0.025)),
            float(np.quantile(values, 0.975)),
        ]
        for key, values in samples.items()
    }


def estimate(rows, iterations, seed):
    summary = summarize(rows)
    intervals = bootstrap(rows, iterations, seed)
    return {
        "n_problems": len({(row["benchmark"], row["problem_id"]) for row in rows}),
        "n_signals": len(rows),
        **summary,
        "ci95": intervals,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "root",
        type=Path,
        help="Directory containing benchmark/effect_estimates.csv files",
    )
    parser.add_argument("--iterations", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260724)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rows = load_rows(args.root)
    by_benchmark = defaultdict(list)
    for row in rows:
        by_benchmark[row["benchmark"]].append(row)

    payload = {
        "design": {
            "estimand": (
                "mean repeated trajectory-value estimate, stratified by "
                "proposal correctness"
            ),
            "bootstrap_unit": (
                "problem within benchmark, then matched replay block within "
                "problem; all five signals share sampled block indices"
            ),
            "iterations": args.iterations,
            "seed": args.seed,
        },
        "pooled": estimate(rows, args.iterations, args.seed),
        "benchmarks": {
            benchmark: estimate(
                benchmark_rows,
                args.iterations,
                args.seed + index + 1,
            )
            for index, (benchmark, benchmark_rows) in enumerate(
                sorted(by_benchmark.items())
            )
        },
    }
    output = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(output)
    print(output, end="")


if __name__ == "__main__":
    main()
