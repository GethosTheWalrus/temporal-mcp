"""Entry point for Temporal MCP Server.

Supports:
  - `python -m temporal_mcp`
  - `temporal-mcp-server` CLI (installed via pip)
"""

import asyncio
import os
import sys

from temporal_mcp.server import TemporalMCPServer


def main():
    """Main entry point for the MCP server."""
    temporal_host = os.environ.get("TEMPORAL_HOST", "localhost:7233")
    namespace = os.environ.get("TEMPORAL_NAMESPACE", "default")

    # Parse TLS setting: None (auto-detect), True (force enable), False (force disable)
    tls_env = os.environ.get("TEMPORAL_TLS_ENABLED", "").lower()
    if tls_env == "true":
        tls_enabled = True
    elif tls_env == "false":
        tls_enabled = False
    else:
        tls_enabled = None  # Auto-detect

    # mTLS client certificate paths (for Temporal Cloud)
    tls_client_cert_path = os.environ.get("TEMPORAL_TLS_CLIENT_CERT_PATH")
    tls_client_key_path = os.environ.get("TEMPORAL_TLS_CLIENT_KEY_PATH")

    # API key authentication (for Temporal Cloud)
    api_key = os.environ.get("TEMPORAL_API_KEY")

    print(
        f"Starting MCP server with TEMPORAL_HOST={temporal_host}, TLS={tls_enabled}",
        file=sys.stderr,
    )
    if tls_client_cert_path:
        print(f"mTLS client cert: {tls_client_cert_path}", file=sys.stderr)
    if tls_client_key_path:
        print(f"mTLS client key:  {tls_client_key_path}", file=sys.stderr)
    if api_key:
        print("API key authentication: enabled", file=sys.stderr)

    server = TemporalMCPServer(
        temporal_host=temporal_host,
        namespace=namespace,
        tls_enabled=tls_enabled,
        tls_client_cert_path=tls_client_cert_path,
        tls_client_key_path=tls_client_key_path,
        api_key=api_key,
    )
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
