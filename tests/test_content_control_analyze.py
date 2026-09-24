import csv
import json

from content_control_analyze import analyze


def _event(problem_id, replicate, condition, correct):
    return {
        "problem_id": problem_id,
        "K": 5,
        "condition": condition,
        "arm": "content_control",
        "removed_h_index": 2,
        "target_h_index": 2,
        "replicate_id": replicate,
        "schema_version": "dhd_replay_stability_v1",
        "valid": True,
        "run_contract_hash": "contract",
        "proposal_correctness": 0,
        "correct": correct,
        "condition_pool_word_count": 100,
    }


def test_content_control_analysis_uses_matched_replicate_differences(tmp_path):
    rows = []
    for replicate in range(3):
        rows.extend(
            [
                _event("p1", replicate, "original_full", 1),
                _event("p1", replicate, "removal", 0),
                _event("p1", replicate, "semantic_mask", 0),
                _event("p1", replicate, "answer_masked", 1),
                _event("p1", replicate, "reasoning_masked", 0),
            ]
        )
    (tmp_path / "replay_events.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows)
    )
    (tmp_path / "RUN_META.json").write_text(
        json.dumps(
            {
                "run_contract_hash": "contract",
                "benchmark": "synthetic",
                "actor_model_id": "actor",
                "control_manifest": "targets.jsonl",
                "replicates": 3,
            }
        )
    )
    (tmp_path / "validation.json").write_text(json.dumps({"complete": True}))

    summary = analyze(
        tmp_path,
        output_dir=tmp_path / "analysis",
        iterations=100,
        seed=7,
        allow_incomplete=False,
    )
    by_condition = {row["condition"]: row for row in summary["conditions"]}
    assert by_condition["removal"]["mean_signed_effect"] == 1
    assert by_condition["answer_masked"]["mean_signed_effect"] == 0
    assert by_condition["reasoning_masked"]["persistent_helpful_signals"] == 1

    signals = list(
        csv.DictReader(
            (tmp_path / "analysis" / "content_control_signal_effects.csv").open()
        )
    )
    removal = next(row for row in signals if row["condition"] == "removal")
    assert removal["persistence"] == "persistent_helpful"
