"""Generic OpenAI-compatible model API client, resolved per protocol role.

Connection details never live in this module. They are resolved by
:mod:`dhd.config` from documented environment variables, so the repository
carries no deployment-specific hostname, account, or credential -- and no
default that could point a reader's traffic at somebody else's server.

Two client surfaces exist:

``ClientConfig`` / :func:`load_client_config`
    The single-model surface the published reproducibility artifact used,
    driven by ``MODEL_API_BASE`` / ``MODEL_API_MODEL`` / ``MODEL_API_KEY``.
    Kept working so existing instructions keep working.

:class:`RoleRouter`
    The role-aware surface this repository uses for the protocol path. It holds
    one :class:`~dhd.config.RoleBinding` per role and sends *that role's*
    resolved model identifier on *that role's* endpoint. It also records what it
    actually sent, so a run can be audited after the fact rather than trusted.

The client never prints the key or any authorization header; failures are
re-raised as ``RuntimeError`` with a type name only.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping

from .config import ModelBindingError, RoleBinding, bind_models, load_config  # noqa: F401


@dataclass(frozen=True)
class ClientConfig:
    api_base_url: str
    model: str
    api_key: str = ""
    timeout_s: float = 120.0

    @property
    def configured(self) -> bool:
        return bool(self.api_base_url) and bool(self.model)


def load_client_config() -> ClientConfig:
    """Build a single-model client configuration from generic env vars.

    Recognises the ``DHD_ACTOR_*`` names first and falls back to the artifact's
    original ``MODEL_API_*`` names, so both spellings work.
    """
    base = os.environ.get("DHD_ACTOR_BASE_URL") or os.environ.get("MODEL_API_BASE", "")
    model = os.environ.get("DHD_ACTOR_MODEL") or os.environ.get("MODEL_API_MODEL", "")
    key = os.environ.get("DHD_ACTOR_API_KEY") or os.environ.get("MODEL_API_KEY", "")
    timeout = os.environ.get("DHD_TIMEOUT_S") or os.environ.get("MODEL_API_TIMEOUT_S", "120")
    return ClientConfig(
        api_base_url=str(base).rstrip("/"),
        model=str(model),
        api_key=str(key),
        timeout_s=float(timeout),
    )


def _post_chat_completion(
    *,
    api_base_url: str,
    model: str,
    api_key: str,
    timeout_s: float,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    max_retries: int = 0,
    retry_backoff_s: float = 2.0,
) -> tuple[str, dict[str, Any]]:
    """POST one chat completion. Returns ``(text, sent_payload_without_messages)``.

    Only the Python standard library is used, so the protocol path has no
    required third-party dependency.
    """
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    audit = {k: v for k, v in payload.items() if k != "messages"}
    attempt = 0
    while True:
        request = urllib.request.Request(
            f"{api_base_url}/chat/completions",
            data=data,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_s) as response:
                body = json.loads(response.read().decode("utf-8"))
            return _first_message_text(body), audit
        except Exception as error:  # noqa: BLE001 - reported as operational failure
            if attempt >= max_retries:
                # Never surface headers, URLs, or credentials in the error text.
                raise RuntimeError(
                    f"model_api_call_failed:{type(error).__name__}"
                ) from None
            attempt += 1
            time.sleep(retry_backoff_s * attempt)


def chat_completion(
    config: ClientConfig,
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.0,
    max_tokens: int = 4096,
) -> str:
    """Call an OpenAI-compatible chat completions API and return the text."""
    if not config.configured:
        raise RuntimeError("model_api_not_configured")
    text, _ = _post_chat_completion(
        api_base_url=config.api_base_url,
        model=config.model,
        api_key=config.api_key,
        timeout_s=config.timeout_s,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return text


def _first_message_text(body: dict[str, Any]) -> str:
    choices = body.get("choices") or []
    if not choices:
        raise RuntimeError("model_api_empty_choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("model_api_empty_content")
    return content


class RoleRouter:
    """Send each protocol role's calls under that role's resolved model.

    The router is the only place a model identifier reaches the wire. It records
    every ``(role, model)`` pair it actually sent in :attr:`emitted`, which is
    written into run outputs so a reader can audit what ran instead of trusting
    a filename or a CLI flag.
    """

    def __init__(
        self,
        bindings: Mapping[str, RoleBinding],
        *,
        max_retries: int = 0,
        retry_backoff_s: float = 2.0,
    ) -> None:
        self._bindings = dict(bindings)
        self._max_retries = max_retries
        self._retry_backoff_s = retry_backoff_s
        self.emitted: list[dict[str, Any]] = []

    @classmethod
    def from_env(
        cls,
        config_path: str,
        env: Mapping[str, str] | None = None,
        **kwargs: Any,
    ) -> "RoleRouter":
        return cls(bind_models(load_config(config_path), env), **kwargs)

    @property
    def bindings(self) -> dict[str, RoleBinding]:
        return dict(self._bindings)

    def binding(self, role: str) -> RoleBinding:
        try:
            return self._bindings[role]
        except KeyError as exc:
            raise RuntimeError(f"model_api_unknown_role:{role}") from exc

    def configured(self, role: str) -> bool:
        return role in self._bindings and self._bindings[role].configured

    def generate(
        self,
        role: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        binding = self.binding(role)
        if not binding.configured:
            raise RuntimeError(f"model_api_not_configured:{role}")
        text, audit = _post_chat_completion(
            api_base_url=binding.base_url,
            model=binding.model,
            api_key=binding.api_key,
            timeout_s=binding.timeout_s,
            messages=messages,
            temperature=binding.temperature if temperature is None else temperature,
            max_tokens=binding.max_tokens if max_tokens is None else max_tokens,
            max_retries=self._max_retries,
            retry_backoff_s=self._retry_backoff_s,
        )
        self.emitted.append({"role": role, **audit})
        return text

    def emitted_models_by_role(self) -> dict[str, list[str]]:
        """Distinct model identifiers actually sent, grouped by role."""
        out: dict[str, set[str]] = {}
        for record in self.emitted:
            out.setdefault(str(record["role"]), set()).add(str(record["model"]))
        return {role: sorted(models) for role, models in sorted(out.items())}

    def verify_emitted_matches_configured(self) -> None:
        """Fail if any role sent an identifier other than the configured one.

        The published artifact's defect was exactly this: the YAML declared two
        model slots and every request went out under one identifier. Calling
        this after a run turns that class of defect into a loud error.
        """
        problems: list[str] = []
        for role, models in self.emitted_models_by_role().items():
            expected = self._bindings[role].model
            if models != [expected]:
                problems.append(
                    f"{role}: configured={expected!r} emitted={models!r}"
                )
        if problems:
            raise ModelBindingError(
                "Emitted model identity does not match configuration -> "
                + "; ".join(problems)
            )


__all__ = [
    "ClientConfig",
    "RoleRouter",
    "chat_completion",
    "load_client_config",
]
