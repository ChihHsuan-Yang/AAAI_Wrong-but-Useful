"""Replay orchestration: key construction, missing cells, aggregation, failures."""

from pathlib import Path

from dhd.protocol import load_config
from dhd.replay import replay_problem, signal_labels_from_result

ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_config(ROOT / "configs" / "smoke" / "smoke_config.yaml")

POOL = [
    {"role_name": f"R{i}", "proposed_answer": str(i), "key_idea": f"idea {i}"}
    for i in range(5)
]


def _scripted_generator(integrator_correct_full, integrator_correct_removal):
    """Return a generate() that yields deterministic integrator+evaluator text.

    The integrator message is answered with a boxed answer; the evaluator message
    is answered with a Correctness line chosen by which condition is running. We
    detect the evaluator turn by the presence of 'MAS final submission'.
    """
    state = {"last_pool_size": None}

    def generate(messages, temperature, max_tokens):
        system = messages[0]["content"]
        if "MAS final submission" in system:
            # Evaluator turn: full pool has 5 lines, removal has 4.
            correct = (
                integrator_correct_full
                if state["last_pool_size"] == 5
                else integrator_correct_removal
            )
            return f"Verdict: {'PASS' if correct else 'FAIL'}\nCorrectness: {correct}"
        # Integrator turn: count hypotheses to know the condition.
        state["last_pool_size"] = system.count("Proposed final answer:")
        return r"\boxed{answer}"

    return generate


def test_replay_produces_full_plus_loo_conditions():
    result = replay_problem(
        CONFIG, _scripted_generator(1, 0), "problem", "gold", POOL, replicates=1
    )
    conditions = [o.condition for o in result.scientific]
    assert conditions.count("full") == 1
    assert conditions.count("removal") == 5
    assert result.operational_failures == []


def test_signal_labels_all_helpful_when_removal_breaks_answer():
    # Full pool correct, every removal wrong -> each hypothesis is helpful.
    result = replay_problem(
        CONFIG, _scripted_generator(1, 0), "problem", "gold", POOL, replicates=3
    )
    labels = signal_labels_from_result(result)
    assert len(labels) == 5
    for label in labels:
        assert label["stability_label"] == "stable_helpful"
        assert all(sd == "helpful" for sd in label["single_draw_labels"])


def test_signal_labels_all_harmful_when_removal_fixes_answer():
    result = replay_problem(
        CONFIG, _scripted_generator(0, 1), "problem", "gold", POOL, replicates=3
    )
    labels = signal_labels_from_result(result)
    for label in labels:
        assert label["stability_label"] == "stable_harmful"


def test_operational_failure_is_not_scored_as_wrong():
    def failing_generate(messages, temperature, max_tokens):
        raise RuntimeError("model_api_call_failed:Timeout")

    result = replay_problem(
        CONFIG, failing_generate, "problem", "gold", POOL, replicates=1
    )
    # No scientific outcomes; failures recorded separately.
    assert result.scientific == []
    assert len(result.operational_failures) == 6
    assert signal_labels_from_result(result) == []


def test_missing_full_block_yields_no_labels():
    def only_removal_fails(messages, temperature, max_tokens):
        system = messages[0]["content"]
        if "MAS final submission" in system:
            return "Correctness: 1"
        if system.count("Proposed final answer:") == 5:
            raise RuntimeError("model_api_call_failed:full_pool_only")
        return r"\boxed{a}"

    result = replay_problem(
        CONFIG, only_removal_fails, "problem", "gold", POOL, replicates=1
    )
    # Full failed operationally; removals succeeded but have no matched full.
    assert all(o.condition == "removal" for o in result.scientific)
    assert signal_labels_from_result(result) == []
