#!/usr/bin/env python3
"""Offline DHD routing and integration diagnostics.

Sole generator of the paper's single-vs-full 2x2 table
(``tab:app_single_full_2x2``): shared success, observable interference,
observable synergy, shared failure. That table exists nowhere else -- the
ancillary artifact's ``analysis/run_offline_review_closure.py`` is a superset
for the *routing* question (7 policies, including answer consensus, plus
bootstrap CIs and a regret decomposition) but computes no 2x2. The two are
complementary; for routing tables, the artifact script is authoritative.

REQUIRES A NON-PUBLIC INPUT. ``--release_root`` points at raw per-benchmark
replay shards (``raw/<benchmark>/dhd/<model>/layer_a/part-00000.jsonl.zst``)
that this repository does not ship. The script itself carries no data and no
default root, so it is readable and testable without them: its unit tests in
``tests/test_offline_routing_analysis.py`` exercise the analysis on synthetic
records. Requires the optional ``zstandard`` dependency.

The script consumes canonical Layer-A records. It makes no model or evaluator
calls. Two analyses are produced:

1. A directly observable 2x2 crossing whether any single-hypothesis integration
   succeeds with whether the full K=5 integration succeeds.
2. Budget-one routing policies using the already-recorded single-hypothesis
   outcomes.

The proposal-correctness oracle is intentionally an oracle: if at least one
proposal has a correct final answer, it selects uniformly among those proposals;
otherwise it falls back to uniform random selection. Highest-confidence routing
uses a documented deterministic parser and averages over exact score ties.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

BENCHMARKS = ("omnimath2", "jeebench", "scibench", "labbench", "mascqa")
MODELS = ("gpt_oss_120b", "gemma_4_31b")


def _read_jsonl_zst(path: Path) -> list[dict[str, Any]]:
    try:
        import zstandard
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise SystemExit(
            "This analysis reads zstd-compressed shards and needs the optional "
            "`zstandard` dependency: python -m pip install zstandard"
        ) from exc

    rows: list[dict[str, Any]] = []
    with path.open("rb") as raw:
        with zstandard.ZstdDecompressor().stream_reader(raw) as reader:
            text = reader.read().decode("utf-8")
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"Non-object JSON at {path}:{line_number}")
        rows.append(value)
    return rows


def _binary(value: Any) -> int | None:
    if value is True or value == 1:
        return 1
    if value is False or value == 0:
        return 0
    return None


def _k5_correct(row: dict[str, Any]) -> int | None:
    trace = row.get("trace") or {}
    for outcome in trace.get("committee_outcomes") or []:
        if int(outcome.get("committee_size") or 0) == 5:
            return _binary(outcome.get("correct"))
    return _binary((row.get("outcome") or {}).get("final_correct"))


def _confidence_score(value: Any) -> float:
    """Map free-text self-confidence to a reproducible ordinal score."""
    text = str(value or "").strip().lower()
    if not text:
        return 0.5

    percentages = [
        float(match) / 100.0
        for match in re.findall(r"(?<![\d.])(\d{1,3}(?:\.\d+)?)\s*%", text)
    ]
    if percentages:
        return min(1.0, max(0.0, percentages[0]))

    decimals = [
        float(match)
        for match in re.findall(r"(?<![\d.])(0(?:\.\d+)?|1(?:\.0+)?)(?![\d.])", text)
    ]
    if decimals:
        return min(1.0, max(0.0, decimals[0]))

    if any(token in text for token in ("very high", "extremely high", "certain")):
        return 0.95
    if "high" in text or "confident" in text:
        return 0.8
    if any(token in text for token in ("medium", "moderate", "fair")):
        return 0.6
    if any(token in text for token in ("very low", "extremely low", "uncertain")):
        return 0.2
    if "low" in text or "tentative" in text:
        return 0.35
    return 0.5


def _uniform_weights(indices: Iterable[int], size: int) -> list[float]:
    selected = list(indices)
    weights = [0.0] * size
    if not selected:
        return weights
    probability = 1.0 / len(selected)
    for index in selected:
        weights[index] = probability
    return weights


def _policy_weights(
    policy: str,
    hypotheses: list[dict[str, Any]],
    single_outcomes: list[int],
) -> list[float]:
    size = len(hypotheses)
    if policy == "random_hypothesis":
        return _uniform_weights(range(size), size)
    if policy == "highest_self_reported_confidence":
        scores = [_confidence_score(hypothesis.get("confidence")) for hypothesis in hypotheses]
        best = max(scores)
        return _uniform_weights(
            (index for index, score in enumerate(scores) if math.isclose(score, best)),
            size,
        )
    if policy == "proposal_correctness_oracle":
        correct = [
            index
            for index, hypothesis in enumerate(hypotheses)
            if _binary(hypothesis.get("proposal_correctness")) == 1
        ]
        return _uniform_weights(correct if correct else range(size), size)
    if policy == "best_single_outcome_oracle":
        best = max(single_outcomes)
        return _uniform_weights(
            (index for index, outcome in enumerate(single_outcomes) if outcome == best),
            size,
        )
    raise ValueError(f"Unknown policy: {policy}")


def _mean(values: Iterable[float]) -> float:
    items = list(values)
    return sum(items) / len(items) if items else float("nan")


def _analyze_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    eligible: list[dict[str, Any]] = []
    exclusion_counts: Counter[str] = Counter()
    for row in rows:
        trace = row.get("trace") or {}
        hypotheses = trace.get("hypotheses") or []
        if len(hypotheses) != 5:
            exclusion_counts["not_exactly_five_hypotheses"] += 1
            continue
        baseline = _binary((trace.get("no_hypothesis_baseline") or {}).get("correct"))
        full = _k5_correct(row)
        singles = [
            _binary(hypothesis.get("single_hyp_integrator_correct"))
            for hypothesis in hypotheses
        ]
        if baseline is None:
            exclusion_counts["missing_binary_k0"] += 1
            continue
        if full is None:
            exclusion_counts["missing_binary_full_k5"] += 1
            continue
        if any(value is None for value in singles):
            exclusion_counts["missing_single_hypothesis_outcome"] += 1
            continue
        eligible.append(
            {
                "problem_uid": row.get("problem_uid") or row.get("source_problem_id"),
                "baseline": baseline,
                "full": full,
                "hypotheses": hypotheses,
                "singles": [int(value) for value in singles],
            }
        )

    two_by_two = Counter()
    for row in eligible:
        any_single = int(any(row["singles"]))
        full = int(row["full"])
        name = {
            (1, 1): "shared_success",
            (1, 0): "observable_interference",
            (0, 1): "observable_synergy",
            (0, 0): "shared_failure",
        }[(any_single, full)]
        two_by_two[name] += 1

    policy_names = (
        "random_hypothesis",
        "highest_self_reported_confidence",
        "proposal_correctness_oracle",
        "best_single_outcome_oracle",
    )
    per_policy: dict[str, list[dict[str, float]]] = defaultdict(list)
    for row in eligible:
        baseline = int(row["baseline"])
        singles = list(row["singles"])
        effects = [outcome - baseline for outcome in singles]
        total_helpful = sum(effect == 1 for effect in effects)
        total_harmful = sum(effect == -1 for effect in effects)

        for policy in policy_names:
            weights = _policy_weights(policy, row["hypotheses"], singles)
            accuracy = sum(weight * outcome for weight, outcome in zip(weights, singles))
            helpful_admitted = sum(
                weight * int(effect == 1) for weight, effect in zip(weights, effects)
            )
            harmful_admitted = sum(
                weight * int(effect == -1) for weight, effect in zip(weights, effects)
            )
            per_policy[policy].append(
                {
                    "accuracy": accuracy,
                    "helpful_discarded": total_helpful - helpful_admitted,
                    "harmful_admitted": harmful_admitted,
                }
            )

        per_policy["independent_k0"].append(
            {
                "accuracy": float(baseline),
                "helpful_discarded": float(total_helpful),
                "harmful_admitted": 0.0,
            }
        )
        per_policy["full_k5"].append(
            {
                "accuracy": float(row["full"]),
                "helpful_discarded": 0.0,
                "harmful_admitted": float(total_harmful),
            }
        )

    oracle_accuracy = _mean(
        item["accuracy"] for item in per_policy["best_single_outcome_oracle"]
    )
    policy_summary: dict[str, dict[str, float]] = {}
    for policy, values in per_policy.items():
        accuracy = _mean(item["accuracy"] for item in values)
        policy_summary[policy] = {
            "accuracy": accuracy,
            "accuracy_percent": 100.0 * accuracy,
            "helpful_signals_discarded_per_problem": _mean(
                item["helpful_discarded"] for item in values
            ),
            "harmful_signals_admitted_per_problem": _mean(
                item["harmful_admitted"] for item in values
            ),
            "best_single_oracle_regret_points": 100.0 * (oracle_accuracy - accuracy),
        }

    return {
        "source_rows": len(rows),
        "eligible_problems": len(eligible),
        "excluded_problems": len(rows) - len(eligible),
        "exclusion_counts": dict(sorted(exclusion_counts.items())),
        "integration_2x2": {
            **dict(sorted(two_by_two.items())),
            "n": len(eligible),
            "cell_definitions": {
                "shared_success": "at least one single-hypothesis integration succeeds and full-K=5 succeeds",
                "observable_interference": "at least one single-hypothesis integration succeeds but full-K=5 fails",
                "observable_synergy": "no single-hypothesis integration succeeds but full-K=5 succeeds",
                "shared_failure": "neither any single-hypothesis integration nor full-K=5 succeeds",
            },
        },
        "routing": policy_summary,
        "routing_definition": {
            "helpful_signal": "single-hypothesis integration correct while independent K=0 is wrong",
            "harmful_signal": "single-hypothesis integration wrong while independent K=0 is correct",
            "proposal_correctness_oracle": "uniform among correct proposals when any exist; otherwise uniform among all five",
            "tie_handling": "expected outcome under uniform selection among exact ties",
            "oracle_regret": "best-single-outcome oracle accuracy minus policy accuracy, in percentage points",
        },
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release_root", required=True)
    parser.add_argument("--output_dir", required=True)
    args = parser.parse_args()

    release_root = Path(args.release_root)
    output_dir = Path(args.output_dir)
    results: dict[str, Any] = {
        "analysis": "offline_budget_one_routing_and_single_vs_full_2x2",
        "release_root": str(release_root),
        "models": {},
    }
    routing_rows: list[dict[str, Any]] = []
    integration_rows: list[dict[str, Any]] = []

    for model in MODELS:
        results["models"][model] = {}
        pooled: list[dict[str, Any]] = []
        for benchmark in BENCHMARKS:
            path = (
                release_root
                / "raw"
                / benchmark
                / "dhd"
                / model
                / "layer_a"
                / "part-00000.jsonl.zst"
            )
            if not path.exists():
                raise SystemExit(
                    f"Missing replay shard: {path}\n"
                    "This analysis needs the raw per-benchmark replay shards, "
                    "which this repository does not ship (see "
                    "docs/PAPER_REPRODUCTION_MAP.md). Point --release_root at a "
                    "tree laid out as raw/<benchmark>/dhd/<model>/layer_a/"
                    "part-00000.jsonl.zst"
                )
            rows = _read_jsonl_zst(path)
            pooled.extend(rows)
            analysis = _analyze_group(rows)
            results["models"][model][benchmark] = analysis
        results["models"][model]["pooled_micro"] = _analyze_group(pooled)

        for benchmark, analysis in results["models"][model].items():
            for policy, metrics in analysis["routing"].items():
                routing_rows.append(
                    {
                        "model": model,
                        "benchmark": benchmark,
                        "policy": policy,
                        **{key: round(value, 6) for key, value in metrics.items()},
                        "eligible_problems": analysis["eligible_problems"],
                    }
                )
            cells = analysis["integration_2x2"]
            integration_rows.append(
                {
                    "model": model,
                    "benchmark": benchmark,
                    "eligible_problems": analysis["eligible_problems"],
                    "shared_success": cells.get("shared_success", 0),
                    "observable_interference": cells.get("observable_interference", 0),
                    "observable_synergy": cells.get("observable_synergy", 0),
                    "shared_failure": cells.get("shared_failure", 0),
                }
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "offline_routing_and_integration.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n"
    )
    _write_csv(output_dir / "budget_one_routing.csv", routing_rows)
    _write_csv(output_dir / "single_vs_full_2x2.csv", integration_rows)
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
