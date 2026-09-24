"""Matched full-pool vs leave-one-out replay over a cached hypothesis pool.

This is the measurement unit of the paper: a cached problem, its ordered
hypothesis pool, the actor (integrator) and evaluator prompts, and a fixed prompt
contract. The integrator is re-run under the full pool and under each single
leave-one-out removal; the evaluator scores each output; single-draw and repeated
trajectory-value labels follow from those scored outcomes.

Scientific outcomes and operational failures are kept separate: a model API,
parse, or verdict failure is recorded as an operational failure and never
converted into an incorrect scientific answer.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable

from .labels import (
    extract_boxed,
    parse_evaluator_verdict,
    single_draw_label,
    trajectory_value_label,
)
from .protocol import (
    DHDConfig,
    render_evaluator_prompt,
    render_integrator_prompt,
)

# A generation function maps chat messages + sampling params to response text.
# It may additionally accept a ``role`` argument ("integrator" / "evaluator").
# When it does, this module passes the role so the caller can send each role's
# own resolved model identifier; when it does not, the three-argument form is
# used unchanged. This is how per-role model identity reaches the wire without
# breaking generators written against the original signature.
GenerateFn = Callable[..., str]


def _accepts_role(generate: GenerateFn) -> bool:
    try:
        signature = inspect.signature(generate)
    except (TypeError, ValueError):
        return False
    parameters = signature.parameters
    if any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    ):
        return True
    return "role" in parameters


def _call(
    generate: GenerateFn,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    role: str,
) -> str:
    if _accepts_role(generate):
        return generate(messages, temperature, max_tokens, role=role)
    return generate(messages, temperature, max_tokens)


@dataclass
class ReplayOutcome:
    condition: str
    removed_h_index: int | None
    answer_text: str
    answer_boxed: str
    correct: int


@dataclass
class ReplayResult:
    problem_id: str
    scientific: list[ReplayOutcome] = field(default_factory=list)
    operational_failures: list[dict[str, Any]] = field(default_factory=list)


def _run_condition(
    config: DHDConfig,
    generate: GenerateFn,
    problem: str,
    reference: str,
    hypotheses: list[dict[str, Any]],
    *,
    condition: str,
    removed_h_index: int | None,
) -> ReplayOutcome:
    integrator = config.agent("integrator")
    evaluator = config.agent("evaluator")

    integrator_messages = render_integrator_prompt(config, problem, hypotheses)
    answer_text = _call(
        generate,
        integrator_messages,
        integrator.temperature,
        integrator.max_tokens,
        "integrator",
    )
    answer_boxed = extract_boxed(answer_text)

    evaluator_messages = render_evaluator_prompt(
        config, problem, answer_text, reference
    )
    verdict_text = _call(
        generate,
        evaluator_messages,
        evaluator.temperature,
        evaluator.max_tokens,
        "evaluator",
    )
    correct = parse_evaluator_verdict(verdict_text)
    return ReplayOutcome(
        condition=condition,
        removed_h_index=removed_h_index,
        answer_text=answer_text,
        answer_boxed=answer_boxed,
        correct=correct,
    )


def replay_problem(
    config: DHDConfig,
    generate: GenerateFn,
    problem: str,
    reference: str,
    hypotheses: list[dict[str, Any]],
    *,
    problem_id: str = "",
    replicates: int = 1,
    include_loo: bool = True,
) -> ReplayResult:
    """Run matched full-pool and leave-one-out conditions for one problem.

    For each replicate, the full pool is scored once and each single-hypothesis
    removal is scored once, so single-draw and repeated labels can be computed
    downstream. Any failure in a condition is captured as an operational failure
    and does not abort the remaining conditions.
    """
    result = ReplayResult(problem_id=problem_id)
    k = len(hypotheses)

    for replicate_id in range(replicates):
        conditions: list[tuple[str, int | None, list[dict[str, Any]]]] = [
            ("full", None, list(hypotheses))
        ]
        if include_loo:
            for removed in range(k):
                pool = [h for i, h in enumerate(hypotheses) if i != removed]
                conditions.append(("removal", removed, pool))

        for condition, removed_h_index, pool in conditions:
            try:
                outcome = _run_condition(
                    config,
                    generate,
                    problem,
                    reference,
                    pool,
                    condition=condition,
                    removed_h_index=removed_h_index,
                )
                result.scientific.append(outcome)
            except Exception as error:  # noqa: BLE001 - operational, not scientific
                result.operational_failures.append(
                    {
                        "replicate_id": replicate_id,
                        "condition": condition,
                        "removed_h_index": removed_h_index,
                        "failure": f"{type(error).__name__}:{error}",
                    }
                )
    return result


def signal_labels_from_result(result: ReplayResult) -> list[dict[str, Any]]:
    """Compute per-hypothesis single-draw and repeated trajectory-value labels.

    Each removal is compared to the matched full-pool outcome from the same
    replicate. Repeated blocks are aggregated with :func:`trajectory_value_label`.
    """
    fulls = [o for o in result.scientific if o.condition == "full"]
    removals = [o for o in result.scientific if o.condition == "removal"]
    if not fulls:
        return []
    # Matched pairing uses replicate order; the full outcomes and removal groups
    # are emitted in replicate-major order by replay_problem.
    n_replicates = len(fulls)
    labels: list[dict[str, Any]] = []
    removed_indices = sorted({o.removed_h_index for o in removals})
    for removed in removed_indices:
        block_deltas: list[float] = []
        single_draws: list[str] = []
        matched = [o for o in removals if o.removed_h_index == removed]
        for replicate_id in range(min(n_replicates, len(matched))):
            full_correct = fulls[replicate_id].correct
            removal_correct = matched[replicate_id].correct
            block_deltas.append(full_correct - removal_correct)
            single_draws.append(single_draw_label(full_correct, removal_correct))
        aggregate = trajectory_value_label(block_deltas)
        labels.append(
            {
                "hypothesis_index": removed,
                "single_draw_labels": single_draws,
                **aggregate,
            }
        )
    return labels
