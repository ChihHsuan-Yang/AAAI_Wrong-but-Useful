#!/usr/bin/env python3
"""Analyze matched DHD content-preserving intervention controls.

Each problem targets one hypothesis slot and repeats five conditions: the
original pool, removal, a length-matched semantic mask, answer masking, and
reasoning masking. Effects are defined as original-full correctness minus the
corresponding intervention correctness within the same replicate block, so
every comparison is matched inside one replicate.

RUNS ON LOCAL INPUTS. It reads a run directory produced by
``scripts/run_content_control.py`` (``replay_events.jsonl``, ``RUN_META.json``,
``validation.json``) and makes no model call, so a run you produced yourself can
be re-analyzed offline:

    python scripts/run_content_control.py --source POOLS --control-manifest M --out-dir RUN
    python analysis/replay/content_control_analyze.py --run_dir RUN

NAMING CAVEAT, UNRESOLVED. The paper's component-masking table describes six
conditions per target -- these five plus a byte-identical repeat and a
same-position approximate-length neutral replacement -- and 22 x 5 x 8 = 880
outcomes. This code defines five and its analyzer consumes four effects
(22 x 5 x 5 = 550). ``semantic_mask`` plausibly *is* the neutral replacement and
``original_full`` run twice plausibly *is* the repeat, but no manifest states
that mapping, so it is UNPROVEN. Do not claim this reproduces the paper's table
until the naming map is confirmed against a run directory that recorded it; see
docs/PAPER_REPRODUCTION_MAP.md.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "dhd_content_control_analysis_v1"
CONDITIONS = (
    "removal",
    "semantic_mask",
    "answer_masked",
    "reasoning_masked",
)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(path) as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"Expected object at {path}:{line_number}")
            rows.append(value)
    return rows


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    index = (len(ordered) - 1) * quantile
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _seed_for(seed: int, *parts: Any) -> int:
    raw = "|".join([str(seed), *(str(part) for part in parts)])
    return int(hashlib.sha256(raw.encode()).hexdigest()[:16], 16)


def _cluster_bootstrap(
    problem_values: dict[str, float], *, iterations: int, seed: int
) -> tuple[float, float]:
    problem_ids = sorted(problem_values)
    if not problem_ids:
        return float("nan"), float("nan")
    values = [problem_values[problem_id] for problem_id in problem_ids]
    if len(set(values)) == 1:
        return values[0], values[0]
    rng = random.Random(seed)
    draws = [
        _mean([values[rng.randrange(len(values))] for _ in values])
        for _ in range(iterations)
    ]
    return _percentile(draws, 0.025), _percentile(draws, 0.975)


def analyze(
    run_dir: Path,
    *,
    output_dir: Path,
    iterations: int,
    seed: int,
    allow_incomplete: bool,
) -> dict[str, Any]:
    meta = _load_json(run_dir / "RUN_META.json")
    validation = _load_json(run_dir / "validation.json")
    if not validation.get("complete") and not allow_incomplete:
        raise ValueError("Run validation is incomplete; pass --allow_incomplete to inspect")
    if not meta.get("control_manifest"):
        raise ValueError("RUN_META.json does not describe a content-control run")

    rows = _load_jsonl(run_dir / "replay_events.jsonl")
    if any(row.get("valid") is not True for row in rows):
        raise ValueError("Scientific event file contains invalid rows")
    keys = [
        (
            row.get("problem_id"),
            row.get("target_h_index"),
            row.get("condition"),
            row.get("replicate_id"),
        )
        for row in rows
    ]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate content-control event keys")

    by_block: dict[tuple[str, int, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        key = (
            str(row["problem_id"]),
            int(row["target_h_index"]),
            int(row["replicate_id"]),
        )
        by_block[key][str(row["condition"])] = row

    expected = {"original_full", *CONDITIONS}
    for key, block in by_block.items():
        if set(block) != expected:
            raise ValueError(f"Incomplete condition block {key}: {sorted(block)}")

    paired_rows: list[dict[str, Any]] = []
    per_problem_condition: dict[tuple[str, int, str], list[float]] = defaultdict(list)
    proposal_labels: dict[tuple[str, int], int] = {}
    for (problem_id, target_h_index, replicate_id), block in sorted(by_block.items()):
        full = int(block["original_full"]["correct"])
        label = block["original_full"].get("proposal_correctness")
        if label in (0, 1):
            proposal_labels[(problem_id, target_h_index)] = int(label)
        for condition in CONDITIONS:
            controlled = int(block[condition]["correct"])
            delta = full - controlled
            per_problem_condition[(problem_id, target_h_index, condition)].append(delta)
            paired_rows.append(
                {
                    "problem_id": problem_id,
                    "hypothesis_index": target_h_index,
                    "replicate_id": replicate_id,
                    "proposal_correctness": label,
                    "condition": condition,
                    "original_full_correct": full,
                    "controlled_correct": controlled,
                    "signed_effect": delta,
                    "original_pool_word_count": block["original_full"].get(
                        "condition_pool_word_count"
                    ),
                    "controlled_pool_word_count": block[condition].get(
                        "condition_pool_word_count"
                    ),
                }
            )

    signal_rows: list[dict[str, Any]] = []
    for (problem_id, target_h_index, condition), deltas in sorted(
        per_problem_condition.items()
    ):
        effect = _mean(deltas)
        helpful_votes = sum(delta > 0 for delta in deltas)
        harmful_votes = sum(delta < 0 for delta in deltas)
        if helpful_votes > len(deltas) / 2:
            persistence = "persistent_helpful"
        elif harmful_votes > len(deltas) / 2:
            persistence = "persistent_harmful"
        else:
            persistence = "indeterminate"
        signal_rows.append(
            {
                "problem_id": problem_id,
                "hypothesis_index": target_h_index,
                "proposal_correctness": proposal_labels.get(
                    (problem_id, target_h_index)
                ),
                "condition": condition,
                "n_replicates": len(deltas),
                "mean_signed_effect": round(effect, 8),
                "helpful_replicates": helpful_votes,
                "neutral_replicates": sum(delta == 0 for delta in deltas),
                "harmful_replicates": harmful_votes,
                "persistence": persistence,
            }
        )

    condition_rows: list[dict[str, Any]] = []
    for condition in CONDITIONS:
        relevant = [row for row in signal_rows if row["condition"] == condition]
        problem_values = {
            str(row["problem_id"]): float(row["mean_signed_effect"])
            for row in relevant
        }
        ci_low, ci_high = _cluster_bootstrap(
            problem_values,
            iterations=iterations,
            seed=_seed_for(seed, condition),
        )
        paired = [row for row in paired_rows if row["condition"] == condition]
        condition_rows.append(
            {
                "condition": condition,
                "problems": len(relevant),
                "replicate_pairs": len(paired),
                "mean_signed_effect": round(
                    _mean([float(row["signed_effect"]) for row in paired]), 8
                ),
                "cluster_ci95_low": round(ci_low, 8),
                "cluster_ci95_high": round(ci_high, 8),
                "helpful_pairs": sum(int(row["signed_effect"]) > 0 for row in paired),
                "neutral_pairs": sum(int(row["signed_effect"]) == 0 for row in paired),
                "harmful_pairs": sum(int(row["signed_effect"]) < 0 for row in paired),
                "persistent_helpful_signals": sum(
                    row["persistence"] == "persistent_helpful" for row in relevant
                ),
                "persistent_harmful_signals": sum(
                    row["persistence"] == "persistent_harmful" for row in relevant
                ),
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    for path, values in (
        (output_dir / "content_control_paired_events.csv", paired_rows),
        (output_dir / "content_control_signal_effects.csv", signal_rows),
        (output_dir / "content_control_summary.csv", condition_rows),
    ):
        with open(path, "w", newline="") as handle:
            if values:
                writer = csv.DictWriter(handle, fieldnames=list(values[0]))
                writer.writeheader()
                writer.writerows(values)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "benchmark": meta.get("benchmark"),
        "actor_model_id": meta.get("actor_model_id"),
        "run_contract_hash": meta.get("run_contract_hash"),
        "problems": len({row["problem_id"] for row in signal_rows}),
        "target_signals": len(
            {(row["problem_id"], row["hypothesis_index"]) for row in signal_rows}
        ),
        "replicates": meta.get("replicates"),
        "conditions": condition_rows,
        "interpretation": (
            "Positive signed effects mean the original target content improved "
            "correctness relative to the intervention; negative effects mean the "
            "intervention improved correctness."
        ),
    }
    (output_dir / "content_control_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_dir", required=True)
    parser.add_argument("--output_dir", default="")
    parser.add_argument("--bootstrap_iterations", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260723)
    parser.add_argument("--allow_incomplete", action="store_true")
    args = parser.parse_args()
    run_dir = Path(args.run_dir)
    output_dir = Path(args.output_dir) if args.output_dir else run_dir / "analysis"
    summary = analyze(
        run_dir,
        output_dir=output_dir,
        iterations=args.bootstrap_iterations,
        seed=args.seed,
        allow_incomplete=args.allow_incomplete,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
