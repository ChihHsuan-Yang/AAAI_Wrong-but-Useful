from trace_example_report import (
    _message_text,
    _readability_score,
)


def test_message_text_preserves_structured_fields():
    text = _message_text(
        {
            "reasoning_direction": "Use conservation.",
            "key_idea": "Cancel equal terms.",
            "critical_assumption": "The system is closed.",
            "what_to_check": "Check the sign.",
            "proposed_answer": "\\boxed{B}",
        }
    )
    assert "Reasoning direction: Use conservation." in text
    assert "Proposed answer: \\boxed{B}" in text


def test_readability_prefers_compact_complete_record():
    compact = {
        "problem_text": "p" * 300,
        "message_text": "m" * 300,
        "proposed_answer": "A",
        "reduced_answer": "B",
        "full_answer": "A",
        "single_hypothesis_correct": 1,
    }
    long = {**compact, "problem_text": "p" * 8000}
    assert _readability_score(compact) > _readability_score(long)
