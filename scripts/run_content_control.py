#!/usr/bin/env python3
"""Run the component-masking diagnostic against a configured model API.

This is the standalone replacement for the repository-internal replay runner
that produced ``tab:component_masking``. That runner reached the model through
the authors' agent framework and could not run outside the monorepo; this one
reaches it through ``src/dhd``, so the *mechanism* -- five matched arms per
target slot, word-count-matched masking, interleaved within each replicate --
is runnable anywhere an OpenAI-compatible endpoint is.

It writes ``replay_events.jsonl``, ``RUN_META.json``, and ``validation.json``
in the schema ``analysis/replay/content_control_analyze.py`` consumes, so the
two halves compose:

    python scripts/run_content_control.py --source POOLS --control-manifest M --out-dir RUN
    python analysis/replay/content_control_analyze.py --run_dir RUN

Model identity is resolved per role and the emitted identifier is recorded in
``RUN_META.json``; a mismatch between emitted and configured fails the run.
Without a configured endpoint the script skips with exit code 0.

Scientific outcomes and operational failures are written separately: a timeout,
endpoint error, or unparseable verdict is recorded as an operational failure and
never converted into an incorrect answer.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from dhd.config import (  # noqa: E402
    ConfigError,
    ModelBindingError,
    bind_models,
    load_run_settings,
    resolved_models_record,
)
from dhd.content_control import (  # noqa: E402
    apply_hypothesis_control,
    build_content_control_schedule,
    event_key,
    load_control_targets,
    pool_word_count,
    sha256_text,
)
from dhd.labels import extract_boxed, parse_evaluator_verdict  # noqa: E402
from dhd.model_api import RoleRouter  # noqa: E402
from dhd.protocol import (  # noqa: E402
    load_config,
    render_evaluator_prompt,
    render_integrator_prompt,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"Non-object JSON at {path}:{line_number}")
            rows.append(value)
    return rows


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def main() -> int:
    settings = load_run_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=REPO_ROOT / "configs" / "smoke" / "smoke_config.yaml",
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="JSONL of cached pools: problem_id, problem, reference, hypotheses[5].",
    )
    parser.add_argument(
        "--control-manifest",
        type=Path,
        required=True,
        help="JSONL with one problem_id + hypothesis_index target per row.",
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--replicates", type=int, default=max(settings.replicates, 1))
    parser.add_argument("--seed", type=int, default=settings.seed)
    parser.add_argument("--benchmark", default=settings.benchmark)
    args = parser.parse_args()

    config = load_config(args.config)
    try:
        bindings = bind_models(config)
    except ConfigError as error:
        print(f"CONFIGURATION ERROR: {error}", flush=True)
        print(
            "Nothing was sent. Run `python scripts/dry_run.py` to see the "
            "resolved identity per role.",
            flush=True,
        )
        return 2
    unconfigured = sorted(
        r for r in ("integrator", "evaluator") if not bindings[r].configured
    )
    if unconfigured:
        print(
            "SKIP: model API is not configured for role(s): "
            + ", ".join(unconfigured)
            + ". See .env.example and `python scripts/dry_run.py`.",
            flush=True,
        )
        return 0

    source_rows = _load_jsonl(args.source)
    source_by_id = {str(row["problem_id"]): row for row in source_rows}
    if len(source_by_id) != len(source_rows):
        raise ValueError("Duplicate problem_id in source pools")
    targets = load_control_targets(_load_jsonl(args.control_manifest))
    missing = sorted(set(targets) - set(source_by_id))
    if missing:
        raise ValueError(f"Control targets absent from source; first: {missing[:10]}")

    selected = [source_by_id[pid] for pid in targets]
    schedule = build_content_control_schedule(
        selected, targets=targets, replicates=args.replicates, seed=args.seed + 1
    )

    router = RoleRouter(
        bindings,
        max_retries=settings.max_retries,
        retry_backoff_s=settings.retry_backoff_s,
    )
    identity = resolved_models_record(bindings, args.config)

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    events_path = out_dir / "replay_events.jsonl"
    errors_path = out_dir / "errors.jsonl"

    run_contract = {
        "schema_version": "dhd_replay_stability_v1",
        "benchmark": args.benchmark,
        "replicates": args.replicates,
        "seed": args.seed,
        "control_manifest": str(args.control_manifest),
        "config_sha256": identity["config_sha256"],
        "schedule_policy": "problem_blocked_replicate_interleaved_content_controls",
        "selected_problem_ids": sorted(targets),
        "actor_model_id": bindings["integrator"].model,
        "evaluator_model_id": bindings["evaluator"].model,
    }
    run_contract_hash = sha256_text(run_contract)

    valid = 0
    failed = 0
    with events_path.open("w", encoding="utf-8") as events, errors_path.open(
        "w", encoding="utf-8"
    ) as errors:
        for event in schedule:
            source = source_by_id[event["problem_id"]]
            hypotheses = list(source["hypotheses"])
            pool = apply_hypothesis_control(
                hypotheses,
                target_h_index=int(event["target_h_index"]),
                condition=str(event["condition"]),
            )
            started = _utc_now()
            try:
                messages = render_integrator_prompt(config, source["problem"], pool)
                answer_text = router.generate("integrator", messages)
                if not str(answer_text).strip():
                    raise RuntimeError("integrator_returned_empty_output")
                verdict_messages = render_evaluator_prompt(
                    config,
                    source["problem"],
                    answer_text,
                    source.get("reference") or source.get("gold") or "",
                )
                verdict_text = router.generate("evaluator", verdict_messages)
                correct = parse_evaluator_verdict(verdict_text)
            except Exception as error:  # noqa: BLE001 - operational, not scientific
                failed += 1
                errors.write(
                    json.dumps(
                        {
                            **event,
                            "valid": False,
                            "run_contract_hash": run_contract_hash,
                            "failure": f"{type(error).__name__}:{error}",
                            "started_at_utc": started,
                            "finished_at_utc": _utc_now(),
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )
                continue
            target = hypotheses[int(event["target_h_index"])]
            record = {
                **event,
                "schema_version": "dhd_replay_stability_v1",
                "valid": True,
                "benchmark": args.benchmark,
                "run_contract_hash": run_contract_hash,
                "actor_model_id": bindings["integrator"].model,
                "evaluator_model_id": bindings["evaluator"].model,
                "event_id": sha256_text(
                    {"run": run_contract_hash, "key": event_key(event)}
                )[:24],
                "condition_input_hash": sha256_text(
                    {"problem": source["problem"], "hypotheses": pool}
                ),
                "proposal_correctness": target.get("proposal_correctness"),
                "target_original_word_count": pool_word_count([target]),
                "condition_pool_word_count": pool_word_count(pool),
                "answer_text": answer_text,
                "answer_boxed": extract_boxed(answer_text),
                "correct": correct,
                "started_at_utc": started,
                "finished_at_utc": _utc_now(),
            }
            events.write(json.dumps(record, sort_keys=True) + "\n")
            valid += 1

    try:
        router.verify_emitted_matches_configured()
        emitted_ok = True
        emitted_error = ""
    except ModelBindingError as error:
        emitted_ok = False
        emitted_error = str(error)

    _write_json(
        out_dir / "RUN_META.json",
        {
            **run_contract,
            "run_contract_hash": run_contract_hash,
            "expected_events": len(schedule),
            "valid_events": valid,
            "error_events": failed,
            "model_identity": {
                **identity,
                "emitted_models_by_role": router.emitted_models_by_role(),
                "emitted_matches_configured": emitted_ok,
            },
            "finished_at_utc": _utc_now(),
        },
    )
    _write_json(
        out_dir / "validation.json",
        {
            "schema_version": "dhd_replay_stability_v1",
            "run_contract_hash": run_contract_hash,
            "expected_events": len(schedule),
            "valid_unique_events": valid,
            "error_rows_total": failed,
            "complete": valid == len(schedule),
            "validated_at_utc": _utc_now(),
        },
    )
    print(
        f"[content-control] events={valid}/{len(schedule)} failures={failed} "
        f"-> {out_dir}",
        flush=True,
    )
    if not emitted_ok:
        print(f"FAIL: {emitted_error}", flush=True)
        return 1
    return 0 if valid == len(schedule) else 3


if __name__ == "__main__":
    raise SystemExit(main())
