"""Temporal client management and connection handling."""

import sys
from typing import Optional

from temporalio.client import Client, TLSConfig


class TemporalClientManager:
    """Manages connection to Temporal server."""

    def __init__(
        self,
        temporal_host: str = "localhost:7233",
        namespace: str = "default",
        tls_enabled: Optional[bool] = None,
        tls_client_cert_path: Optional[str] = None,
        tls_client_key_path: Optional[str] = None,
        tls_ca_path: Optional[str] = None,
        tls_server_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """Initialize the Temporal client manager.

        Args:
            temporal_host: The Temporal server host and port
            namespace: The Temporal namespace to use
            tls_enabled: Whether to use TLS for connection (None = auto-detect, True = force enable, False = force disable)
            tls_client_cert_path: Path to the TLS client certificate file (for mTLS / Temporal Cloud)
            tls_client_key_path: Path to the TLS client private key file (for mTLS / Temporal Cloud)
            tls_ca_path: Path to a PEM CA certificate used to verify the server certificate
                         (maps to ``temporalio.client.TLSConfig.server_root_ca_cert``).
                         Useful when the server is signed by a private/internal CA that is
                         not in the system trust store.
            tls_server_name: Expected server name to validate the server certificate against,
                             also used as the SNI value during the TLS handshake (maps to
                             ``temporalio.client.TLSConfig.domain``). Useful when connecting
                             through an SNI-routed gateway whose backend cert is issued for a
                             name different from ``temporal_host``.
            api_key: API key for Temporal Cloud authentication
        """
        self.temporal_host = temporal_host
        self.namespace = namespace
        self.tls_enabled = tls_enabled
        self.tls_client_cert_path = tls_client_cert_path
        self.tls_client_key_path = tls_client_key_path
        self.tls_ca_path = tls_ca_path
        self.tls_server_name = tls_server_name
        self.api_key = api_key
        self.client: Optional[Client] = None

    async def connect(self) -> Client:
        """Connect to Temporal server.

        Returns:
            Connected Temporal client

        Raises:
            Exception: If connection fails
        """
        if not self.client:
            tls_config = self._determine_tls_config()

            self._log_connection_info(tls_config)

            try:
                self.client = await Client.connect(
                    self.temporal_host,
                    namespace=self.namespace,
                    tls=tls_config,
                    api_key=self.api_key if self.api_key else None,
                )
                print(f"Successfully connected to Temporal at {self.temporal_host}", file=sys.stderr)
            except Exception as e:
                print(f"Failed to connect to Temporal at {self.temporal_host}: {type(e).__name__}: {e}", file=sys.stderr)
                import traceback

                traceback.print_exc(file=sys.stderr)
                raise

        return self.client

    async def disconnect(self):
        """Disconnect from Temporal server."""
        if self.client:
            try:
                await self.client.close()
            except Exception as e:
                print(f"Error closing Temporal client: {e}", file=sys.stderr)
            finally:
                self.client = None

    def ensure_connected(self) -> Client:
        """Ensure client is connected.

        Returns:
            The connected client

        Raises:
            RuntimeError: If not connected
        """
        if not self.client:
            raise RuntimeError("Not connected to Temporal server. Connection may have failed or been lost.")
        return self.client

    def _load_client_certs(self) -> tuple[Optional[bytes], Optional[bytes]]:
        """Load mTLS client certificate and key from disk.

        Returns:
            Tuple of (client_cert_bytes, client_key_bytes). Both are None when
            no certificate paths are configured.

        Raises:
            FileNotFoundError: If a configured path does not exist.
            ValueError: If only one of cert/key is provided.
        """
        if not self.tls_client_cert_path and not self.tls_client_key_path:
            return None, None

        if bool(self.tls_client_cert_path) != bool(self.tls_client_key_path):
            raise ValueError("Both TEMPORAL_TLS_CLIENT_CERT_PATH and TEMPORAL_TLS_CLIENT_KEY_PATH " "must be set together for mTLS.")

        assert self.tls_client_cert_path is not None
        assert self.tls_client_key_path is not None
        with open(self.tls_client_cert_path, "rb") as f:
            client_cert = f.read()
        with open(self.tls_client_key_path, "rb") as f:
            client_key = f.read()

        print(
            f"Loaded mTLS client certificate from {self.tls_client_cert_path}",
            file=sys.stderr,
        )
        return client_cert, client_key

    def _load_server_ca(self) -> Optional[bytes]:
        """Load the server CA certificate from disk, if configured.

        Returns:
            The CA certificate bytes, or None when no path is configured.

        Raises:
            FileNotFoundError: If the configured path does not exist.
        """
        if not self.tls_ca_path:
            return None

        with open(self.tls_ca_path, "rb") as f:
            ca_bytes = f.read()

        print(f"Loaded server CA certificate from {self.tls_ca_path}", file=sys.stderr)
        return ca_bytes

    def _determine_tls_config(self) -> Optional[TLSConfig]:
        """Determine TLS configuration based on settings, hostname, and credentials.

        Any of the following inputs forces TLS on, regardless of ``tls_enabled``:

        - mTLS client cert + key
        - Server CA cert path
        - SNI / server name override
        - API key

        When TLS is enabled, the resulting :class:`TLSConfig` composes every
        provided knob: mTLS material, custom server CA, and SNI override may be
        used together.

        Returns:
            TLS configuration or ``None`` if TLS should not be used.
        """
        client_cert, client_key = self._load_client_certs()
        server_ca = self._load_server_ca()

        explicit_tls_inputs = bool((client_cert and client_key) or server_ca is not None or self.tls_server_name or self.api_key)

        if explicit_tls_inputs:
            return self._build_tls_config(
                client_cert=client_cert,
                client_key=client_key,
                server_ca=server_ca,
            )

        # Priority: explicit tls_enabled setting > auto-detect from hostname
        if self.tls_enabled is True:
            return TLSConfig()
        elif self.tls_enabled is False:
            return None
        elif self._is_remote_host():
            # Auto-detect: enable TLS for remote connections
            return TLSConfig()
        else:
            # Auto-detect: disable TLS for local connections
            return None

    def _build_tls_config(
        self,
        client_cert: Optional[bytes],
        client_key: Optional[bytes],
        server_ca: Optional[bytes],
    ) -> TLSConfig:
        """Construct a :class:`TLSConfig` populated only with the fields we have.

        Empty fields are omitted so we get the SDK defaults (e.g. system trust
        store when no custom CA is configured).
        """
        kwargs: dict = {}
        if client_cert and client_key:
            kwargs["client_cert"] = client_cert
            kwargs["client_private_key"] = client_key
        if server_ca is not None:
            kwargs["server_root_ca_cert"] = server_ca
        if self.tls_server_name:
            kwargs["domain"] = self.tls_server_name
        return TLSConfig(**kwargs)

    def _is_remote_host(self) -> bool:
        """Check if the host is a remote (non-local) host.

        Returns:
            True if host is remote, False if local
        """
        local_hosts = ["localhost", "127.0.0.1", "host.docker.internal"]
        return not any(local_host in self.temporal_host for local_host in local_hosts)

    def _log_connection_info(self, tls_config: Optional[TLSConfig]):
        """Log connection information for debugging.

        Args:
            tls_config: The TLS configuration being used
        """
        if self.tls_enabled is True:
            print(f"Connecting to {self.temporal_host} with TLS enabled (explicit)", file=sys.stderr)
        elif self.tls_enabled is False:
            print(f"Connecting to {self.temporal_host} without TLS (explicit)", file=sys.stderr)
        elif tls_config is not None:
            print(f"Connecting to {self.temporal_host} with TLS enabled (auto-detected for remote host)", file=sys.stderr)
        else:
            print(f"Connecting to {self.temporal_host} without TLS (auto-detected for local host)", file=sys.stderr)

        print(f"Namespace: {self.namespace}", file=sys.stderr)
        print(f"TLS Enabled: {tls_config is not None}", file=sys.stderr)
        if tls_config is not None and self.tls_server_name:
            print(f"TLS server name (SNI): {self.tls_server_name}", file=sys.stderr)
