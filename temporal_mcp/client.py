"""Temporal client management and connection handling."""

import asyncio
import sys
from typing import Optional, Sequence

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
        api_key: Optional[str] = None,
        allowed_namespaces: Optional[Sequence[str]] = None,
    ):
        """Initialize the Temporal client manager.

        Args:
            temporal_host: The Temporal server host and port
            namespace: The Temporal namespace to use
            tls_enabled: Whether to use TLS for connection (None = auto-detect, True = force enable, False = force disable)
            tls_client_cert_path: Path to the TLS client certificate file (for mTLS / Temporal Cloud)
            tls_client_key_path: Path to the TLS client private key file (for mTLS / Temporal Cloud)
            api_key: API key for Temporal Cloud authentication
            allowed_namespaces: Namespaces callers may select. None permits only the
                configured default; ["*"] permits any namespace.
        """
        self.temporal_host = temporal_host
        if not isinstance(namespace, str) or not namespace.strip():
            raise ValueError("Configured namespace must be a non-empty string")
        self.namespace = namespace.strip()
        self.tls_enabled = tls_enabled
        self.tls_client_cert_path = tls_client_cert_path
        self.tls_client_key_path = tls_client_key_path
        self.api_key = api_key
        self.allowed_namespaces = self._normalize_allowed_namespaces(allowed_namespaces)
        self.client: Optional[Client] = None
        self._connect_lock = asyncio.Lock()

    async def connect(self) -> Client:
        """Connect to Temporal server.

        Returns:
            Connected Temporal client

        Raises:
            Exception: If connection fails
        """
        if self.client:
            return self.client

        async with self._connect_lock:
            if self.client:
                return self.client

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
        """Release the Temporal client and its shared service connection."""
        self.client = None

    async def get_client(self, namespace: Optional[str] = None) -> Client:
        """Return a client bound to an allowed namespace."""
        selected_namespace = self.resolve_namespace(namespace)
        base_client = await self.connect()
        if selected_namespace == self.namespace:
            return base_client

        config = base_client.config()
        config["namespace"] = selected_namespace
        return Client(**config)

    def resolve_namespace(self, namespace: Optional[str] = None) -> str:
        """Resolve and authorize a request-specific namespace."""
        selected_namespace = self.namespace if namespace is None else namespace
        if not isinstance(selected_namespace, str) or not selected_namespace.strip():
            raise ValueError("Namespace must be a non-empty string")
        selected_namespace = selected_namespace.strip()
        if self.allowed_namespaces is not None and selected_namespace not in self.allowed_namespaces:
            raise ValueError(f"Namespace '{selected_namespace}' is not allowed")
        return selected_namespace

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

    def _normalize_allowed_namespaces(self, allowed_namespaces: Optional[Sequence[str]]) -> Optional[frozenset[str]]:
        """Normalize namespace policy; None represents an unrestricted policy."""
        if allowed_namespaces is None:
            return frozenset({self.namespace})
        if isinstance(allowed_namespaces, str):
            raise TypeError("allowed_namespaces must be a sequence of namespace strings")

        if any(not isinstance(namespace, str) for namespace in allowed_namespaces):
            raise ValueError("Allowed namespaces must contain only strings")
        normalized = [namespace.strip() for namespace in allowed_namespaces]
        if not normalized or any(not namespace for namespace in normalized):
            raise ValueError("Allowed namespaces must contain only non-empty values")
        if "*" in normalized:
            if len(normalized) != 1:
                raise ValueError("'*' cannot be combined with explicit allowed namespaces")
            return None

        result = frozenset(normalized)
        if self.namespace not in result:
            raise ValueError(f"Configured namespace '{self.namespace}' must be included in allowed namespaces")
        return result

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

    def _determine_tls_config(self) -> Optional[TLSConfig]:
        """Determine TLS configuration based on settings, hostname, and client certs.

        Returns:
            TLS configuration or None
        """
        client_cert, client_key = self._load_client_certs()

        # If mTLS certs are provided, always enable TLS regardless of other settings
        if client_cert and client_key:
            return TLSConfig(
                client_cert=client_cert,
                client_private_key=client_key,
            )

        # API key auth requires TLS
        if self.api_key:
            return TLSConfig()

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
