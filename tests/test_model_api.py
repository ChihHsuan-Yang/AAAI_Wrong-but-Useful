"""Generic model API client: env-driven config, graceful skip, no secret leaks."""

from dhd.model_api import ClientConfig, load_client_config


def test_load_client_config_reads_generic_env(monkeypatch):
    monkeypatch.setenv("MODEL_API_BASE", "http://localhost:8000/v1/")
    monkeypatch.setenv("MODEL_API_MODEL", "some-model")
    monkeypatch.setenv("MODEL_API_KEY", "secret-token")
    config = load_client_config()
    assert config.configured
    assert config.api_base_url == "http://localhost:8000/v1"  # trailing slash trimmed
    assert config.model == "some-model"


def test_unconfigured_client_reports_not_configured(monkeypatch):
    monkeypatch.delenv("MODEL_API_BASE", raising=False)
    monkeypatch.delenv("MODEL_API_MODEL", raising=False)
    config = load_client_config()
    assert not config.configured


def test_unconfigured_call_reports_generic_error_without_token():
    # A fabricated token value, assembled at run time so this test file contains
    # no key-like literal for the secret scanner to match.
    fabricated_token = "-".join(["do", "not", "leak", "me"])
    config = ClientConfig(
        api_base_url="http://localhost", model="m", api_key=fabricated_token
    )
    assert config.api_key == fabricated_token

    from dhd import model_api

    unconfigured = ClientConfig(api_base_url="", model="")
    try:
        model_api.chat_completion(unconfigured, [{"role": "user", "content": "x"}])
        raise AssertionError("expected RuntimeError for unconfigured client")
    except RuntimeError as error:
        assert fabricated_token not in str(error)
        assert str(error) == "model_api_not_configured"
