"""Tests for TemporalClientManager — TLS, mTLS, and API key auth."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from temporalio.client import TLSConfig

from temporal_mcp.client import TemporalClientManager


class TestIsRemoteHost:
    def test_localhost(self):
        assert TemporalClientManager(temporal_host="localhost:7233")._is_remote_host() is False

    def test_127(self):
        assert TemporalClientManager(temporal_host="127.0.0.1:7233")._is_remote_host() is False

    def test_docker_internal(self):
        assert TemporalClientManager(temporal_host="host.docker.internal:7233")._is_remote_host() is False

    def test_cloud_host(self):
        assert TemporalClientManager(temporal_host="my-namespace.tmprl.cloud:7233")._is_remote_host() is True


class TestLoadClientCerts:
    def test_no_paths_returns_none(self):
        cert, key = TemporalClientManager()._load_client_certs()
        assert cert is None
        assert key is None

    def test_only_cert_raises(self):
        mgr = TemporalClientManager(tls_client_cert_path="/path/to/cert.pem")
        with pytest.raises(ValueError, match="must be set together"):
            mgr._load_client_certs()

    def test_only_key_raises(self):
        mgr = TemporalClientManager(tls_client_key_path="/path/to/key.pem")
        with pytest.raises(ValueError, match="must be set together"):
            mgr._load_client_certs()

    def test_both_paths_loaded(self, tmp_path):
        cert_file = tmp_path / "client.pem"
        key_file = tmp_path / "client.key"
        cert_file.write_bytes(b"CERT_DATA")
        key_file.write_bytes(b"KEY_DATA")

        mgr = TemporalClientManager(
            tls_client_cert_path=str(cert_file),
            tls_client_key_path=str(key_file),
        )
        cert, key = mgr._load_client_certs()
        assert cert == b"CERT_DATA"
        assert key == b"KEY_DATA"

    def test_missing_cert_file_raises(self, tmp_path):
        key_file = tmp_path / "client.key"
        key_file.write_bytes(b"KEY_DATA")

        mgr = TemporalClientManager(
            tls_client_cert_path="/nonexistent/cert.pem",
            tls_client_key_path=str(key_file),
        )
        with pytest.raises(FileNotFoundError):
            mgr._load_client_certs()


class TestDetermineTlsConfig:
    def test_mtls_returns_config_with_certs(self, tmp_path):
        cert_file = tmp_path / "client.pem"
        key_file = tmp_path / "client.key"
        cert_file.write_bytes(b"CERT")
        key_file.write_bytes(b"KEY")

        mgr = TemporalClientManager(
            tls_client_cert_path=str(cert_file),
            tls_client_key_path=str(key_file),
        )
        tls = mgr._determine_tls_config()
        assert isinstance(tls, TLSConfig)
        assert tls.client_cert == b"CERT"
        assert tls.client_private_key == b"KEY"

    def test_api_key_returns_plain_tls(self):
        tls = TemporalClientManager(api_key="my-secret-key")._determine_tls_config()
        assert isinstance(tls, TLSConfig)
        assert tls.client_cert is None
        assert tls.client_private_key is None

    def test_explicit_true_enables_tls(self):
        tls = TemporalClientManager(temporal_host="localhost:7233", tls_enabled=True)._determine_tls_config()
        assert isinstance(tls, TLSConfig)

    def test_explicit_false_disables_tls(self):
        tls = TemporalClientManager(temporal_host="my-namespace.tmprl.cloud:7233", tls_enabled=False)._determine_tls_config()
        assert tls is None

    def test_auto_detect_remote_enables_tls(self):
        tls = TemporalClientManager(temporal_host="my-namespace.tmprl.cloud:7233")._determine_tls_config()
        assert isinstance(tls, TLSConfig)

    def test_auto_detect_local_disables_tls(self):
        tls = TemporalClientManager(temporal_host="localhost:7233")._determine_tls_config()
        assert tls is None


class TestConnect:
    @pytest.mark.asyncio
    async def test_connect_success(self):
        mgr = TemporalClientManager(temporal_host="localhost:7233", namespace="payments")
        mock_client = AsyncMock()

        with patch("temporal_mcp.client.Client.connect", return_value=mock_client) as mock_connect:
            client = await mgr.connect()

        assert client is mock_client
        assert mgr.client is mock_client
        assert mock_connect.call_args.kwargs["namespace"] == "payments"

    @pytest.mark.asyncio
    async def test_connect_reuses_existing_client(self):
        mgr = TemporalClientManager()
        mock_client = AsyncMock()

        with patch("temporal_mcp.client.Client.connect", return_value=mock_client) as mock_connect:
            await mgr.connect()
            await mgr.connect()
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure_propagates(self):
        mgr = TemporalClientManager()
        with patch("temporal_mcp.client.Client.connect", side_effect=Exception("connection refused")):
            with pytest.raises(Exception, match="connection refused"):
                await mgr.connect()

    @pytest.mark.asyncio
    async def test_concurrent_connect_creates_one_connection(self):
        mgr = TemporalClientManager()
        mock_client = MagicMock()

        async def connect(*args, **kwargs):
            await asyncio.sleep(0)
            return mock_client

        with patch("temporal_mcp.client.Client.connect", side_effect=connect) as mock_connect:
            clients = await asyncio.gather(mgr.connect(), mgr.connect(), mgr.connect())

        assert clients == [mock_client, mock_client, mock_client]
        mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_passes_api_key(self):
        mgr = TemporalClientManager(
            temporal_host="my-namespace.tmprl.cloud:7233",
            api_key="tok_abc123",
        )
        mock_client = AsyncMock()

        with patch("temporal_mcp.client.Client.connect", return_value=mock_client) as mock_connect:
            await mgr.connect()
            _, kwargs = mock_connect.call_args
            assert kwargs.get("api_key") == "tok_abc123"
            assert isinstance(kwargs.get("tls"), TLSConfig)

    @pytest.mark.asyncio
    async def test_connect_passes_mtls_config(self, tmp_path):
        cert_file = tmp_path / "client.pem"
        key_file = tmp_path / "client.key"
        cert_file.write_bytes(b"CERT")
        key_file.write_bytes(b"KEY")

        mgr = TemporalClientManager(
            temporal_host="my-namespace.tmprl.cloud:7233",
            tls_client_cert_path=str(cert_file),
            tls_client_key_path=str(key_file),
        )
        mock_client = AsyncMock()

        with patch("temporal_mcp.client.Client.connect", return_value=mock_client) as mock_connect:
            await mgr.connect()
            _, kwargs = mock_connect.call_args
            tls = kwargs.get("tls")
            assert isinstance(tls, TLSConfig)
            assert tls.client_cert == b"CERT"
            assert tls.client_private_key == b"KEY"


class TestNamespaceClients:
    @pytest.mark.asyncio
    async def test_override_client_shares_base_service_client(self):
        mgr = TemporalClientManager(namespace="default", allowed_namespaces=["default", "payments"])
        service_client = MagicMock()
        base_client = MagicMock()
        base_client.config.return_value = {
            "service_client": service_client,
            "namespace": "default",
        }
        mgr.client = base_client

        with patch("temporal_mcp.client.Client") as client_class:
            override_client = await mgr.get_client("payments")

        assert override_client is client_class.return_value
        client_class.assert_called_once_with(service_client=service_client, namespace="payments")

    @pytest.mark.asyncio
    async def test_default_namespace_reuses_base_client(self):
        mgr = TemporalClientManager(namespace="default")
        base_client = MagicMock()
        mgr.client = base_client

        assert await mgr.get_client() is base_client

    def test_unset_allowlist_only_permits_default(self):
        mgr = TemporalClientManager(namespace="production")

        assert mgr.resolve_namespace() == "production"
        with pytest.raises(ValueError, match="not allowed"):
            mgr.resolve_namespace("payments")

    def test_wildcard_permits_any_non_empty_namespace(self):
        mgr = TemporalClientManager(allowed_namespaces=["*"])

        assert mgr.resolve_namespace("payments") == "payments"
        with pytest.raises(ValueError, match="non-empty"):
            mgr.resolve_namespace("")

    def test_finite_allowlist_must_include_default(self):
        with pytest.raises(ValueError, match="must be included"):
            TemporalClientManager(namespace="default", allowed_namespaces=["payments"])

    def test_allowlist_is_trimmed_and_deduplicated(self):
        mgr = TemporalClientManager(namespace="default", allowed_namespaces=[" default ", "payments", "payments"])

        assert mgr.allowed_namespaces == frozenset({"default", "payments"})

    @pytest.mark.parametrize("allowed_namespaces", [[], [""], ["default", ""], ["*", "default"]])
    def test_invalid_allowlist_rejected(self, allowed_namespaces):
        with pytest.raises(ValueError):
            TemporalClientManager(allowed_namespaces=allowed_namespaces)


class TestDisconnectAndEnsureConnected:
    @pytest.mark.asyncio
    async def test_disconnect_releases_client(self):
        mgr = TemporalClientManager()
        mock_client = MagicMock()
        mgr.client = mock_client

        await mgr.disconnect()

        assert mgr.client is None

    @pytest.mark.asyncio
    async def test_disconnect_noop_when_not_connected(self):
        mgr = TemporalClientManager()
        await mgr.disconnect()  # Should not raise

    def test_ensure_connected_returns_client(self):
        mgr = TemporalClientManager()
        mock_client = MagicMock()
        mgr.client = mock_client
        assert mgr.ensure_connected() is mock_client

    def test_ensure_connected_raises_when_not_connected(self):
        mgr = TemporalClientManager()
        with pytest.raises(RuntimeError, match="Not connected"):
            mgr.ensure_connected()
