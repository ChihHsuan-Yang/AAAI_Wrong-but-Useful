from offline_routing_analysis import (
    _analyze_group,
    _confidence_score,
)


def _hyp(proposal, single, confidence):
    return {
        "proposal_correctness": proposal,
        "single_hyp_integrator_correct": single,
        "confidence": confidence,
    }


def _row(problem_id, baseline, full, hypotheses):
    return {
        "problem_uid": problem_id,
        "outcome": {"final_correct": bool(full)},
        "trace": {
            "no_hypothesis_baseline": {"correct": baseline},
            "committee_outcomes": [{"committee_size": 5, "correct": full}],
            "hypotheses": hypotheses,
        },
    }


def test_confidence_parser_handles_text_and_numbers():
    assert _confidence_score("high") == 0.8
    assert _confidence_score("medium") == 0.6
    assert _confidence_score("confidence 73%") == 0.73
    assert _confidence_score("") == 0.5


def test_two_by_two_and_budget_one_metrics():
    rows = [
        _row(
            "synergy",
            0,
            1,
            [
                _hyp(0, 0, "high"),
                _hyp(0, 0, "low"),
                _hyp(0, 0, "low"),
                _hyp(0, 0, "low"),
                _hyp(0, 0, "low"),
            ],
        ),
        _row(
            "interference",
            0,
            0,
            [
                _hyp(0, 1, "high"),
                _hyp(1, 0, "medium"),
                _hyp(0, 0, "low"),
                _hyp(0, 0, "low"),
                _hyp(0, 0, "low"),
            ],
        ),
        _row(
            "shared-success",
            1,
            1,
            [
                _hyp(1, 1, "high"),
                _hyp(0, 0, "low"),
                _hyp(0, 1, "medium"),
                _hyp(0, 1, "medium"),
                _hyp(0, 1, "medium"),
            ],
        ),
        _row(
            "shared-failure",
            1,
            0,
            [
                _hyp(0, 0, "high"),
                _hyp(0, 0, "low"),
                _hyp(0, 0, "low"),
                _hyp(0, 0, "low"),
                _hyp(0, 0, "low"),
            ],
        ),
    ]
    analysis = _analyze_group(rows)
    cells = analysis["integration_2x2"]
    assert cells["observable_synergy"] == 1
    assert cells["observable_interference"] == 1
    assert cells["shared_success"] == 1
    assert cells["shared_failure"] == 1
    assert analysis["routing"]["best_single_outcome_oracle"]["accuracy"] == 0.5
    assert analysis["routing"]["highest_self_reported_confidence"]["accuracy"] == 0.5
