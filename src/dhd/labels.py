"""Answer extraction and trajectory-value label computation.

These functions define the paper's measurement semantics exactly:

- ``extract_boxed`` extracts the last ``\\boxed{...}`` span, honoring nested braces.
- ``parse_evaluator_verdict`` reads the evaluator's ``Correctness: 0/1`` line.
- Single-draw signal labels compare a full-pool outcome to a matched removal
  outcome; ``trajectory_value_label`` and ``stability_label`` aggregate repeated
  matched blocks with a bootstrap confidence interval.
"""

from __future__ import annotations

import random
import re
from typing import Iterable


def extract_boxed(text: str) -> str:
    """Return the content of the last ``\\boxed{...}`` group, or ``""``."""
    if not text:
        return ""
    raw = str(text)
    marker = r"\boxed{"
    last_match = ""
    start = 0
    while True:
        idx = raw.find(marker, start)
        if idx == -1:
            break
        cursor = idx + len(marker)
        depth = 1
        chunks: list[str] = []
        while cursor < len(raw) and depth > 0:
            char = raw[cursor]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    break
            chunks.append(char)
            cursor += 1
        if depth == 0:
            last_match = "".join(chunks).strip()
        start = idx + 1
    return last_match


def parse_evaluator_verdict(text: str) -> int:
    """Parse the evaluator response into a binary correctness label.

    Recognizes an explicit ``Correctness: 0|1`` line first, then falls back to a
    ``Verdict: PASS|FAIL`` line. Raises ``ValueError`` when neither is present so
    an unparseable verdict is never silently scored as incorrect.
    """
    if not text:
        raise ValueError("empty_evaluator_response")
    body = str(text)
    match = re.search(r"correctness\s*[:=]\s*([01])", body, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    verdict = re.search(r"verdict\s*[:=]\s*(pass|fail)", body, flags=re.IGNORECASE)
    if verdict:
        return 1 if verdict.group(1).lower() == "pass" else 0
    raise ValueError("unparseable_evaluator_verdict")


def normalize_answer(value: str) -> str:
    """Conservative deterministic normalization used for answer agreement."""
    return re.sub(r"\s+", "", str(value or "")).lower()


def _sign(value: float, *, tolerance: float = 1e-12) -> int:
    if value > tolerance:
        return 1
    if value < -tolerance:
        return -1
    return 0


def single_draw_label(full_correct: int, removal_correct: int) -> str:
    """Label one matched full-vs-removal draw.

    ``helpful`` when removing the hypothesis loses a correct answer,
    ``harmful`` when removing it recovers a correct answer, ``neutral`` when the
    outcome is unchanged.
    """
    delta = int(full_correct) - int(removal_correct)
    if delta > 0:
        return "helpful"
    if delta < 0:
        return "harmful"
    return "neutral"


def _bootstrap_mean_ci(
    values: list[float], *, iterations: int, seed: int
) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    if len(values) == 1:
        return (values[0], values[0])
    rng = random.Random(seed)
    means: list[float] = []
    n = len(values)
    for _ in range(iterations):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(0.025 * (len(means) - 1))]
    hi = means[int(0.975 * (len(means) - 1))]
    return (lo, hi)


def trajectory_value_label(
    block_deltas: Iterable[float],
    *,
    iterations: int = 10000,
    seed: int = 20260717,
) -> dict:
    """Aggregate matched full-minus-removal block deltas into a stability label.

    Returns the mean trajectory value, its bootstrap 95% interval, and the
    stability label used by the paper: ``stable_helpful`` when the interval lies
    above zero, ``stable_harmful`` when below zero, ``indeterminate`` otherwise.
    """
    deltas = [float(delta) for delta in block_deltas]
    if not deltas:
        raise ValueError("no_block_deltas")
    mean_value = sum(deltas) / len(deltas)
    ci_low, ci_high = _bootstrap_mean_ci(deltas, iterations=iterations, seed=seed)
    if ci_low > 0:
        label = "stable_helpful"
    elif ci_high < 0:
        label = "stable_harmful"
    else:
        label = "indeterminate"
    aggregate_sign = _sign(mean_value)
    sign_agreement = sum(
        1 for delta in deltas if _sign(delta) == aggregate_sign
    ) / len(deltas)
    return {
        "trajectory_value": mean_value,
        "ci95_low": ci_low,
        "ci95_high": ci_high,
        "observed_sign": aggregate_sign,
        "stability_label": label,
        "replicate_sign_agreement": sign_agreement,
        "n_blocks": len(deltas),
    }
