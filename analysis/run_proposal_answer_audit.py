#!/usr/bin/env python3
"""Audit answer-bearing proposal coverage in canonical DHD matrices."""

import argparse
import json
from collections import Counter
from pathlib import Path


RENDERED_FIELDS = (
    "proposed_answer",
    "reasoning_direction",
    "key_idea",
    "critical_assumption",
    "what_to_check",
    "confidence",
)


def load_jsonl(path):
    rows = {}
    with open(path) as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            problem_id = str(row.get("problem_id") or "")
            if not problem_id:
                raise ValueError(f"Missing problem_id at {path}:{line_number}")
            if problem_id in rows:
                raise ValueError(f"Duplicate problem_id {problem_id!r} in {path}")
            rows[problem_id] = row
    return rows


def effect_direction(reduced_correct, full_correct):
    if reduced_correct == 0 and full_correct == 1:
        return "help"
    if reduced_correct == 1 and full_correct == 0:
        return "harm"
    return "neutral"


def is_answer_bearing(hypothesis):
    return bool(str(hypothesis.get("proposed_answer_extracted") or "").strip())


def is_renderable(hypothesis):
    return any(str(hypothesis.get(key) or "").strip() for key in RENDERED_FIELDS)


def audit_benchmark(entry):
    layer_rows = load_jsonl(entry["layer_a_path"])
    loo_rows = load_jsonl(entry["loo_path"])
    if set(layer_rows) != set(loo_rows):
        raise ValueError(f"Layer/LOO IDs differ for {entry['benchmark']}")

    quality = Counter()
    missing_examples = []
    for problem_id, row in layer_rows.items():
        hypotheses = row.get("hypotheses") or []
        if len(hypotheses) != 5:
            raise ValueError(
                f"{entry['benchmark']}/{problem_id} does not have five hypotheses"
            )
        for index, hypothesis in enumerate(hypotheses):
            quality["total"] += 1
            if is_renderable(hypothesis):
                quality["renderable"] += 1
            if hypothesis.get("parse_complete") is True:
                quality["parse_complete"] += 1
            correctness = hypothesis.get("proposal_correctness")
            if correctness in (0, 1):
                quality[f"proposal_correctness_{int(correctness)}"] += 1
            if is_answer_bearing(hypothesis):
                quality["answer_bearing"] += 1
            else:
                quality["missing_answer"] += 1
                if len(missing_examples) < 5:
                    missing_examples.append(
                        {
                            "problem_id": problem_id,
                            "hypothesis_index": index,
                            "proposal_correctness": hypothesis.get(
                                "proposal_correctness"
                            ),
                            "parse_complete": hypothesis.get("parse_complete"),
                            "proposed_answer": str(
                                hypothesis.get("proposed_answer_extracted") or ""
                            ),
                        }
                    )

    groups = {
        "loo_all": Counter(),
        "loo_answer_bearing_only": Counter(),
        "loo_missing_answer_only": Counter(),
        "loo_renderable": Counter(),
        "loo_renderable_answer_bearing_only": Counter(),
        "loo_renderable_missing_answer_only": Counter(),
    }
    for problem_id, row in loo_rows.items():
        hypotheses = layer_rows[problem_id]["hypotheses"]
        for item in row.get("loo") or []:
            hypothesis = hypotheses[int(item["removed_h_index"])]
            correctness = item.get("proposal_correctness")
            if correctness not in (0, 1):
                proposal_label = "null"
            else:
                proposal_label = "correct" if int(correctness) == 1 else "wrong"
            effect = effect_direction(
                int(item["minus_i_correct"]), int(item["fullK_correct"])
            )
            key = f"{proposal_label}_{effect}"
            groups["loo_all"][key] += 1
            if is_answer_bearing(hypothesis):
                groups["loo_answer_bearing_only"][key] += 1
            else:
                groups["loo_missing_answer_only"][key] += 1
            if is_renderable(hypothesis):
                groups["loo_renderable"][key] += 1
                suffix = (
                    "answer_bearing_only"
                    if is_answer_bearing(hypothesis)
                    else "missing_answer_only"
                )
                groups[f"loo_renderable_{suffix}"][key] += 1

    return {
        "benchmark": entry["benchmark"],
        "problems": len(layer_rows),
        "proposal_quality": dict(quality),
        "answer_bearing_rate": quality["answer_bearing"] / quality["total"],
        "parse_complete_rate": quality["parse_complete"] / quality["total"],
        **{name: dict(counts) for name, counts in groups.items()},
        "missing_answer_examples": missing_examples,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("--output")
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text())
    benchmarks = [audit_benchmark(entry) for entry in manifest["benchmarks"]]

    pooled_quality = Counter()
    pooled_groups = {
        name: Counter()
        for name in (
            "loo_all",
            "loo_answer_bearing_only",
            "loo_missing_answer_only",
            "loo_renderable",
            "loo_renderable_answer_bearing_only",
            "loo_renderable_missing_answer_only",
        )
    }
    for row in benchmarks:
        pooled_quality.update(row["proposal_quality"])
        for name in pooled_groups:
            pooled_groups[name].update(row[name])

    payload = {
        "manifest": str(Path(args.manifest).resolve()),
        "benchmarks": benchmarks,
        "pooled": {
            "proposal_quality": dict(pooled_quality),
            "answer_bearing_rate": (
                pooled_quality["answer_bearing"] / pooled_quality["total"]
            ),
            "parse_complete_rate": (
                pooled_quality["parse_complete"] / pooled_quality["total"]
            ),
            **{name: dict(counts) for name, counts in pooled_groups.items()},
        },
    }
    output = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(output)
    print(output, end="")


if __name__ == "__main__":
    main()
