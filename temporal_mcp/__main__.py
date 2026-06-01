"""Entry point for Temporal MCP Server.

Supports:
  - `python -m temporal_mcp`
  - `temporal-mcp-server` CLI (installed via pip)

Configuration priority (highest → lowest):
  1. CLI arguments
  2. Environment variables
  3. Built-in defaults
"""

import argparse
import asyncio
import os
import sys

from temporal_mcp.server import TemporalMCPServer


def _parse_args() -> argparse.Namespace:
    """Parse optional CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="temporal-mcp-server",
        description="MCP server for Temporal workflow orchestration.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--host",
        metavar="HOST:PORT",
        default=None,
        help="Temporal server host and port (env: TEMPORAL_HOST, default: localhost:7233)",
    )
    parser.add_argument(
        "--namespace",
        metavar="NAMESPACE",
        default=None,
        help="Temporal namespace (env: TEMPORAL_NAMESPACE, default: default)",
    )
    parser.add_argument(
        "--tls-enabled",
        metavar="BOOL",
        default=None,
        choices=["true", "false"],
        type=str.lower,
        help="Force-enable or force-disable TLS; omit to auto-detect (env: TEMPORAL_TLS_ENABLED)",
    )
    parser.add_argument(
        "--tls-cert",
        metavar="PATH",
        default=None,
        help="Path to mTLS client certificate file (env: TEMPORAL_TLS_CLIENT_CERT_PATH)",
    )
    parser.add_argument(
        "--tls-key",
        metavar="PATH",
        default=None,
        help="Path to mTLS client private key file (env: TEMPORAL_TLS_CLIENT_KEY_PATH)",
    )
    parser.add_argument(
        "--tls-ca",
        metavar="PATH",
        default=None,
        help=("Path to a PEM CA certificate used to verify the server. " "Use this for clusters signed by a private/internal CA that is not in " "the system trust store (env: TEMPORAL_TLS_CA_PATH)"),
    )
    parser.add_argument(
        "--tls-server-name",
        metavar="NAME",
        default=None,
        help=(
            "Override the expected server name and TLS SNI value. "
            "Use this when connecting through an SNI-routed gateway whose backend "
            "cert is issued for a different name than --host (env: TEMPORAL_TLS_SERVER_NAME)"
        ),
    )
    parser.add_argument(
        "--api-key",
        metavar="KEY",
        default=None,
        help="API key for Temporal Cloud authentication (env: TEMPORAL_API_KEY)",
    )
    return parser.parse_args()


def main():
    """Main entry point for the MCP server."""
    args = _parse_args()

    # CLI arg → env var → built-in default
    temporal_host = args.host or os.environ.get("TEMPORAL_HOST", "localhost:7233")
    namespace = args.namespace or os.environ.get("TEMPORAL_NAMESPACE", "default")

    # Parse TLS setting: None (auto-detect), True (force enable), False (force disable)
    tls_raw = args.tls_enabled or os.environ.get("TEMPORAL_TLS_ENABLED", "").lower()
    if tls_raw == "true":
        tls_enabled = True
    elif tls_raw == "false":
        tls_enabled = False
    else:
        tls_enabled = None  # Auto-detect

    # mTLS client certificate paths (for Temporal Cloud)
    tls_client_cert_path = args.tls_cert or os.environ.get("TEMPORAL_TLS_CLIENT_CERT_PATH")
    tls_client_key_path = args.tls_key or os.environ.get("TEMPORAL_TLS_CLIENT_KEY_PATH")

    # Server CA certificate path and SNI / server-name override
    # (for clusters signed by a private CA, or SNI-routed gateways)
    tls_ca_path = args.tls_ca or os.environ.get("TEMPORAL_TLS_CA_PATH")
    tls_server_name = args.tls_server_name or os.environ.get("TEMPORAL_TLS_SERVER_NAME")

    # API key authentication (for Temporal Cloud)
    api_key = args.api_key or os.environ.get("TEMPORAL_API_KEY")

    print(
        f"Starting MCP server with TEMPORAL_HOST={temporal_host}, TLS={tls_enabled}",
        file=sys.stderr,
    )
    if tls_client_cert_path:
        print(f"mTLS client cert: {tls_client_cert_path}", file=sys.stderr)
    if tls_client_key_path:
        print(f"mTLS client key:  {tls_client_key_path}", file=sys.stderr)
    if tls_ca_path:
        print(f"Server CA cert:   {tls_ca_path}", file=sys.stderr)
    if tls_server_name:
        print(f"TLS server name:  {tls_server_name}", file=sys.stderr)
    if api_key:
        print("API key authentication: enabled", file=sys.stderr)

    server = TemporalMCPServer(
        temporal_host=temporal_host,
        namespace=namespace,
        tls_enabled=tls_enabled,
        tls_client_cert_path=tls_client_cert_path,
        tls_client_key_path=tls_client_key_path,
        tls_ca_path=tls_ca_path,
        tls_server_name=tls_server_name,
        api_key=api_key,
    )
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
