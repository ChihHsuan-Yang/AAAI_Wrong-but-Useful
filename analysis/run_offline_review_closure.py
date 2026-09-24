#!/usr/bin/env python3
"""Reproduce uncertainty and regret-source diagnostics for the DHD paper.

This script reads the sanitized Hugging Face release candidate and makes no
model or evaluator calls. It reports problem-cluster bootstrap intervals for
the pooled and benchmark-level budget-one policies and decomposes the gap
between the proposal-correctness oracle and the hindsight best-single outcome.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

BENCHMARKS = ("omnimath2", "jeebench", "scibench", "labbench", "mascqa")
MODELS = ("gpt_oss_120b", "gemma_4_31b")
POLICIES = (
    "random_hypothesis",
    "answer_consensus",
    "highest_self_reported_confidence",
    "proposal_correctness_oracle",
    "best_single_outcome_oracle",
    "independent_k0",
    "full_k5",
)
ANALYSIS_VERSION = "offline_review_closure_v3"


def _read_jsonl_zst(path: Path) -> list[dict[str, Any]]:
    import zstandard

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


def _extract_boxed(text: str) -> str:
    marker = r"\boxed{"
    last = ""
    start = 0
    while True:
        index = text.find(marker, start)
        if index < 0:
            return last
        cursor = index + len(marker)
        depth = 1
        chunks: list[str] = []
        while cursor < len(text) and depth:
            char = text[cursor]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if not depth:
                    break
            chunks.append(char)
            cursor += 1
        if not depth:
            last = "".join(chunks).strip()
        start = index + 1


def _normalized_answer(value: Any) -> str:
    text = str(value or "")
    boxed = _extract_boxed(text)
    if boxed:
        text = boxed
    else:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = lines[-1].rstrip(".") if lines else text.strip()
    text = unicodedata.normalize("NFKC", text).lower()
    replacements = {
        r"\dfrac": r"\frac",
        r"\tfrac": r"\frac",
        r"\displaystyle": "",
        r"\left": "",
        r"\right": "",
        "−": "-",
        "–": "-",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"\\(?:,|!|;|:|quad|qquad)", "", text)
    text = text.replace("$", "")
    text = re.sub(r"\\[\[\](){}]", "", text)
    return re.sub(r"\s+", "", text).strip(".,;:")


def _mean(values: Iterable[float]) -> float:
    items = list(values)
    return sum(items) / len(items) if items else float("nan")


def _tied_mean(values: list[float], keys: list[float], *, maximize: bool) -> float:
    target = max(keys) if maximize else min(keys)
    selected = [
        value
        for value, key in zip(values, keys)
        if math.isclose(key, target, rel_tol=0.0, abs_tol=1e-12)
    ]
    return _mean(selected)


def _problem_record(row: dict[str, Any], benchmark: str) -> dict[str, Any] | None:
    trace = row.get("trace") or {}
    hypotheses = trace.get("hypotheses") or []
    if len(hypotheses) != 5:
        return None
    baseline = _binary((trace.get("no_hypothesis_baseline") or {}).get("correct"))
    full = _k5_correct(row)
    singles = [
        _binary(hypothesis.get("single_hyp_integrator_correct"))
        for hypothesis in hypotheses
    ]
    proposal = [
        _binary(hypothesis.get("proposal_correctness")) for hypothesis in hypotheses
    ]
    if baseline is None or full is None:
        return None
    if any(value is None for value in singles) or any(value is None for value in proposal):
        return None

    single_values = [float(value) for value in singles]
    proposal_values = [int(value) for value in proposal]
    confidence = [
        _confidence_score(hypothesis.get("confidence")) for hypothesis in hypotheses
    ]
    signatures = [
        _normalized_answer(
            hypothesis.get("proposed_answer_extracted")
            or hypothesis.get("proposed_answer")
        )
        or f"__missing_{index}"
        for index, hypothesis in enumerate(hypotheses)
    ]
    signature_counts = Counter(signatures)
    modal_count = max(signature_counts.values())
    consensus_indices = [
        index
        for index, signature in enumerate(signatures)
        if signature_counts[signature] == modal_count
    ]
    confidence_max = max(confidence)
    confidence_indices = [
        index
        for index, score in enumerate(confidence)
        if math.isclose(score, confidence_max, rel_tol=0.0, abs_tol=1e-12)
    ]
    correct_indices = [index for index, value in enumerate(proposal_values) if value == 1]
    correctness_indices = correct_indices or list(range(5))
    best_value = max(single_values)
    best_indices = [
        index for index, value in enumerate(single_values) if value == best_value
    ]
    random_accuracy = _mean(single_values)
    consensus_accuracy = _mean(
        [single_values[index] for index in consensus_indices]
    )
    confidence_accuracy = _tied_mean(single_values, confidence, maximize=True)
    correctness_accuracy = _mean(
        [single_values[index] for index in correctness_indices]
    )
    best_accuracy = best_value

    helpful = [
        int(baseline == 0 and single == 1) for single in single_values
    ]
    harmful = [
        int(baseline == 1 and single == 0) for single in single_values
    ]
    total_helpful = float(sum(helpful))
    total_harmful = float(sum(harmful))
    policy_indices = {
        "random_hypothesis": list(range(5)),
        "answer_consensus": consensus_indices,
        "highest_self_reported_confidence": confidence_indices,
        "proposal_correctness_oracle": correctness_indices,
        "best_single_outcome_oracle": best_indices,
    }
    exposure_metrics: dict[str, float] = {}
    for policy, indices in policy_indices.items():
        selected_helpful = _mean([float(helpful[index]) for index in indices])
        selected_harmful = _mean([float(harmful[index]) for index in indices])
        exposure_metrics[f"{policy}_helpful_discarded"] = (
            total_helpful - selected_helpful
        )
        exposure_metrics[f"{policy}_harmful_admitted"] = selected_harmful
    exposure_metrics["independent_k0_helpful_discarded"] = total_helpful
    exposure_metrics["independent_k0_harmful_admitted"] = 0.0
    exposure_metrics["full_k5_helpful_discarded"] = 0.0
    exposure_metrics["full_k5_harmful_admitted"] = total_harmful

    if best_accuracy == correctness_accuracy:
        regret_source = "no_correctness_oracle_regret"
    elif not correct_indices:
        regret_source = "no_correct_proposal_but_a_wrong_proposal_succeeds"
    else:
        correct_outcomes = [single_values[index] for index in correct_indices]
        wrong_outcomes = [
            single_values[index]
            for index, value in enumerate(proposal_values)
            if value == 0
        ]
        if max(correct_outcomes) == 0 and wrong_outcomes and max(wrong_outcomes) == 1:
            regret_source = "only_wrong_proposals_succeed_downstream"
        elif min(correct_outcomes) == 0 and max(correct_outcomes) == 1:
            regret_source = "correct_proposals_have_mixed_downstream_success"
        else:
            regret_source = "other"

    return {
        "problem_uid": str(
            row.get("problem_uid") or row.get("source_problem_id") or ""
        ),
        "benchmark": benchmark,
        "random_hypothesis": random_accuracy,
        "answer_consensus": consensus_accuracy,
        "highest_self_reported_confidence": confidence_accuracy,
        "proposal_correctness_oracle": correctness_accuracy,
        "best_single_outcome_oracle": best_accuracy,
        "independent_k0": float(baseline),
        "full_k5": float(full),
        "correctness_oracle_regret": best_accuracy - correctness_accuracy,
        "regret_source": regret_source,
        **exposure_metrics,
    }


def _bootstrap_policy_draws(
    records: list[dict[str, Any]], *, iterations: int, seed: int
):
    """Return paired problem-bootstrap means for every policy.

    The same resampled problem indices are used for all policies, preserving the
    pairing needed for policy differences and oracle-regret intervals.
    """
    import numpy as np

    matrix = np.asarray(
        [[float(record[policy]) for policy in POLICIES] for record in records],
        dtype=float,
    )
    rng = np.random.default_rng(seed)
    draws = np.empty((iterations, len(POLICIES)), dtype=float)
    batch_size = 256
    for start in range(0, iterations, batch_size):
        stop = min(iterations, start + batch_size)
        indices = rng.integers(
            0,
            len(records),
            size=(stop - start, len(records)),
        )
        draws[start:stop] = matrix[indices].mean(axis=1)
    return matrix.mean(axis=0), draws


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"No rows for {path}")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def analyze(
    release_root: Path,
    *,
    output_dir: Path,
    iterations: int,
    seed: int,
) -> dict[str, Any]:
    policy_rows: list[dict[str, Any]] = []
    benchmark_policy_rows: list[dict[str, Any]] = []
    decomposition_rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {
        "analysis_version": ANALYSIS_VERSION,
        "release_root": str(release_root),
        "bootstrap_iterations": iterations,
        "bootstrap_seed": seed,
        "models": {},
    }

    for model in MODELS:
        records: list[dict[str, Any]] = []
        records_by_benchmark: dict[str, list[dict[str, Any]]] = {}
        source_counts: dict[str, dict[str, int]] = {}
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
            source = _read_jsonl_zst(path)
            eligible = [
                record
                for row in source
                if (record := _problem_record(row, benchmark)) is not None
            ]
            records.extend(eligible)
            records_by_benchmark[benchmark] = eligible
            source_counts[benchmark] = {
                "source": len(source),
                "eligible": len(eligible),
                "excluded": len(source) - len(eligible),
            }

        import numpy as np

        point_estimates, bootstrap_draws = _bootstrap_policy_draws(
            records,
            iterations=iterations,
            seed=seed + MODELS.index(model),
        )
        policy_index = {policy: index for index, policy in enumerate(POLICIES)}
        random_index = policy_index["random_hypothesis"]
        best_index = policy_index["best_single_outcome_oracle"]
        for policy in POLICIES:
            index = policy_index[policy]
            point = float(point_estimates[index])
            ci_low, ci_high = np.quantile(
                bootstrap_draws[:, index], [0.025, 0.975]
            )
            regret_draws = (
                bootstrap_draws[:, best_index] - bootstrap_draws[:, index]
            )
            regret = float(point_estimates[best_index] - point)
            regret_low, regret_high = np.quantile(
                regret_draws, [0.025, 0.975]
            )
            difference_draws = (
                bootstrap_draws[:, index] - bootstrap_draws[:, random_index]
            )
            random_difference = float(point - point_estimates[random_index])
            diff_low, diff_high = np.quantile(
                difference_draws, [0.025, 0.975]
            )
            policy_rows.append(
                {
                    "model": model,
                    "policy": policy,
                    "eligible_problems": len(records),
                    "accuracy_percent": round(100.0 * point, 3),
                    "accuracy_ci95_low": round(100.0 * ci_low, 3),
                    "accuracy_ci95_high": round(100.0 * ci_high, 3),
                    "difference_vs_random_points": round(
                        100.0 * random_difference, 3
                    ),
                    "difference_vs_random_ci95_low": round(100.0 * diff_low, 3),
                    "difference_vs_random_ci95_high": round(100.0 * diff_high, 3),
                    "best_single_regret_points": round(100.0 * regret, 3),
                    "best_single_regret_ci95_low": round(100.0 * regret_low, 3),
                    "best_single_regret_ci95_high": round(100.0 * regret_high, 3),
                    "helpful_discarded_mean": round(
                        _mean(
                            float(record[f"{policy}_helpful_discarded"])
                            for record in records
                        ),
                        6,
                    ),
                    "harmful_admitted_mean": round(
                        _mean(
                            float(record[f"{policy}_harmful_admitted"])
                            for record in records
                        ),
                        6,
                    ),
                }
            )

        benchmark_summaries: dict[str, dict[str, Any]] = {}
        for benchmark_index, benchmark in enumerate(BENCHMARKS):
            benchmark_records = records_by_benchmark[benchmark]
            benchmark_points, benchmark_draws = _bootstrap_policy_draws(
                benchmark_records,
                iterations=iterations,
                seed=(
                    seed
                    + 100
                    + MODELS.index(model) * len(BENCHMARKS)
                    + benchmark_index
                ),
            )
            random_index = policy_index["random_hypothesis"]
            consensus_index = policy_index["answer_consensus"]
            confidence_index = policy_index["highest_self_reported_confidence"]
            correctness_index = policy_index["proposal_correctness_oracle"]
            best_index = policy_index["best_single_outcome_oracle"]
            correctness_difference_draws = (
                benchmark_draws[:, correctness_index]
                - benchmark_draws[:, random_index]
            )
            best_difference_draws = (
                benchmark_draws[:, best_index]
                - benchmark_draws[:, correctness_index]
            )
            correctness_low, correctness_high = np.quantile(
                correctness_difference_draws, [0.025, 0.975]
            )
            best_low, best_high = np.quantile(
                best_difference_draws, [0.025, 0.975]
            )
            benchmark_row = {
                "model": model,
                "benchmark": benchmark,
                "eligible_problems": len(benchmark_records),
                "random_accuracy_percent": round(
                    100.0 * float(benchmark_points[random_index]), 3
                ),
                "consensus_accuracy_percent": round(
                    100.0 * float(benchmark_points[consensus_index]), 3
                ),
                "confidence_accuracy_percent": round(
                    100.0 * float(benchmark_points[confidence_index]), 3
                ),
                "correctness_oracle_accuracy_percent": round(
                    100.0 * float(benchmark_points[correctness_index]), 3
                ),
                "best_single_accuracy_percent": round(
                    100.0 * float(benchmark_points[best_index]), 3
                ),
                "correctness_minus_random_points": round(
                    100.0
                    * float(
                        benchmark_points[correctness_index]
                        - benchmark_points[random_index]
                    ),
                    3,
                ),
                "correctness_minus_random_ci95_low": round(
                    100.0 * float(correctness_low), 3
                ),
                "correctness_minus_random_ci95_high": round(
                    100.0 * float(correctness_high), 3
                ),
                "best_minus_correctness_points": round(
                    100.0
                    * float(
                        benchmark_points[best_index]
                        - benchmark_points[correctness_index]
                    ),
                    3,
                ),
                "best_minus_correctness_ci95_low": round(
                    100.0 * float(best_low), 3
                ),
                "best_minus_correctness_ci95_high": round(
                    100.0 * float(best_high), 3
                ),
            }
            benchmark_policy_rows.append(benchmark_row)
            benchmark_summaries[benchmark] = benchmark_row

        counts = Counter(record["regret_source"] for record in records)
        total_regret = sum(
            float(record["correctness_oracle_regret"]) for record in records
        )
        for source in (
            "no_correctness_oracle_regret",
            "no_correct_proposal_but_a_wrong_proposal_succeeds",
            "only_wrong_proposals_succeed_downstream",
            "correct_proposals_have_mixed_downstream_success",
            "other",
        ):
            contribution = sum(
                float(record["correctness_oracle_regret"])
                for record in records
                if record["regret_source"] == source
            )
            decomposition_rows.append(
                {
                    "model": model,
                    "source": source,
                    "problems": counts[source],
                    "problem_share_percent": round(
                        100.0 * counts[source] / len(records), 3
                    ),
                    "regret_contribution_points": round(
                        100.0 * contribution / len(records), 3
                    ),
                    "share_of_total_correctness_oracle_regret_percent": round(
                        100.0 * contribution / total_regret, 3
                    )
                    if total_regret
                    else 0.0,
                }
            )

        summary["models"][model] = {
            "eligible_problems": len(records),
            "source_counts": source_counts,
            "proposal_correctness_oracle_regret_points": round(
                100.0
                * _mean(
                    float(record["correctness_oracle_regret"])
                    for record in records
                ),
                6,
            ),
            "regret_source_counts": dict(sorted(counts.items())),
            "benchmark_policy_diagnostics": benchmark_summaries,
        }

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "offline_policy_bootstrap.csv", policy_rows)
    _write_csv(
        output_dir / "offline_policy_by_benchmark.csv",
        benchmark_policy_rows,
    )
    _write_csv(
        output_dir / "correctness_oracle_regret_decomposition.csv",
        decomposition_rows,
    )
    (output_dir / "offline_review_closure.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-root", required=True)
    parser.add_argument("--output-dir", default="analysis")
    parser.add_argument("--bootstrap-iterations", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260724)
    args = parser.parse_args()
    summary = analyze(
        Path(args.release_root),
        output_dir=Path(args.output_dir),
        iterations=args.bootstrap_iterations,
        seed=args.seed,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
