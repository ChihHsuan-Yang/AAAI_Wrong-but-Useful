"""Label computation: boxed extraction, verdict parsing, trajectory-value labels."""

import pytest

from dhd.labels import (
    extract_boxed,
    parse_evaluator_verdict,
    single_draw_label,
    trajectory_value_label,
)


def test_extract_boxed_returns_last_nested_group():
    assert extract_boxed(r"first \boxed{1} then \boxed{\frac{a}{b}}") == r"\frac{a}{b}"
    assert extract_boxed("no box here") == ""
    assert extract_boxed("") == ""


def test_extract_boxed_handles_nested_braces():
    assert extract_boxed(r"\boxed{x = \{1, 2\}}") == r"x = \{1, 2\}"


def test_parse_evaluator_verdict_prefers_correctness_line():
    assert parse_evaluator_verdict("Verdict: PASS\nCorrectness: 1") == 1
    assert parse_evaluator_verdict("Verdict: FAIL\nCorrectness: 0") == 0


def test_parse_evaluator_verdict_falls_back_to_verdict():
    assert parse_evaluator_verdict("Verdict: PASS") == 1
    assert parse_evaluator_verdict("Verdict: FAIL") == 0


def test_parse_evaluator_verdict_raises_when_unparseable():
    with pytest.raises(ValueError):
        parse_evaluator_verdict("no verdict at all")
    with pytest.raises(ValueError):
        parse_evaluator_verdict("")


def test_single_draw_label_directions():
    # Removal loses a correct answer -> the hypothesis was helpful.
    assert single_draw_label(full_correct=1, removal_correct=0) == "helpful"
    # Removal recovers a correct answer -> the hypothesis was harmful.
    assert single_draw_label(full_correct=0, removal_correct=1) == "harmful"
    assert single_draw_label(full_correct=1, removal_correct=1) == "neutral"
    assert single_draw_label(full_correct=0, removal_correct=0) == "neutral"


def test_trajectory_value_label_stable_helpful():
    result = trajectory_value_label([1.0, 1.0, 1.0], iterations=500, seed=1)
    assert result["stability_label"] == "stable_helpful"
    assert result["trajectory_value"] == pytest.approx(1.0)
    assert result["observed_sign"] == 1


def test_trajectory_value_label_stable_harmful():
    result = trajectory_value_label([-1.0, -1.0, -1.0], iterations=500, seed=1)
    assert result["stability_label"] == "stable_harmful"
    assert result["observed_sign"] == -1


def test_trajectory_value_label_indeterminate_when_ci_spans_zero():
    result = trajectory_value_label([1.0, -1.0, 0.0, 1.0, -1.0], iterations=500, seed=1)
    assert result["stability_label"] == "indeterminate"


def test_trajectory_value_label_requires_blocks():
    with pytest.raises(ValueError):
        trajectory_value_label([])
