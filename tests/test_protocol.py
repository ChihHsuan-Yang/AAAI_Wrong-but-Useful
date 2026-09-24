"""Protocol prompt construction: config load, hypotheses-block rendering, keys."""

from pathlib import Path

from dhd.protocol import (
    load_config,
    render_evaluator_prompt,
    render_hypotheses_block,
    render_integrator_prompt,
)

ROOT = Path(__file__).resolve().parents[1]
PAPER_CONFIG = ROOT / "configs" / "paper" / "dhd_config.yaml"

POOL = [
    {
        "role_name": "Decomposer",
        "proposed_answer": "24",
        "reasoning_direction": "length times width",
        "key_idea": "multiply sides",
        "critical_assumption": "rectangle",
        "what_to_check": "units",
        "confidence": "high",
    },
    {
        "role_name": "Estimator",
        "proposed_answer": "22",
        "reasoning_direction": "order of magnitude",
        "key_idea": "bound the product",
        "critical_assumption": "no scaling",
        "what_to_check": "exactness",
        "confidence": "low",
    },
]


def test_config_loads_integrator_and_evaluator():
    config = load_config(PAPER_CONFIG)
    assert config.agent("integrator").temperature == 0.0
    assert config.agent("evaluator").max_tokens == 4096


def test_hypotheses_block_lists_every_hypothesis():
    block = render_hypotheses_block(POOL)
    assert "Hypothesis 1 (role: Decomposer):" in block
    assert "Hypothesis 2 (role: Estimator):" in block
    # All hypotheses appear; none is filtered or reranked.
    assert block.count("Proposed final answer:") == 2


def test_hypotheses_block_omits_empty_fields():
    sparse = [{"role_name": "R", "proposed_answer": "5"}]
    block = render_hypotheses_block(sparse)
    assert "Proposed final answer: 5" in block
    assert "Key idea:" not in block


def test_integrator_prompt_embeds_task_and_block():
    config = load_config(PAPER_CONFIG)
    messages = render_integrator_prompt(config, "What is 8*3?", POOL)
    system = messages[0]["content"]
    assert "What is 8*3?" in system
    assert "Hypothesis 1 (role: Decomposer):" in system
    assert messages[1]["content"].strip().startswith("Think step by step")


def test_evaluator_prompt_embeds_solution_and_reference():
    config = load_config(PAPER_CONFIG)
    messages = render_evaluator_prompt(config, "problem", "my answer", "gold")
    system = messages[0]["content"]
    assert "my answer" in system
    assert "gold" in system
    # The evaluator must be told not to leak the reference.
    assert "Do not reveal" in system
