"""Single configuration layer for the DHD runtime.

Everything the runtime needs -- which endpoint to call, with which credential,
under which model identifier, with which decoding parameters -- is resolved
here and nowhere else. Two rules are structural, not stylistic:

1. **No author endpoint is ever a default.** Every connection value defaults to
   the empty string. An unconfigured run skips; it never silently points at
   somebody else's server or proxy.
2. **Model identity is resolved per role.** The protocol config declares a
   *model slot* per agent (``recruiter``, ``hypothesizer``, ``integrator``,
   ``evaluator``). This module binds each slot to a concrete model identifier
   and refuses bindings that contradict what the config declared.

Rule 2 exists because of a measured defect in the published artifact: a single
``MODEL_API_MODEL`` was sent for *both* the integrator and the evaluator while
the YAML declared two different slots. The paper's design requires a separate
evaluator ("Both gpt-oss-120b and gemma-4-31B-it model families use a separate
gpt-oss-120b evaluator"), so that collapse makes the secondary-actor arm
impossible to enact. :func:`bind_models` fails closed on it.

Environment variables (most specific wins)
------------------------------------------

Per role::

    DHD_RECRUITER_BASE_URL / _API_KEY / _MODEL
    DHD_HYPOTHESIZER_BASE_URL / _API_KEY / _MODEL
    DHD_INTEGRATOR_BASE_URL / _API_KEY / _MODEL
    DHD_EVALUATOR_BASE_URL / _API_KEY / _MODEL

Per lane -- ``DHD_ACTOR_*`` covers recruiter + hypothesizer + integrator, which
is the paper's actor family::

    DHD_ACTOR_BASE_URL / DHD_ACTOR_API_KEY / DHD_ACTOR_MODEL

Global fallback -- the names the published artifact already used, kept working::

    MODEL_API_BASE / MODEL_API_KEY / MODEL_API_MODEL

Assertions (optional, recommended in scripted runs). If set, the resolved
identifier for that role must match exactly or the run aborts::

    DHD_EXPECT_RECRUITER_MODEL / _HYPOTHESIZER_ / _INTEGRATOR_ / _EVALUATOR_

Other settings::

    DHD_DATASET_ID, DHD_DATA_ROOT, DHD_CACHE_DIR, DHD_OUTPUT_DIR,
    DHD_BENCHMARK, DHD_SAMPLE_LIMIT, DHD_REPLICATES, DHD_SEED,
    DHD_CONCURRENCY, DHD_MAX_RETRIES, DHD_RETRY_BACKOFF_S, DHD_TIMEOUT_S,
    DHD_TEMPERATURE_OVERRIDE, DHD_MAX_TOKENS_OVERRIDE,
    DHD_ANALYSIS_INPUT_DIR, DHD_ANALYSIS_OUTPUT_DIR
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

from .protocol import DHDConfig, load_config

#: The four protocol roles, in call order.
ROLES: tuple[str, ...] = ("recruiter", "hypothesizer", "integrator", "evaluator")

#: Roles filled by the *actor* model family. The evaluator is deliberately not
#: in this set: the paper scores every actor family with a separate evaluator.
ACTOR_ROLES: frozenset[str] = frozenset({"recruiter", "hypothesizer", "integrator"})

#: ``agent_type`` strings the shipped configs use for each role.
_AGENT_TYPE_BY_ROLE: dict[str, tuple[str, ...]] = {
    "recruiter": ("role_assigner", "recruiter"),
    "hypothesizer": ("hypothesizer",),
    "integrator": ("integrator",),
    "evaluator": ("evaluator",),
}

#: Repository-relative defaults. Nothing here escapes the checkout.
REPO_ROOT: Path = Path(__file__).resolve().parents[2]


class ConfigError(RuntimeError):
    """Raised when the environment/config combination is not runnable."""


class ModelBindingError(ConfigError):
    """Raised when resolved model identities contradict the protocol config.

    This is the guard ported from the repository's replay runner, which raised
    on ``declared != loaded``. Here it additionally enforces the *structure* the
    config declares: two roles that declare different model slots must not
    collapse onto one identifier.
    """


def _env(mapping: Mapping[str, str], name: str, default: str = "") -> str:
    return str(mapping.get(name, default) or "").strip()


def _first(mapping: Mapping[str, str], names: list[str]) -> tuple[str, str]:
    """Return ``(value, source_env_var)`` for the first name that is set."""
    for name in names:
        value = _env(mapping, name)
        if value:
            return value, name
    return "", ""


@dataclass(frozen=True)
class RoleBinding:
    """Everything needed to issue one role's calls, plus where it came from."""

    role: str
    declared_slot: str
    model: str
    model_source: str
    base_url: str
    base_url_source: str
    api_key: str = field(default="", repr=False)
    api_key_source: str = ""
    temperature: float = 0.0
    max_tokens: int = 4096
    timeout_s: float = 120.0

    @property
    def configured(self) -> bool:
        return bool(self.base_url) and bool(self.model)

    @property
    def endpoint_label(self) -> str:
        """Host (and port) of the base URL. Never userinfo, path, or query."""
        return sanitize_url(self.base_url)

    @property
    def provider(self) -> str:
        return "openai-compatible /chat/completions"

    def public_dict(self) -> dict[str, Any]:
        """A credential-free description safe to write into run outputs."""
        return {
            "role": self.role,
            "declared_model_slot": self.declared_slot,
            "resolved_model": self.model,
            "resolved_model_source": self.model_source or "config",
            "provider": self.provider,
            "endpoint_label": self.endpoint_label,
            "endpoint_source": self.base_url_source,
            "api_key_present": bool(self.api_key),
            "api_key_source": self.api_key_source,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout_s": self.timeout_s,
        }


