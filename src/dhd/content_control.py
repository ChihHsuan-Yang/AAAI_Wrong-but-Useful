"""Content-preserving intervention arms for the component-masking diagnostic.

Whole-message removal cannot say *which part* of a message carries value. These
arms separate a message's proposed answer from its reasoning while holding the
slot position and the approximate word count fixed, which is what stops the
contrast from being a length or a position artifact.

The five arms per target slot are:

``original_full``
    the pool unchanged -- the matched reference for every other arm;
``removal``
    the target hypothesis deleted from the pool;
``semantic_mask``
    every renderable field of the target replaced by length-matched filler --
    the slot is still occupied, but carries no content;
``answer_masked``
    only the proposed-answer fields replaced;
``reasoning_masked``
    only the reasoning fields replaced.

Effects are read as ``original_full`` correctness minus the intervention's
correctness within the same replicate block, so every comparison is matched.

This module is pure standard library and has no runtime dependency on any
orchestration framework, so the mechanism is testable and runnable on its own.
"""

from __future__ import annotations

import hashlib
import json
import random
from typing import Any, Iterable

#: Fields rendered into the integrator prompt for each hypothesis.
RENDER_KEYS: tuple[str, ...] = (
    "role",
    "proposed_answer",
    "reasoning_direction",
    "key_idea",
    "critical_assumption",
    "what_to_check",
    "confidence",
)

#: Renderable fields excluding the role label.
CONTENT_RENDER_KEYS: tuple[str, ...] = tuple(k for k in RENDER_KEYS if k != "role")

#: The fields that carry reasoning rather than a proposed answer.
REASONING_RENDER_KEYS: tuple[str, ...] = (
    "reasoning_direction",
    "key_idea",
    "critical_assumption",
    "what_to_check",
)

#: The five matched arms, in canonical order.
CONTENT_CONTROL_CONDITIONS: tuple[str, ...] = (
    "original_full",
    "removal",
    "semantic_mask",
    "answer_masked",
    "reasoning_masked",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_text(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def mask_like(value: Any) -> str:
    """Deterministic neutral filler with a matched word count.

    ``"derive the expression"`` becomes ``"masked masked masked"``. Matching the
    word count is the length control the diagnostic depends on: without it, a
    masked arm would differ from the original in length as well as in content.
    """
    words = str(value or "").split()
    return " ".join("masked" for _ in words)


def apply_hypothesis_control(
    hypotheses: list[dict[str, Any]],
    *,
    target_h_index: int,
    condition: str,
) -> list[dict[str, Any]]:
    """Apply one content-preserving intervention to a fixed hypothesis slot."""
    if condition not in CONTENT_CONTROL_CONDITIONS:
        raise ValueError(f"Unknown content-control condition: {condition}")
    if target_h_index < 0 or target_h_index >= len(hypotheses):
        raise ValueError(
            f"Target hypothesis index {target_h_index} outside pool of {len(hypotheses)}"
        )
    controlled = [dict(hypothesis) for hypothesis in hypotheses]
    if condition == "original_full":
        return controlled
    if condition == "removal":
        return [
            hypothesis
            for index, hypothesis in enumerate(controlled)
            if index != target_h_index
        ]

    target = controlled[target_h_index]
    if condition == "semantic_mask":
        target["role_name"] = mask_like(target.get("role_name")) or "masked"
        target["reasoning_lens"] = mask_like(target.get("reasoning_lens"))
        for key in CONTENT_RENDER_KEYS:
            target[key] = mask_like(target.get(key))
        target["proposed_answer_extracted"] = mask_like(
            target.get("proposed_answer_extracted")
        )
    elif condition == "answer_masked":
        target["proposed_answer"] = mask_like(target.get("proposed_answer"))
        target["proposed_answer_extracted"] = mask_like(
            target.get("proposed_answer_extracted")
        )
    elif condition == "reasoning_masked":
        for key in REASONING_RENDER_KEYS:
            target[key] = mask_like(target.get(key))
    return controlled


def build_content_control_schedule(
    rows: Iterable[dict[str, Any]],
    *,
    targets: dict[str, int],
    replicates: int,
    seed: int,
) -> list[dict[str, Any]]:
    """Interleave the five matched arms within each problem replicate.

    Interleaving matters: if each arm ran in its own long phase, endpoint drift
    over the phases would be confounded with the arm. Shuffling the condition
    order per replicate puts the matched comparison inside one local time block.
    """
    source_rows = list(rows)
    rng = random.Random(seed)
    rng.shuffle(source_rows)
    schedule: list[dict[str, Any]] = []
    for source in source_rows:
        problem_id = str(source["problem_id"])
        target_h_index = targets[problem_id]
        for replicate_id in range(replicates):
            conditions = list(CONTENT_CONTROL_CONDITIONS)
            rng.shuffle(conditions)
            for condition in conditions:
                schedule.append(
                    {
                        "problem_id": problem_id,
                        "K": 5,
                        "condition": condition,
                        "arm": "content_control",
                        "removed_h_index": target_h_index,
                        "target_h_index": target_h_index,
                        "replicate_id": replicate_id,
                    }
                )
    return schedule


def event_key(event: dict[str, Any]) -> str:
    return "|".join(
        str(event.get(key, ""))
        for key in ("problem_id", "K", "condition", "arm", "removed_h_index", "replicate_id")
    )


def load_control_targets(rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    """One target hypothesis index per problem; duplicates are an error."""
    targets: dict[str, int] = {}
    for row in rows:
        problem_id = str(row.get("problem_id") or "").strip()
        if not problem_id:
            raise ValueError(f"Control manifest row lacks problem_id: {row}")
        raw_index = row.get("hypothesis_index", row.get("target_h_index"))
        try:
            hypothesis_index = int(raw_index)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Control manifest has invalid hypothesis index for {problem_id}: {raw_index}"
            ) from exc
        if hypothesis_index < 0 or hypothesis_index > 4:
            raise ValueError(
                f"Control target for {problem_id} must be in [0,4], got {hypothesis_index}"
            )
        if problem_id in targets:
            raise ValueError(f"Control manifest repeats problem_id {problem_id}")
        targets[problem_id] = hypothesis_index
    if not targets:
        raise ValueError("Control manifest is empty")
    return targets


def pool_word_count(hypotheses: list[dict[str, Any]]) -> int:
    """Total rendered word count of a pool -- the length control's observable."""
    return sum(
        len(str(hypothesis.get(key, "")).split())
        for hypothesis in hypotheses
        for key in ("role_name", *CONTENT_RENDER_KEYS)
    )


__all__ = [
    "CONTENT_CONTROL_CONDITIONS",
    "CONTENT_RENDER_KEYS",
    "REASONING_RENDER_KEYS",
    "RENDER_KEYS",
    "apply_hypothesis_control",
    "build_content_control_schedule",
    "canonical_json",
    "event_key",
    "load_control_targets",
    "mask_like",
    "pool_word_count",
    "sha256_text",
]
