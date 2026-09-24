"""Model identity must be resolved per role, emitted, and auditable.

These tests exist because of a measured defect in the published ancillary
artifact: all 24 outbound requests carried ONE model identifier -- the single
``MODEL_API_MODEL`` value -- for BOTH the integrator and the evaluator, while
the protocol YAML declared two different model slots. The parsed
``AgentSpec.model`` was never read by anything.

That breaks the paper's own design: "Both gpt-oss-120b and gemma-4-31B-it model
families use a separate gpt-oss-120b evaluator." The secondary-actor arm
*requires* actor != evaluator, and with one global model variable it cannot be
enacted at all.

Each test below fails if that defect returns. Every one of them was checked
against the defective behaviour before being kept: see
``test_collapse_detector_is_not_vacuous`` for the in-suite positive control.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dhd.config import (
    ConfigError,
    ModelBindingError,
    RoleBinding,
    bind_models,
    resolved_models_record,
    sanitize_url,
)
from dhd.model_api import RoleRouter
from dhd.protocol import load_config

ROOT = Path(__file__).resolve().parents[1]
SMOKE_CONFIG = ROOT / "configs" / "smoke" / "smoke_config.yaml"
PAPER_CONFIG = ROOT / "configs" / "paper" / "dhd_config.yaml"

#: The exact environment shape that produced the defect: one global model.
COLLAPSED_ENV = {
    "MODEL_API_BASE": "http://localhost:8000/v1",
    "MODEL_API_MODEL": "one-model-for-everything",
    "MODEL_API_KEY": "unused",
}

#: A correct environment: actor and evaluator resolved separately.
SPLIT_ENV = {
    "DHD_ACTOR_BASE_URL": "http://localhost:8000/v1",
    "DHD_ACTOR_MODEL": "actor-model-id",
    "DHD_EVALUATOR_BASE_URL": "http://localhost:8001/v1",
    "DHD_EVALUATOR_MODEL": "evaluator-model-id",
}


# --------------------------------------------------------------------------
# 1. Emitted must equal configured.
# --------------------------------------------------------------------------


def test_actor_and_evaluator_must_not_collapse_onto_one_model():
    """The measured defect itself: two declared slots, one emitted identifier."""
    config = load_config(SMOKE_CONFIG)
    integrator_slot = config.agent("integrator").model
    evaluator_slot = config.agent("evaluator").model
    assert integrator_slot != evaluator_slot, (
        "precondition: the shipped config must declare two distinct model slots, "
        "otherwise this test cannot detect a collapse"
    )
    with pytest.raises(ModelBindingError) as excinfo:
        bind_models(config, COLLAPSED_ENV)
    assert "one-model-for-everything" in str(excinfo.value)


def test_split_environment_binds_each_role_to_its_own_model():
    bindings = bind_models(load_config(SMOKE_CONFIG), SPLIT_ENV)
    assert bindings["integrator"].model == "actor-model-id"
    assert bindings["evaluator"].model == "evaluator-model-id"
    assert bindings["integrator"].model != bindings["evaluator"].model


def test_paper_config_binds_all_four_roles_separately():
    """Recruiter/hypothesizer/integrator share the actor lane; evaluator does not."""
    env = dict(SPLIT_ENV)
    bindings = bind_models(load_config(PAPER_CONFIG), env)
    assert set(bindings) == {"recruiter", "hypothesizer", "integrator", "evaluator"}
    for role in ("recruiter", "hypothesizer", "integrator"):
        assert bindings[role].model == "actor-model-id"
    assert bindings["evaluator"].model == "evaluator-model-id"


def test_router_emits_the_configured_model_per_role(monkeypatch):
    """Record what actually reaches the wire; it must match the configuration."""
    sent: list[dict] = []

    def fake_post(**kwargs):
        sent.append({"model": kwargs["model"], "url": kwargs["api_base_url"]})
        return "Correctness: 1", {"model": kwargs["model"]}

    monkeypatch.setattr("dhd.model_api._post_chat_completion", fake_post)
    router = RoleRouter(bind_models(load_config(SMOKE_CONFIG), SPLIT_ENV))
    router.generate("integrator", [{"role": "user", "content": "x"}])
    router.generate("evaluator", [{"role": "user", "content": "y"}])

    assert [item["model"] for item in sent] == ["actor-model-id", "evaluator-model-id"]
    assert router.emitted_models_by_role() == {
        "evaluator": ["evaluator-model-id"],
        "integrator": ["actor-model-id"],
    }
    router.verify_emitted_matches_configured()  # must not raise


def test_verify_fails_when_emitted_differs_from_configured():
    """A router that sent the wrong identifier must be caught after the fact."""
    bindings = bind_models(load_config(SMOKE_CONFIG), SPLIT_ENV)
    router = RoleRouter(bindings)
    router.emitted.append({"role": "integrator", "model": "something-else"})
    with pytest.raises(ModelBindingError) as excinfo:
        router.verify_emitted_matches_configured()
    assert "configured='actor-model-id'" in str(excinfo.value)
    assert "something-else" in str(excinfo.value)


def test_explicit_expectation_mismatch_aborts():
    """The guard ported from the repository runner: declared != loaded raises."""
    env = {**SPLIT_ENV, "DHD_EXPECT_EVALUATOR_MODEL": "a-different-judge"}
    with pytest.raises(ModelBindingError) as excinfo:
        bind_models(load_config(SMOKE_CONFIG), env)
    message = str(excinfo.value)
    assert "declared='a-different-judge'" in message
    assert "loaded='evaluator-model-id'" in message


def test_same_slot_must_not_split():
    """Roles sharing one declared slot must not resolve to different models."""
    env = {
        **SPLIT_ENV,
        "DHD_INTEGRATOR_MODEL": "integrator-only",
    }
    with pytest.raises(ModelBindingError) as excinfo:
        bind_models(load_config(PAPER_CONFIG), env)
    assert "one model slot" in str(excinfo.value)


# --------------------------------------------------------------------------
# 2. A required endpoint must be missing loudly, not silently.
# --------------------------------------------------------------------------


def test_missing_endpoint_is_reported_not_defaulted():
    bindings = bind_models(load_config(SMOKE_CONFIG), {"DHD_ACTOR_MODEL": "m"})
    assert not bindings["integrator"].configured
    assert bindings["integrator"].base_url == ""


def test_require_configured_raises_and_names_the_missing_roles():
    env = {"DHD_ACTOR_BASE_URL": "http://localhost:8000/v1", "DHD_ACTOR_MODEL": "m"}
    with pytest.raises(ConfigError) as excinfo:
        bind_models(load_config(SMOKE_CONFIG), env, require_configured=True)
    assert "evaluator" in str(excinfo.value)


def test_router_refuses_to_call_an_unconfigured_role():
    router = RoleRouter(bind_models(load_config(SMOKE_CONFIG), {}))
    with pytest.raises(RuntimeError) as excinfo:
        router.generate("integrator", [{"role": "user", "content": "x"}])
    assert str(excinfo.value) == "model_api_not_configured:integrator"


# --------------------------------------------------------------------------
# 3. Credentials must never be printable.
# --------------------------------------------------------------------------


def test_public_record_never_contains_the_credential():
    secret = "-".join(["sk", "do", "not", "leak", "me"])
    env = {**SPLIT_ENV, "DHD_ACTOR_API_KEY": secret, "DHD_EVALUATOR_API_KEY": secret}
    bindings = bind_models(load_config(SMOKE_CONFIG), env)
    assert bindings["integrator"].api_key == secret  # it IS held...
    record = resolved_models_record(bindings, SMOKE_CONFIG)
    blob = json.dumps(record)
    assert secret not in blob  # ...but never published
    assert record["roles"]["integrator"]["api_key_present"] is True
    assert record["roles"]["integrator"]["api_key_source"] == "DHD_ACTOR_API_KEY"


def test_repr_of_a_binding_does_not_expose_the_key():
    secret = "-".join(["sk", "hidden", "value"])
    binding = RoleBinding(
        role="integrator",
        declared_slot="slot",
        model="m",
        model_source="env",
        base_url="https://example.invalid/v1",
        base_url_source="env",
        api_key=secret,
    )
    assert secret not in repr(binding)


def test_credentials_in_a_url_are_stripped_from_the_endpoint_label():
    token = "-".join(["user", "tok3n"])
    binding = RoleBinding(
        role="integrator",
        declared_slot="slot",
        model="m",
        model_source="env",
        base_url=f"https://{token}@models.example.invalid:8443/v1",
        base_url_source="env",
    )
    assert binding.endpoint_label == "https://models.example.invalid:8443"
    assert token not in binding.endpoint_label
    assert token not in json.dumps(binding.public_dict())


def test_sanitize_url_drops_userinfo_path_and_query():
    assert sanitize_url("https://u:p@h.example.invalid/v1?key=abc") == "https://h.example.invalid"
    assert sanitize_url("") == "(unset)"


# --------------------------------------------------------------------------
# 4. No author endpoint may be selected by default.
# --------------------------------------------------------------------------

#: Hosts and path fragments that must never appear as a default anywhere in the
#: repository. Assembled from parts so this file contains no matchable literal
#: that would trip the portability audit against itself.
_FORBIDDEN_HOST_PARTS = [
    ("inference-api", "alcf", "anl", "gov"),
    ("proxy", "alcf", "anl", "gov"),
]


def test_no_author_endpoint_is_reachable_as_a_default():
    """With an empty environment, every role resolves to nothing at all."""
    for config_path in (SMOKE_CONFIG, PAPER_CONFIG):
        bindings = bind_models(load_config(config_path), {})
        for role, binding in bindings.items():
            assert binding.base_url == "", f"{role} defaulted to {binding.base_url!r}"
            assert binding.model == "", f"{role} defaulted to model {binding.model!r}"
            assert not binding.configured


def test_repository_contains_no_author_endpoint_default():
    forbidden = [".".join(parts) for parts in _FORBIDDEN_HOST_PARTS]
    offenders = []
    skip_dirs = {
        ".git", ".venv", "venv", "__pycache__", ".pytest_cache", "reproduced",
        "outputs", "smoke_output", "site-packages", "node_modules", ".dhd_cache",
    }
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() in {".pdf", ".png", ".svg"}:
            continue
        if set(path.relative_to(ROOT).parts) & skip_dirs:
            continue
        if path.resolve() == Path(__file__).resolve():
            continue  # this file names them in order to forbid them
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for host in forbidden:
            if host in text:
                offenders.append((path.relative_to(ROOT).as_posix(), host))
    assert not offenders, f"author endpoint present: {offenders}"


# --------------------------------------------------------------------------
# 5. Positive control: prove the collapse detector can actually fire.
# --------------------------------------------------------------------------


def test_collapse_detector_is_not_vacuous():
    """A detector only ever run on good input detects nothing known.

    Here the *defective* configuration is constructed on purpose and must be
    rejected, while a correct one must be accepted. If a future refactor made
    ``bind_models`` unconditionally permissive, the first half fails; if it made
    it unconditionally strict, the second half fails.
    """
    config = load_config(SMOKE_CONFIG)
    with pytest.raises(ModelBindingError):
        bind_models(config, COLLAPSED_ENV)          # must reject the defect
    bind_models(config, SPLIT_ENV)                  # must accept the fix
