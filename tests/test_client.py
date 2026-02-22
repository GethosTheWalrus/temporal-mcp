"""Tests for TemporalClientManager — TLS, mTLS, and API key auth."""
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
        tls = TemporalClientManager(
            temporal_host="my-namespace.tmprl.cloud:7233", tls_enabled=False
        )._determine_tls_config()
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
        mgr = TemporalClientManager(temporal_host="localhost:7233")
        mock_client = AsyncMock()

        with patch("temporal_mcp.client.Client.connect", return_value=mock_client):
            client = await mgr.connect()

        assert client is mock_client
        assert mgr.client is mock_client

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


class TestDisconnectAndEnsureConnected:
    @pytest.mark.asyncio
    async def test_disconnect_closes_client(self):
        mgr = TemporalClientManager()
        mock_client = AsyncMock()
        mgr.client = mock_client

        await mgr.disconnect()

        mock_client.close.assert_called_once()
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
