#!/usr/bin/env python3
"""Print exactly what a live run would do -- without calling any model.

This is the audit surface for the protocol path. It prints, per role: the
provider, the sanitized endpoint label, the model slot the config declared, the
identifier that resolves for that slot and which environment variable supplied
it, the decoding parameters, the seed behaviour, the config hash, the code
commit, the benchmark, the requested sample ids, the expected role-call count,
and the output path.

It never prints a credential -- only whether one is present and which variable
it came from. It makes no network call, so it is safe to run and paste.

Exit codes
----------
0   the configuration is coherent (it may still be unconfigured; that is said)
2   the configuration contradicts itself, e.g. two roles that declare different
    model slots resolved to one identifier
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from dhd.config import (  # noqa: E402
    ROLES,
    ConfigError,
    bind_models,
    load_run_settings,
    resolved_models_record,
)
from dhd.protocol import load_config  # noqa: E402


def _load_fixture_ids(path: Path, limit: int) -> list[str]:
    ids: list[str] = []
    if not path.exists():
        return ids
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                ids.append(str(json.loads(line).get("problem_id", "")))
            except json.JSONDecodeError:
                continue
    return ids[:limit] if limit > 0 else ids


def _pool_size(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                return len(json.loads(line).get("hypotheses", []))
    return 0


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
    )
    parser.add_argument("--replicates", type=int, default=settings.replicates)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args()

    config = load_config(args.config)
    try:
        bindings = bind_models(config)
    except ConfigError as error:
        print(f"CONFIGURATION ERROR: {error}")
        return 2

    identity = resolved_models_record(bindings, args.config)
    sample_ids = _load_fixture_ids(args.fixture, settings.sample_limit)
    pool_size = _pool_size(args.fixture)
    # One full-pool condition plus one per leave-one-out removal, times
    # replicates, times problems; each condition issues one integrator call and
    # one evaluator call.
    conditions = (1 + pool_size) * args.replicates * max(len(sample_ids), 0)
    expected_calls = {
        "integrator": conditions,
        "evaluator": conditions,
        "total": 2 * conditions,
    }

    report = {
        "protocol_config": str(args.config),
        "config_sha256": identity["config_sha256"],
        "code_commit": identity["code_commit"],
        "benchmark": settings.benchmark,
        "dataset_id": settings.dataset_id,
        "fixture": str(args.fixture),
        "requested_sample_ids": sample_ids,
        "pool_size_k": pool_size,
        "replicates": args.replicates,
        "seed": settings.seed,
        "seed_behavior": (
            "Bootstrap label aggregation is seeded and deterministic. Model "
            "sampling is NOT seeded: the OpenAI-compatible API exposes no seed "
            "parameter here, so generated text is not promised byte-identical."
        ),
        "concurrency": settings.concurrency,
        "max_retries": settings.max_retries,
        "retry_backoff_s": settings.retry_backoff_s,
        "timeout_s": settings.timeout_s,
        "expected_role_calls": expected_calls,
        "output_path": str(args.output_dir / "smoke_results.json"),
        "roles": identity["roles"],
        "distinct_resolved_models": identity["distinct_resolved_models"],
        "unconfigured_roles": sorted(r for r, b in bindings.items() if not b.configured),
        "credentials_printed": False,
    }

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    print("=== DHD dry run (no model call is made) ===")
    print(f"protocol config   : {report['protocol_config']}")
    print(f"config sha256     : {report['config_sha256']}")
    print(f"code commit       : {report['code_commit']}")
    print(f"benchmark         : {report['benchmark']}")
    print(f"dataset id        : {report['dataset_id']}")
    print(f"fixture           : {report['fixture']}")
    print(f"sample ids        : {report['requested_sample_ids'] or '(none found)'}")
    print(f"pool size K       : {report['pool_size_k']}")
    print(f"replicates        : {report['replicates']}")
    print(f"seed              : {report['seed']}")
    print(f"seed behavior     : {report['seed_behavior']}")
    print(f"concurrency       : {report['concurrency']}")
    print(f"retry / timeout   : {report['max_retries']} retries, "
          f"{report['retry_backoff_s']}s backoff, {report['timeout_s']}s timeout")
    print(f"expected calls    : integrator={expected_calls['integrator']} "
          f"evaluator={expected_calls['evaluator']} total={expected_calls['total']}")
    print(f"output path       : {report['output_path']}")
    print("")
    print("--- per-role model identity ---")
    for role in ROLES:
        info = report["roles"].get(role)
        if info is None:
            continue
        print(f"[{role}]")
        print(f"  provider            : {info['provider']}")
        print(f"  endpoint (sanitized): {info['endpoint_label']}"
              f"  (from {info['endpoint_source'] or 'unset'})")
        print(f"  declared model slot : {info['declared_model_slot']}")
        print(f"  resolved model      : {info['resolved_model'] or '(unset)'}"
              f"  (from {info['resolved_model_source'] or 'unset'})")
        print(f"  emitted model       : {info['resolved_model'] or '(unset)'}"
              "  <- this exact string is sent as the request's \"model\" field")
        print(f"  temperature         : {info['temperature']}")
        print(f"  max_tokens          : {info['max_tokens']}")
        print(f"  credential          : "
              f"{'present' if info['api_key_present'] else 'absent'}"
              f" (from {info['api_key_source'] or 'unset'}); value never printed")
    print("")
    if report["unconfigured_roles"]:
        print("NOT RUNNABLE YET -- unconfigured role(s): "
              + ", ".join(report["unconfigured_roles"]))
        print("A live run would SKIP. See .env.example.")
    else:
        print("Configuration is complete; a live run would proceed.")
    print(f"distinct resolved models: {report['distinct_resolved_models'] or '(none)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
