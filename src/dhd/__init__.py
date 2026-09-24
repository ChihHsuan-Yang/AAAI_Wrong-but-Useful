"""Minimal, self-contained runtime for the DHD trajectory-value protocol.

This package is a faithful, dependency-light reimplementation of the measurement
procedure described in the paper. It loads the exact paper prompt templates and
protocol configuration, renders a cached hypothesis pool into the integrator
prompt in the paper's format, calls a generic OpenAI-compatible model API, parses
boxed final answers, runs the evaluator prompt, and computes the correctness and
trajectory-value labels used by the analysis.

It intentionally does not reproduce any facility-specific orchestration, queueing,
retry, or monitoring behavior. Stochastic model generations are not promised to
be byte-identical across model deployments; see ``REPRODUCE.md``.
"""

from .protocol import (
    DHDConfig,
    load_config,
    render_hypotheses_block,
    render_integrator_prompt,
    render_evaluator_prompt,
)
from .labels import (
    extract_boxed,
    trajectory_value_label,
    parse_evaluator_verdict,
)

__all__ = [
    "DHDConfig",
    "load_config",
    "render_hypotheses_block",
    "render_integrator_prompt",
    "render_evaluator_prompt",
    "extract_boxed",
    "trajectory_value_label",
    "parse_evaluator_verdict",
]
