#!/usr/bin/env python3
"""Measure whether the DHD K=5 integrator behaves like proposal voting.

The analysis uses only saved layer-A records from the canonical DHD release.
Correct proposals are grouped by reference equivalence. Wrong proposals are
grouped by conservative deterministic normalization, so wrong-answer agreement
is a lower bound when equivalent strings use different syntax.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import unicodedata
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, TextIO


ANALYSIS_VERSION = "dhd_majority_following_v2"
BENCHMARKS = ("omnimath2", "jeebench", "scibench", "labbench", "mascqa")
MODELS = ("gpt_oss_120b", "gemma_4_31b")
GOLD_EQUIVALENT = "__gold_equivalent__"


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


def _extract_final_answer(value: Any) -> str:
    text = str(value or "")
    boxed = _extract_boxed(text)
    if boxed:
        return boxed
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1].rstrip(".") if lines else text.strip()


def _normalized_answer(value: Any) -> str:
    text = unicodedata.normalize("NFKC", _extract_final_answer(value)).lower()
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
    text = re.sub(r"\s+", "", text).strip(".,;:")
    if text.count("=") == 1:
        lhs, rhs = text.split("=", 1)
        if lhs and rhs:
            lhs = re.sub(r"\([^()]*\)$", "", lhs)
            text = f"{lhs}={rhs}"
    return text


@contextmanager
def _open_jsonl(path: Path) -> Iterator[TextIO]:
    if path.suffix != ".zst":
        with path.open(encoding="utf-8") as handle:
            yield handle
        return

    process = subprocess.Popen(
        ["zstd", "-dc", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    assert process.stdout is not None
    try:
        yield process.stdout
    finally:
        process.stdout.close()
        stderr = process.stderr.read() if process.stderr else ""
        return_code = process.wait()
        if return_code:
            raise RuntimeError(f"zstd failed for {path}: {stderr.strip()}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _k5_outcome(row: dict[str, Any]) -> dict[str, Any] | None:
    outcomes = row.get("trace", {}).get("committee_outcomes", [])
    return next(
        (
            outcome
            for outcome in outcomes
            if outcome.get("committee_size") == 5
            and outcome.get("correct") in (0, 1, False, True)
        ),
        None,
    )


def _record(row: dict[str, Any]) -> dict[str, Any] | None:
    hypotheses = row.get("trace", {}).get("hypotheses", [])
    outcome = _k5_outcome(row)
    if (
        len(hypotheses) != 5
        or outcome is None
        or any(
            hypothesis.get("proposal_correctness") not in (0, 1, False, True)
            for hypothesis in hypotheses
        )
    ):
        return None

    signatures: list[str] = []
    for index, hypothesis in enumerate(hypotheses):
        if bool(hypothesis["proposal_correctness"]):
            signatures.append(GOLD_EQUIVALENT)
            continue
        answer = (
            hypothesis.get("proposed_answer_extracted")
            or hypothesis.get("proposed_answer")
            or ""
        )
        normalized = _normalized_answer(answer)
        signatures.append(f"wrong:{normalized}" if normalized else f"missing:{index}")

    correct_count = sum(
        bool(hypothesis["proposal_correctness"]) for hypothesis in hypotheses
    )
    integrator_correct = bool(outcome["correct"])
    integrator_signature = (
        GOLD_EQUIVALENT
        if integrator_correct
        else f"wrong:{_normalized_answer(outcome.get('integrator_boxed'))}"
    )
    signature_counts = Counter(signatures)
    strict_majority, majority_size = signature_counts.most_common(1)[0]
    if majority_size < 3:
        strict_majority = ""

    return {
        "majority_correct": correct_count >= 3,
        "integrator_correct": integrator_correct,
        "strict_answer_majority": bool(strict_majority),
        "strict_majority_followed": bool(
            strict_majority and integrator_signature == strict_majority
        ),
    }


def _summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    for record in records:
        majority = record["majority_correct"]
        integrator = record["integrator_correct"]
        counts["majority_correct"] += int(majority)
        counts["integrator_correct"] += int(integrator)
        counts["integrator_only"] += int(integrator and not majority)
        counts["majority_only"] += int(majority and not integrator)
        counts["strict_majority"] += int(record["strict_answer_majority"])
        counts["strict_followed"] += int(record["strict_majority_followed"])

    total = len(records)
    strict_total = counts["strict_majority"]
    return {
        "problem_count": total,
        "proposal_majority_accuracy": counts["majority_correct"] / total,
        "integrator_accuracy": counts["integrator_correct"] / total,
        "integrator_only": counts["integrator_only"],
        "majority_only": counts["majority_only"],
        "strict_majority_problems": strict_total,
        "strict_majority_follow_rate": (
            counts["strict_followed"] / strict_total if strict_total else None
        ),
    }


def _source_path(root: Path, benchmark: str, model: str) -> Path:
    return (
        root
        / "raw"
        / benchmark
        / "dhd"
        / model
        / "layer_a"
        / "part-00000.jsonl.zst"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    for model in MODELS:
        pooled: list[dict[str, Any]] = []
        for benchmark in BENCHMARKS:
            path = _source_path(args.release_root, benchmark, model)
            if not path.is_file():
                raise FileNotFoundError(path)
            records: list[dict[str, Any]] = []
            with _open_jsonl(path) as handle:
                for raw in handle:
                    record = _record(json.loads(raw))
                    if record is not None:
                        records.append(record)
            summary = _summarize(records)
            rows.append({"model": model, "benchmark": benchmark, **summary})
            pooled.extend(records)
            sources.append(
                {
                    "model": model,
                    "benchmark": benchmark,
                    "path": str(path),
                    "sha256": _sha256(path),
                }
            )
        rows.append({"model": model, "benchmark": "pooled", **_summarize(pooled)})

    csv_path = args.output_dir / "majority_diagnostic.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    payload = {
        "analysis_version": ANALYSIS_VERSION,
        "definitions": {
            "proposal_majority": (
                "at least three of five proposals are evaluator-labeled correct"
            ),
            "strict_answer_majority": (
                "at least three normalized proposal answer signatures agree"
            ),
            "answer_equivalence": (
                "correct proposals collapse by reference equivalence; wrong "
                "proposals use deterministic normalization"
            ),
            "causal_caveat": (
                "answer agreement is observational and does not prove copying"
            ),
        },
        "rows": rows,
        "sources": sources,
    }
    json_path = args.output_dir / "majority_diagnostic.json"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
