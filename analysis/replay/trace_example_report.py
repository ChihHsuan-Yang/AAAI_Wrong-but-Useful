#!/usr/bin/env python3
"""Build auditable wrong-helpful and correct-harmful trace shortlists.

The report joins canonical Layer-A and K=5 leave-one-out records with the
original benchmark problem. It never invents or rewrites agent text. The output
carries enough provenance to recover every quoted field from the release.

REQUIRES NON-PUBLIC INPUTS. Two things this repository does not ship:

* ``--release_root`` -- the per-benchmark raw replay shards
  (``raw/<benchmark>/dhd/<model>/{layer_a,loo}/part-00000.jsonl.zst``). These
  carry verbatim agent message text and are not in the public data release.
* ``--data_root`` -- the benchmark question text, which you must obtain from
  each benchmark's own upstream release under that benchmark's own license.

OUTPUTS ARE NOT REDISTRIBUTABLE. ``trace_candidates.json`` embeds verbatim
benchmark question text, including LAB-Bench (CC-BY-SA-4.0, carries a canary)
and MaScQA (CC-BY-NC-SA-4.0) content that ``DATA.md`` deliberately excludes from
this repository. Run it locally; do not republish what it writes.

The script itself ships no data and takes every root as an argument, so it is
safe to read and to run against inputs you are licensed to hold.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from offline_routing_analysis import (  # noqa: E402
    BENCHMARKS,
    MODELS,
    _read_jsonl_zst,
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"Non-object JSON at {path}:{line_number}")
            rows.append(value)
    return rows


def _problem_text(row: dict[str, Any]) -> str:
    return str(row.get("input") or row.get("question") or row.get("problem") or "")


def _problem_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


#: Where each benchmark's problem file sits under ``--data_root``.
#:
#: You assemble ``--data_root`` yourself from each benchmark's own upstream
#: release under that benchmark's own license; this repository ships no
#: benchmark question text (see DATA.md). Override the layout with
#: ``--benchmark_layout`` pointing at a JSON object of
#: ``{"benchmark": "relative/path/all.jsonl"}`` if your copy is arranged
#: differently. Missing files are skipped with a warning rather than aborting,
#: so a partial ``--data_root`` still produces the benchmarks you do have.
DEFAULT_BENCHMARK_LAYOUT: dict[str, str] = {
    "jeebench": "jeebench/all.jsonl",
    "scibench": "scibench/all.jsonl",
    "labbench": "labbench/all.jsonl",
    "mascqa": "mascqa/all.jsonl",
    "omnimath2": "omnimath2/*.jsonl",
}


def _load_problem_maps(
    data_root: Path, layout: dict[str, str] | None = None
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    layout = dict(layout or DEFAULT_BENCHMARK_LAYOUT)
    by_id: dict[str, dict[str, Any]] = {}
    by_hash: dict[str, dict[str, Any]] = {}
    paths: list[Path] = []
    for pattern in layout.values():
        if any(ch in pattern for ch in "*?["):
            paths.extend(sorted(data_root.glob(pattern)))
        else:
            paths.append(data_root / pattern)
    for path in paths:
        if not path.exists():
            print(f"[trace-report] skipping absent benchmark file: {path}")
            continue
        for row in _read_jsonl(path):
            problem_id = str(row.get("id") or row.get("question_id") or "")
            if problem_id:
                by_id[problem_id] = row
            text = _problem_text(row)
            if text:
                by_hash[_problem_hash(text)] = row
    if not by_id and not by_hash:
        raise SystemExit(
            f"No benchmark problems loaded from --data_root {data_root}. "
            "This report joins replay records to the original question text, "
            "which you must supply yourself from each benchmark's upstream "
            "release; see DATA.md. Use --benchmark_layout to describe a "
            "different on-disk arrangement."
        )
    return by_id, by_hash


def _committee_outcome(trace: dict[str, Any], k: int) -> dict[str, Any]:
    for outcome in trace.get("committee_outcomes") or []:
        if int(outcome.get("committee_size") or 0) == k:
            return outcome
    return {}


def _message_text(hypothesis: dict[str, Any]) -> str:
    fields = (
        ("Reasoning direction", "reasoning_direction"),
        ("Key idea", "key_idea"),
        ("Critical assumption", "critical_assumption"),
        ("What to check", "what_to_check"),
        ("Proposed answer", "proposed_answer"),
    )
    return "\n".join(
        f"{label}: {str(hypothesis.get(key) or '').strip()}"
        for label, key in fields
        if str(hypothesis.get(key) or "").strip()
    )


def _readability_score(record: dict[str, Any]) -> float:
    problem_len = len(record["problem_text"])
    message_len = len(record["message_text"])
    score = 0.0
    if 120 <= problem_len <= 1600:
        score += 3.0
    elif problem_len <= 3000:
        score += 1.0
    if 160 <= message_len <= 900:
        score += 3.0
    elif message_len <= 1400:
        score += 1.0
    if record["proposed_answer"] and len(record["proposed_answer"]) <= 80:
        score += 1.0
    if record["reduced_answer"] and len(record["reduced_answer"]) <= 80:
        score += 1.0
    if record["full_answer"] and len(record["full_answer"]) <= 80:
        score += 1.0
    if record["single_hypothesis_correct"] == 1:
        score += 0.5
    score -= min(2.0, len(re.findall(r"\\\\[a-zA-Z]+", record["message_text"])) / 12.0)
    score -= min(2.0, max(0, problem_len - 1600) / 2000.0)
    return round(score, 4)


def _candidate_records(
    *,
    release_root: Path,
    model: str,
    benchmark: str,
    by_id: dict[str, dict[str, Any]],
    by_hash: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    layer_path = (
        release_root / "raw" / benchmark / "dhd" / model / "layer_a" / "part-00000.jsonl.zst"
    )
    loo_path = (
        release_root / "raw" / benchmark / "dhd" / model / "loo" / "part-00000.jsonl.zst"
    )
    layer_rows = _read_jsonl_zst(layer_path)
    loo_rows = _read_jsonl_zst(loo_path)
    layer_by_id = {str(row.get("source_problem_id")): row for row in layer_rows}
    output: list[dict[str, Any]] = []

    for loo_row in loo_rows:
        problem_id = str(loo_row.get("source_problem_id") or "")
        layer = layer_by_id.get(problem_id)
        if not layer:
            continue
        trace = layer.get("trace") or {}
        hypotheses = trace.get("hypotheses") or []
        source_hash = str(layer.get("source_problem_hash") or "")
        problem = by_id.get(problem_id) or by_hash.get(source_hash)
        if not problem:
            continue
        full = _committee_outcome(trace, 5)
        for event in loo_row.get("loo") or []:
            if int(event.get("K") or 0) != 5:
                continue
            proposal = event.get("proposal_correctness")
            delta = event.get("delta_loo")
            if proposal == 0 and delta == 1:
                category = "wrong_helpful"
            elif proposal == 1 and delta == -1:
                category = "correct_harmful"
            else:
                continue
            index = int(event.get("removed_h_index"))
            if index < 0 or index >= len(hypotheses):
                continue
            hypothesis = hypotheses[index]
            record = {
                "category": category,
                "benchmark": benchmark,
                "model": model,
                "problem_id": problem_id,
                "problem_uid": layer.get("problem_uid"),
                "source_problem_hash": source_hash,
                "hypothesis_index": index,
                "role_name": hypothesis.get("role_name"),
                "problem_text": _problem_text(problem),
                "reference_answer": (
                    problem.get("answer_number")
                    or problem.get("answer")
                    or problem.get("label")
                ),
                "message_text": _message_text(hypothesis),
                "reasoning_direction": hypothesis.get("reasoning_direction"),
                "key_idea": hypothesis.get("key_idea"),
                "critical_assumption": hypothesis.get("critical_assumption"),
                "what_to_check": hypothesis.get("what_to_check"),
                "confidence": hypothesis.get("confidence"),
                "proposed_answer": hypothesis.get("proposed_answer_extracted")
                or hypothesis.get("proposed_answer"),
                "proposal_correctness": proposal,
                "single_hypothesis_answer": hypothesis.get("single_hyp_integrator_boxed"),
                "single_hypothesis_correct": hypothesis.get("single_hyp_integrator_correct"),
                "full_answer": full.get("integrator_boxed"),
                "full_correct": full.get("correct"),
                "reduced_answer": event.get("minus_i_boxed"),
                "reduced_correct": event.get("minus_i_correct"),
                "delta_loo": delta,
                "layer_source": str(layer_path),
                "loo_source": str(loo_path),
            }
            record["readability_score"] = _readability_score(record)
            output.append(record)
    return output


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = (
        "category",
        "benchmark",
        "model",
        "problem_id",
        "hypothesis_index",
        "role_name",
        "proposed_answer",
        "reference_answer",
        "full_answer",
        "reduced_answer",
        "single_hypothesis_correct",
        "readability_score",
    )
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fields})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release_root", required=True)
    parser.add_argument("--data_root", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--top_n", type=int, default=20)
    parser.add_argument(
        "--benchmark_layout",
        default="",
        help=(
            "Optional JSON file mapping benchmark -> path (relative to "
            "--data_root) of its problems JSONL. Defaults to "
            "DEFAULT_BENCHMARK_LAYOUT."
        ),
    )
    args = parser.parse_args()

    release_root = Path(args.release_root)
    output_dir = Path(args.output_dir)
    layout = (
        json.loads(Path(args.benchmark_layout).read_text())
        if args.benchmark_layout
        else None
    )
    by_id, by_hash = _load_problem_maps(Path(args.data_root), layout)
    all_records: list[dict[str, Any]] = []
    shortlists: list[dict[str, Any]] = []
    counts: dict[str, dict[str, dict[str, int]]] = {}

    for model in MODELS:
        counts[model] = {}
        for benchmark in BENCHMARKS:
            records = _candidate_records(
                release_root=release_root,
                model=model,
                benchmark=benchmark,
                by_id=by_id,
                by_hash=by_hash,
            )
            all_records.extend(records)
            counts[model][benchmark] = {}
            for category in ("wrong_helpful", "correct_harmful"):
                subset = [record for record in records if record["category"] == category]
                subset.sort(
                    key=lambda record: (
                        -record["readability_score"],
                        record["problem_id"],
                        record["hypothesis_index"],
                    )
                )
                counts[model][benchmark][category] = len(subset)
                shortlists.extend(subset[: args.top_n])

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "trace_candidates.json").write_text(
        json.dumps(
            {
                "counts": counts,
                "records": all_records,
                "provenance_note": (
                    "All messages are verbatim structured fields from sanitized canonical "
                    "Layer-A records joined to canonical K=5 LOO outcomes."
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    (output_dir / "trace_shortlists.json").write_text(
        json.dumps(shortlists, indent=2, sort_keys=True) + "\n"
    )
    _write_csv(output_dir / "trace_shortlists.csv", shortlists)
    print(json.dumps(counts, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