def sanitize_url(url: str) -> str:
    """Reduce a URL to ``scheme://host[:port]``; drop userinfo and path.

    A base URL can legally embed credentials (``https://user:token@host``).
    Printing the raw URL would leak them, so every human-readable surface in
    this repository goes through here.
    """
    if not url:
        return "(unset)"
    parts = urlsplit(url if "//" in url else f"//{url}")
    host = parts.hostname or ""
    if not host:
        return "(unparseable)"
    if parts.port:
        host = f"{host}:{parts.port}"
    scheme = parts.scheme or "http"
    return f"{scheme}://{host}"


def _role_spec(config: DHDConfig, role: str) -> Any:
    for agent_type in _AGENT_TYPE_BY_ROLE[role]:
        try:
            return config.agent(agent_type)
        except KeyError:
            continue
    return None


def _float_env(mapping: Mapping[str, str], name: str, default: float) -> float:
    raw = _env(mapping, name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from exc


def _int_env(mapping: Mapping[str, str], name: str, default: int) -> int:
    raw = _env(mapping, name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc


def bind_models(
    config: DHDConfig,
    env: Mapping[str, str] | None = None,
    *,
    require_configured: bool = False,
) -> dict[str, RoleBinding]:
    """Resolve one :class:`RoleBinding` per role and verify it against config.

    Raises :class:`ModelBindingError` when the resolved identities contradict
    what the protocol config declared:

    * two roles declaring **different** model slots resolved to the **same**
      identifier (the measured actor/evaluator collapse), or
    * two roles declaring the **same** slot resolved to **different**
      identifiers, or
    * a ``DHD_EXPECT_<ROLE>_MODEL`` assertion that does not match.
    """
    environ = os.environ if env is None else env
    timeout_s = _float_env(environ, "DHD_TIMEOUT_S", _float_env(environ, "MODEL_API_TIMEOUT_S", 120.0))
    temperature_override = _env(environ, "DHD_TEMPERATURE_OVERRIDE")
    max_tokens_override = _env(environ, "DHD_MAX_TOKENS_OVERRIDE")

    bindings: dict[str, RoleBinding] = {}
    for role in ROLES:
        spec = _role_spec(config, role)
        if spec is None:
            continue
        upper = role.upper()
        lane = ["DHD_ACTOR_MODEL"] if role in ACTOR_ROLES else []
        model, model_src = _first(
            environ, [f"DHD_{upper}_MODEL", *lane, "MODEL_API_MODEL"]
        )
        lane_url = ["DHD_ACTOR_BASE_URL"] if role in ACTOR_ROLES else []
        base_url, url_src = _first(
            environ, [f"DHD_{upper}_BASE_URL", *lane_url, "MODEL_API_BASE"]
        )
        lane_key = ["DHD_ACTOR_API_KEY"] if role in ACTOR_ROLES else []
        api_key, key_src = _first(
            environ, [f"DHD_{upper}_API_KEY", *lane_key, "MODEL_API_KEY"]
        )
        bindings[role] = RoleBinding(
            role=role,
            declared_slot=spec.model,
            model=model,
            model_source=model_src,
            base_url=base_url.rstrip("/"),
            base_url_source=url_src,
            api_key=api_key,
            api_key_source=key_src,
            temperature=(
                float(temperature_override) if temperature_override else spec.temperature
            ),
            max_tokens=(
                int(max_tokens_override) if max_tokens_override else spec.max_tokens
            ),
            timeout_s=timeout_s,
        )

    _check_expectations(bindings, environ)
    _check_slot_structure(bindings)

    if require_configured:
        missing = sorted(r for r, b in bindings.items() if not b.configured)
        if missing:
            raise ConfigError(
                "missing endpoint or model for role(s): "
                + ", ".join(missing)
                + ". Set DHD_<ROLE>_BASE_URL and DHD_<ROLE>_MODEL (or the "
                "DHD_ACTOR_* / MODEL_API_* fallbacks). See .env.example."
            )
    return bindings


def _check_expectations(
    bindings: Mapping[str, RoleBinding], env: Mapping[str, str]
) -> None:
    for role, binding in bindings.items():
        expected = _env(env, f"DHD_EXPECT_{role.upper()}_MODEL")
        if expected and expected != binding.model:
            raise ModelBindingError(
                f"Configured {role} model mismatch: "
                f"declared={expected!r} loaded={binding.model!r}"
            )


def _check_slot_structure(bindings: Mapping[str, RoleBinding]) -> None:
    """Resolved identities must mirror the slot structure the config declares."""
    configured = {r: b for r, b in bindings.items() if b.model}
    if len(configured) < 2:
        return
    for left in sorted(configured):
        for right in sorted(configured):
            if left >= right:
                continue
            a, b = configured[left], configured[right]
            same_slot = a.declared_slot == b.declared_slot
            same_model = a.model == b.model
            if same_slot and not same_model:
                raise ModelBindingError(
                    f"Roles {left!r} and {right!r} declare one model slot "
                    f"({a.declared_slot!r}) but resolved to different "
                    f"identifiers: {a.model!r} vs {b.model!r}. Set them to the "
                    "same value or split the slot in the protocol config."
                )
            if not same_slot and same_model:
                raise ModelBindingError(
                    f"Roles {left!r} and {right!r} declare different model "
                    f"slots ({a.declared_slot!r} vs {b.declared_slot!r}) but "
                    f"both resolved to {a.model!r}. The protocol requires a "
                    f"separate model per slot; set DHD_{left.upper()}_MODEL "
                    f"and DHD_{right.upper()}_MODEL explicitly."
                )


@dataclass(frozen=True)
class RunSettings:
    """Non-connection run parameters, resolved from one place."""

    dataset_id: str
    data_root: Path
    cache_dir: Path
    output_dir: Path
    benchmark: str
    sample_limit: int
    replicates: int
    seed: int
    concurrency: int
    max_retries: int
    retry_backoff_s: float
    timeout_s: float
    analysis_input_dir: Path
    analysis_output_dir: Path

    def public_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "data_root": str(self.data_root),
            "cache_dir": str(self.cache_dir),
            "output_dir": str(self.output_dir),
            "benchmark": self.benchmark,
            "sample_limit": self.sample_limit,
            "replicates": self.replicates,
            "seed": self.seed,
            "concurrency": self.concurrency,
            "max_retries": self.max_retries,
            "retry_backoff_s": self.retry_backoff_s,
            "timeout_s": self.timeout_s,
            "analysis_input_dir": str(self.analysis_input_dir),
            "analysis_output_dir": str(self.analysis_output_dir),
        }


def load_run_settings(env: Mapping[str, str] | None = None) -> RunSettings:
    """Resolve run parameters. Every path default is repository-relative."""
    environ = os.environ if env is None else env

    def _path(name: str, default: Path) -> Path:
        raw = _env(environ, name)
        return Path(raw).expanduser() if raw else default

    return RunSettings(
        dataset_id=_env(environ, "DHD_DATASET_ID", "AgentsSci/AAAI_Wrong-but-Useful"),
        data_root=_path("DHD_DATA_ROOT", REPO_ROOT / "data"),
        cache_dir=_path("DHD_CACHE_DIR", REPO_ROOT / ".dhd_cache"),
        output_dir=_path("DHD_OUTPUT_DIR", REPO_ROOT / "outputs"),
        benchmark=_env(environ, "DHD_BENCHMARK", "smoke_fixture"),
        sample_limit=_int_env(environ, "DHD_SAMPLE_LIMIT", 0),
        replicates=_int_env(environ, "DHD_REPLICATES", 1),
        seed=_int_env(environ, "DHD_SEED", 20260717),
        concurrency=_int_env(environ, "DHD_CONCURRENCY", 1),
        max_retries=_int_env(environ, "DHD_MAX_RETRIES", 2),
        retry_backoff_s=_float_env(environ, "DHD_RETRY_BACKOFF_S", 2.0),
        timeout_s=_float_env(environ, "DHD_TIMEOUT_S", 120.0),
        analysis_input_dir=_path("DHD_ANALYSIS_INPUT_DIR", REPO_ROOT / "data" / "derived"),
        analysis_output_dir=_path("DHD_ANALYSIS_OUTPUT_DIR", REPO_ROOT / "reproduced"),
    )


def config_sha256(config_path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(config_path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def code_commit() -> str:
    """Best-effort git commit of this checkout; ``"unknown"`` when unavailable."""
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    value = out.stdout.strip()
    return value if out.returncode == 0 and value else "unknown"


def resolved_models_record(
    bindings: Mapping[str, RoleBinding], config_path: str | Path
) -> dict[str, Any]:
    """The audit block written into every run output. Carries no credentials."""
    return {
        "config_path": str(config_path),
        "config_sha256": config_sha256(config_path),
        "code_commit": code_commit(),
        "roles": {role: bindings[role].public_dict() for role in sorted(bindings)},
        "distinct_resolved_models": sorted(
            {b.model for b in bindings.values() if b.model}
        ),
    }


__all__ = [
    "ACTOR_ROLES",
    "ROLES",
    "ConfigError",
    "ModelBindingError",
    "RoleBinding",
    "RunSettings",
    "bind_models",
    "code_commit",
    "config_sha256",
    "load_config",
    "load_run_settings",
    "resolved_models_record",
    "sanitize_url",
]
