"""Tests for __main__ entry point: CLI arg parsing, env var fallback, and precedence."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_main(argv: list[str], env: dict[str, str] | None = None):
    """Invoke main() with a controlled argv and environment, returning the
    TemporalMCPServer constructor kwargs captured via mock."""
    import sys

    env = env or {}

    captured = {}

    def fake_server(**kwargs):
        captured.update(kwargs)
        instance = MagicMock()
        instance.run = AsyncMock()
        return instance

    with (
        patch.object(sys, "argv", ["temporal-mcp-server"] + argv),
        patch.dict("os.environ", env, clear=True),
        patch("temporal_mcp.__main__.TemporalMCPServer", side_effect=fake_server),
        patch("temporal_mcp.__main__.asyncio.run"),
    ):
        from temporal_mcp.__main__ import main

        main()

    return captured


# ---------------------------------------------------------------------------
# _parse_args
# ---------------------------------------------------------------------------


class TestParseArgs:
    def _parse(self, argv: list[str]):
        import sys
        from unittest.mock import patch
        from temporal_mcp.__main__ import _parse_args

        with patch.object(sys, "argv", ["temporal-mcp-server"] + argv):
            return _parse_args()

    def test_all_args_parsed(self):
        ns = self._parse(
            [
                "--host",
                "myhost:7233",
                "--namespace",
                "mynamespace",
                "--tls-enabled",
                "true",
                "--tls-cert",
                "/certs/client.pem",
                "--tls-key",
                "/certs/client.key",
                "--api-key",
                "secret",
            ]
        )
        assert ns.host == "myhost:7233"
        assert ns.namespace == "mynamespace"
        assert ns.tls_enabled == "true"
        assert ns.tls_cert == "/certs/client.pem"
        assert ns.tls_key == "/certs/client.key"
        assert ns.api_key == "secret"

    def test_no_args_all_none(self):
        ns = self._parse([])
        assert ns.host is None
        assert ns.namespace is None
        assert ns.tls_enabled is None
        assert ns.tls_cert is None
        assert ns.tls_key is None
        assert ns.api_key is None

    def test_tls_enabled_normalised_to_lowercase(self):
        ns = self._parse(["--tls-enabled", "True"])
        assert ns.tls_enabled == "true"

    def test_tls_enabled_false(self):
        ns = self._parse(["--tls-enabled", "false"])
        assert ns.tls_enabled == "false"

    def test_invalid_tls_enabled_raises(self):
        import sys
        from unittest.mock import patch
        from temporal_mcp.__main__ import _parse_args

        with (
            patch.object(sys, "argv", ["temporal-mcp-server", "--tls-enabled", "maybe"]),
            pytest.raises(SystemExit),
        ):
            _parse_args()


# ---------------------------------------------------------------------------
# Defaults (no args, no env vars)
# ---------------------------------------------------------------------------


class TestDefaults:
    def test_host_default(self):
        kwargs = _run_main([], env={})
        assert kwargs["temporal_host"] == "localhost:7233"

    def test_namespace_default(self):
        kwargs = _run_main([], env={})
        assert kwargs["namespace"] == "default"

    def test_tls_default_is_none(self):
        kwargs = _run_main([], env={})
        assert kwargs["tls_enabled"] is None

    def test_cert_key_api_key_default_is_none(self):
        kwargs = _run_main([], env={})
        assert kwargs["tls_client_cert_path"] is None
        assert kwargs["tls_client_key_path"] is None
        assert kwargs["api_key"] is None


# ---------------------------------------------------------------------------
# Env vars used when no args supplied
# ---------------------------------------------------------------------------


class TestEnvVarFallback:
    def test_host_from_env(self):
        kwargs = _run_main([], env={"TEMPORAL_HOST": "envhost:7233"})
        assert kwargs["temporal_host"] == "envhost:7233"

    def test_namespace_from_env(self):
        kwargs = _run_main([], env={"TEMPORAL_NAMESPACE": "envns"})
        assert kwargs["namespace"] == "envns"

    def test_tls_true_from_env(self):
        kwargs = _run_main([], env={"TEMPORAL_TLS_ENABLED": "true"})
        assert kwargs["tls_enabled"] is True

    def test_tls_false_from_env(self):
        kwargs = _run_main([], env={"TEMPORAL_TLS_ENABLED": "false"})
        assert kwargs["tls_enabled"] is False

    def test_tls_empty_env_gives_none(self):
        kwargs = _run_main([], env={"TEMPORAL_TLS_ENABLED": ""})
        assert kwargs["tls_enabled"] is None

    def test_cert_from_env(self):
        kwargs = _run_main([], env={"TEMPORAL_TLS_CLIENT_CERT_PATH": "/env/cert.pem"})
        assert kwargs["tls_client_cert_path"] == "/env/cert.pem"

    def test_key_from_env(self):
        kwargs = _run_main([], env={"TEMPORAL_TLS_CLIENT_KEY_PATH": "/env/key.pem"})
        assert kwargs["tls_client_key_path"] == "/env/key.pem"

    def test_api_key_from_env(self):
        kwargs = _run_main([], env={"TEMPORAL_API_KEY": "env-secret"})
        assert kwargs["api_key"] == "env-secret"


# ---------------------------------------------------------------------------
# CLI args take precedence over env vars
# ---------------------------------------------------------------------------


class TestArgPrecedenceOverEnv:
    def test_host_arg_overrides_env(self):
        kwargs = _run_main(
            ["--host", "arghost:7233"],
            env={"TEMPORAL_HOST": "envhost:7233"},
        )
        assert kwargs["temporal_host"] == "arghost:7233"

    def test_namespace_arg_overrides_env(self):
        kwargs = _run_main(
            ["--namespace", "argns"],
            env={"TEMPORAL_NAMESPACE": "envns"},
        )
        assert kwargs["namespace"] == "argns"

    def test_tls_arg_overrides_env(self):
        kwargs = _run_main(
            ["--tls-enabled", "true"],
            env={"TEMPORAL_TLS_ENABLED": "false"},
        )
        assert kwargs["tls_enabled"] is True

    def test_cert_arg_overrides_env(self):
        kwargs = _run_main(
            ["--tls-cert", "/arg/cert.pem"],
            env={"TEMPORAL_TLS_CLIENT_CERT_PATH": "/env/cert.pem"},
        )
        assert kwargs["tls_client_cert_path"] == "/arg/cert.pem"

    def test_key_arg_overrides_env(self):
        kwargs = _run_main(
            ["--tls-key", "/arg/key.pem"],
            env={"TEMPORAL_TLS_CLIENT_KEY_PATH": "/env/key.pem"},
        )
        assert kwargs["tls_client_key_path"] == "/arg/key.pem"

    def test_api_key_arg_overrides_env(self):
        kwargs = _run_main(
            ["--api-key", "arg-secret"],
            env={"TEMPORAL_API_KEY": "env-secret"},
        )
        assert kwargs["api_key"] == "arg-secret"

    def test_all_args_override_all_env_vars(self):
        kwargs = _run_main(
            [
                "--host",
                "arghost:7233",
                "--namespace",
                "argns",
                "--tls-enabled",
                "false",
                "--tls-cert",
                "/arg/cert.pem",
                "--tls-key",
                "/arg/key.pem",
                "--api-key",
                "arg-secret",
            ],
            env={
                "TEMPORAL_HOST": "envhost:7233",
                "TEMPORAL_NAMESPACE": "envns",
                "TEMPORAL_TLS_ENABLED": "true",
                "TEMPORAL_TLS_CLIENT_CERT_PATH": "/env/cert.pem",
                "TEMPORAL_TLS_CLIENT_KEY_PATH": "/env/key.pem",
                "TEMPORAL_API_KEY": "env-secret",
            },
        )
        assert kwargs["temporal_host"] == "arghost:7233"
        assert kwargs["namespace"] == "argns"
        assert kwargs["tls_enabled"] is False
        assert kwargs["tls_client_cert_path"] == "/arg/cert.pem"
        assert kwargs["tls_client_key_path"] == "/arg/key.pem"
        assert kwargs["api_key"] == "arg-secret"
