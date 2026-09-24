"""DHD protocol prompt construction from the exact paper configuration.

The prompt templates and per-role model parameters live in ``configs/paper`` and
are the byte-exact text used in the paper. This module loads that configuration
and renders the integrator and evaluator inputs from a cached hypothesis pool in
the paper's format. It performs no model calls itself; see ``replay.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import Any

import yaml


# The ordered fields rendered into the integrator's hypotheses block. This
# mirrors the paper's hypothesizer response format exactly.
HYPOTHESIS_FIELDS: list[tuple[str, str]] = [
    ("proposed_answer", "Proposed final answer"),
    ("reasoning_direction", "Reasoning direction"),
    ("key_idea", "Key idea"),
    ("critical_assumption", "Critical assumption"),
    ("what_to_check", "What another solver should check"),
    ("confidence", "Confidence / uncertainty"),
]

# Neutral, length-controlled preamble shown before every hypothesis in the
# score-free ("none") exposure condition used by the live protocol.
PLACEBO_PREAMBLE = (
    "[No score estimates are available for the hypothesis below. "
    "Use your own judgement to weigh it. Do not blindly copy any proposed "
    "answer. Verify before using.]"
)


@dataclass(frozen=True)
class AgentSpec:
    name: str
    agent_type: str
    prepend_prompt_template: str
    append_prompt_template: str
    model: str
    temperature: float
    max_tokens: int


@dataclass(frozen=True)
class DHDConfig:
    name: str
    agents: dict[str, AgentSpec]

    def agent(self, agent_type: str) -> AgentSpec:
        for spec in self.agents.values():
            if spec.agent_type == agent_type:
                return spec
        raise KeyError(agent_type)


def load_config(config_path: str | Path) -> DHDConfig:
    """Load a DHD protocol config YAML into typed prompt/model specs."""
    raw = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    agents: dict[str, AgentSpec] = {}
    for entry in raw.get("agents", []):
        llm = entry.get("llm", {})
        spec = AgentSpec(
            name=str(entry.get("name", "")),
            agent_type=str(entry.get("agent_type", "")),
            prepend_prompt_template=str(entry.get("prepend_prompt_template", "")),
            append_prompt_template=str(entry.get("append_prompt_template", "")),
            model=str(llm.get("model", "")),
            temperature=float(llm.get("temperature", 0.0)),
            max_tokens=int(llm.get("max_tokens", 4096)),
        )
        agents[spec.name or spec.agent_type] = spec
    return DHDConfig(name=str(raw.get("name", "")), agents=agents)


def render_hypotheses_block(hypotheses: list[dict[str, Any]]) -> str:
    """Render the K hypotheses into the integrator-visible block.

    All hypotheses always appear; none is filtered, gated, reranked, or
    discarded. The score-free placebo preamble precedes each hypothesis so the
    live exposure condition differs from a scored condition only in text content.
    """
    rendered: list[str] = []
    for idx, hyp in enumerate(hypotheses):
        role_name = hyp.get("role_name") or hyp.get("role") or f"Agent {idx + 1}"
        body_lines = [f"Hypothesis {idx + 1} (role: {role_name}):"]
        for key, label in HYPOTHESIS_FIELDS:
            value = str(hyp.get(key, "") or "").strip()
            if value:
                body_lines.append(f"{label}: {value}")
        entry = PLACEBO_PREAMBLE + "\n" + "\n".join(body_lines)
        rendered.append(entry.strip())
    return "\n\n".join(rendered)


def _fill(template: str, mapping: dict[str, str]) -> str:
    return Template(template).safe_substitute(mapping)


def render_integrator_prompt(
    config: DHDConfig,
    task_description: str,
    hypotheses: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Build the integrator chat messages for a cached hypothesis pool."""
    spec = config.agent("integrator")
    block = render_hypotheses_block(hypotheses)
    prepend = _fill(
        spec.prepend_prompt_template,
        {"task_description": task_description, "hypotheses_block": block},
    )
    append = _fill(spec.append_prompt_template, {})
    return [
        {"role": "system", "content": prepend},
        {"role": "user", "content": append},
    ]


def render_evaluator_prompt(
    config: DHDConfig,
    task_description: str,
    solution: str,
    reference: str,
) -> list[dict[str, str]]:
    """Build the evaluator chat messages for a submitted final answer."""
    spec = config.agent("evaluator")
    prepend = _fill(
        spec.prepend_prompt_template,
        {
            "task_description": task_description,
            "solution": solution,
            "result": reference,
        },
    )
    append = _fill(spec.append_prompt_template, {})
    return [
        {"role": "system", "content": prepend},
        {"role": "user", "content": append},
    ]
