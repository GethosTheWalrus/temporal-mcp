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
        tls_enabled: Optional[bool] = None
    ):
        """Initialize the Temporal client manager.
        
        Args:
            temporal_host: The Temporal server host and port
            namespace: The Temporal namespace to use
            tls_enabled: Whether to use TLS for connection (None = auto-detect, True = force enable, False = force disable)
        """
        self.temporal_host = temporal_host
        self.namespace = namespace
        self.tls_enabled = tls_enabled
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
    
    def _determine_tls_config(self) -> Optional[TLSConfig]:
        """Determine TLS configuration based on settings and hostname.
        
        Returns:
            TLS configuration or None
        """
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
