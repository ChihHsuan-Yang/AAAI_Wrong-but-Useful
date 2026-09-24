#!/usr/bin/env python3
"""Fixture-based end-to-end smoke test for the DHD protocol runtime.

Reads a tiny cached hypothesis pool from ``data/fixtures/smoke_pool.jsonl`` and
runs the full-pool and leave-one-out integration conditions through an
OpenAI-compatible model API, then scores each output with the evaluator prompt
and reports single-draw and repeated trajectory-value labels.

Model identity is resolved **per role** by ``src/dhd/config.py``: the integrator
and the evaluator each get their own endpoint, credential, and model identifier.
The identifier actually sent on the wire is recorded in ``smoke_results.json``
under ``model_identity``, and the run aborts if what was emitted differs from
what was configured.

Configuration comes only from environment variables (see ``.env.example``).
When no endpoint is configured the test skips gracefully with exit code 0, so
the repository can be inspected and packaged without credentials. Credentials
and authorization headers are never printed. Outputs are written only under the
chosen output directory.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from dhd.config import (  # noqa: E402
    ConfigError,
    ModelBindingError,
    bind_models,
    load_run_settings,
    resolved_models_record,
)
from dhd.model_api import RoleRouter  # noqa: E402
from dhd.protocol import load_config  # noqa: E402
from dhd.replay import replay_problem, signal_labels_from_result  # noqa: E402


def _load_pool(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> int:
    settings = load_run_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=REPO_ROOT / "configs" / "smoke" / "smoke_config.yaml",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=REPO_ROOT / "data" / "fixtures" / "smoke_pool.jsonl",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=settings.output_dir / "smoke_output",
        help="Directory for run outputs (default: $DHD_OUTPUT_DIR/smoke_output).",
    )
    parser.add_argument("--replicates", type=int, default=settings.replicates)
    args = parser.parse_args()

    config = load_config(args.config)
    # bind_models raises if the resolved identities contradict the config, e.g.
    # if the integrator and the evaluator collapse onto one model identifier.
    # Report that as a clear message and exit 2, not as a traceback: it is a
    # configuration problem the reader can fix, not a crash.
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

    unconfigured = sorted(r for r in ("integrator", "evaluator") if not bindings[r].configured)
    if unconfigured:
        print(
            "SKIP: model API is not configured for role(s): "
            + ", ".join(unconfigured)
            + ". Set DHD_ACTOR_BASE_URL/DHD_ACTOR_MODEL and "
            "DHD_EVALUATOR_BASE_URL/DHD_EVALUATOR_MODEL (or the legacy "
            "MODEL_API_BASE/MODEL_API_MODEL pair) to run the protocol smoke "
            "test. See .env.example and `python scripts/dry_run.py`.",
            flush=True,
        )
        return 0

    router = RoleRouter(
        bindings,
        max_retries=settings.max_retries,
        retry_backoff_s=settings.retry_backoff_s,
    )
    identity = resolved_models_record(bindings, args.config)
    for role in ("integrator", "evaluator"):
        info = identity["roles"][role]
        print(
            f"[smoke] {role}: model={info['resolved_model']} "
            f"endpoint={info['endpoint_label']} "
            f"temperature={info['temperature']} max_tokens={info['max_tokens']}",
            flush=True,
        )

    pool = _load_pool(args.fixture)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    def generate(messages, temperature, max_tokens, role="integrator"):
        return router.generate(role, messages, temperature, max_tokens)

    all_records = []
    for row in pool:
        result = replay_problem(
            config,
            generate,
            row["problem"],
            row.get("reference") or row.get("gold") or "",
            row["hypotheses"],
            problem_id=row["problem_id"],
            replicates=args.replicates,
            include_loo=True,
        )
        labels = signal_labels_from_result(result)
        record = {
            "problem_id": row["problem_id"],
            "n_scientific": len(result.scientific),
            "n_operational_failures": len(result.operational_failures),
            "signal_labels": labels,
        }
        all_records.append(record)
        print(
            f"[smoke] {row['problem_id']}: "
            f"scientific={record['n_scientific']} "
            f"failures={record['n_operational_failures']} "
            f"signals={len(labels)}",
            flush=True,
        )

    # Audit what actually went on the wire, not what we intended to send.
    emitted = router.emitted_models_by_role()
    try:
        router.verify_emitted_matches_configured()
        emitted_matches_configured = True
    except ModelBindingError as error:
        emitted_matches_configured = False
        emitted_error = str(error)

    payload = {
        "model_identity": {
            **identity,
            "emitted_models_by_role": emitted,
            "emitted_matches_configured": emitted_matches_configured,
        },
        "run_settings": settings.public_dict(),
        "records": all_records,
    }
    out_path = output_dir / "smoke_results.json"
    out_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"[smoke] wrote {out_path}", flush=True)

    if not emitted_matches_configured:
        print(f"FAIL: {emitted_error}", flush=True)
        return 1
    print(
        "[smoke] emitted model identity matches configuration for role(s): "
        + ", ".join(sorted(emitted)),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
