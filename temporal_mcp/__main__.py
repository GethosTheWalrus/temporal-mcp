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
from typing import Optional

from temporal_mcp.auth import CodecTokenProvider
from temporal_mcp.codec import CodecSettings
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
        "--api-key",
        metavar="KEY",
        default=None,
        help="API key for Temporal Cloud authentication (env: TEMPORAL_API_KEY)",
    )
    parser.add_argument(
        "--codec-endpoint",
        metavar="URL",
        default=None,
        help="Base URL of a codec server used to decode payloads and failure messages (env: TEMPORAL_CODEC_ENDPOINT)",
    )
    parser.add_argument(
        "--codec-auth",
        metavar="HEADER",
        default=None,
        help='Authorization header value sent to the codec server, e.g. "Bearer <token>" (env: TEMPORAL_CODEC_AUTH)',
    )
    parser.add_argument(
        "--codec-token-cache",
        metavar="PATH",
        default=None,
        help="Writable token cache file; enables OAuth token refresh and the codec_login tool, and takes precedence over --codec-auth (env: TEMPORAL_CODEC_TOKEN_CACHE)",
    )
    parser.add_argument(
        "--codec-oauth-url",
        metavar="URL",
        default=None,
        help="Base URL of the Auth0-compatible authorization server; required with --codec-token-cache (env: TEMPORAL_CODEC_OAUTH_URL)",
    )
    parser.add_argument(
        "--codec-oauth-client-id",
        metavar="ID",
        default=None,
        help="OAuth client ID for the device-code and refresh grants; required with --codec-token-cache (env: TEMPORAL_CODEC_OAUTH_CLIENT_ID)",
    )
    parser.add_argument(
        "--codec-oauth-audience",
        metavar="AUDIENCE",
        default=None,
        help="OAuth audience requested at login; required with --codec-token-cache (env: TEMPORAL_CODEC_OAUTH_AUDIENCE)",
    )
    parser.add_argument(
        "--transport",
        default=None,
        choices=["stdio", "http"],
        type=str.lower,
        help="stdio, or streamable HTTP served at /mcp (env: TEMPORAL_MCP_TRANSPORT, default: stdio)",
    )
    parser.add_argument(
        "--http-host",
        metavar="HOST",
        default=None,
        help="Address to listen on with --transport http (env: TEMPORAL_MCP_HTTP_HOST, default: 127.0.0.1)",
    )
    parser.add_argument(
        "--http-port",
        metavar="PORT",
        default=None,
        type=int,
        help="Port to listen on with --transport http (env: TEMPORAL_MCP_HTTP_PORT, default: 8000)",
    )
    return parser.parse_args()


_LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")


def _http_settings(args: argparse.Namespace) -> tuple[str, int, Optional[str]]:
    """Resolve the HTTP listener, refusing to serve unauthenticated on a non-loopback address."""
    host = args.http_host or os.environ.get("TEMPORAL_MCP_HTTP_HOST", "127.0.0.1")
    try:
        port = args.http_port or int(os.environ.get("TEMPORAL_MCP_HTTP_PORT", "8000"))
    except ValueError:
        raise SystemExit("TEMPORAL_MCP_HTTP_PORT must be an integer")
    # Env only: a token on the command line is visible to every local user in the process list.
    bearer_token = os.environ.get("TEMPORAL_MCP_HTTP_BEARER_TOKEN") or None
    allow_unauthenticated = os.environ.get("TEMPORAL_MCP_HTTP_ALLOW_UNAUTHENTICATED", "").lower() == "true"
    if not bearer_token and host not in _LOOPBACK_HOSTS and not allow_unauthenticated:
        raise SystemExit(
            f"Refusing to serve HTTP on {host} without TEMPORAL_MCP_HTTP_BEARER_TOKEN: anyone who reaches it "
            "acts on Temporal with this server's credentials. Set a token, listen on loopback, or set "
            "TEMPORAL_MCP_HTTP_ALLOW_UNAUTHENTICATED=true if another layer authenticates callers."
        )
    return host, port, bearer_token


def _build_codec(args: argparse.Namespace) -> Optional[CodecSettings]:
    """Build the codec settings from CLI arguments and environment variables, exiting with a message on invalid combinations."""
    endpoint = args.codec_endpoint or os.environ.get("TEMPORAL_CODEC_ENDPOINT")
    auth = args.codec_auth or os.environ.get("TEMPORAL_CODEC_AUTH")
    token_cache = args.codec_token_cache or os.environ.get("TEMPORAL_CODEC_TOKEN_CACHE")
    if not endpoint:
        if auth or token_cache:
            raise SystemExit("--codec-auth and --codec-token-cache require --codec-endpoint (TEMPORAL_CODEC_ENDPOINT)")
        return None

    token_provider = None
    if token_cache:
        oauth = {
            "--codec-oauth-url (TEMPORAL_CODEC_OAUTH_URL)": args.codec_oauth_url or os.environ.get("TEMPORAL_CODEC_OAUTH_URL"),
            "--codec-oauth-client-id (TEMPORAL_CODEC_OAUTH_CLIENT_ID)": args.codec_oauth_client_id or os.environ.get("TEMPORAL_CODEC_OAUTH_CLIENT_ID"),
            "--codec-oauth-audience (TEMPORAL_CODEC_OAUTH_AUDIENCE)": args.codec_oauth_audience or os.environ.get("TEMPORAL_CODEC_OAUTH_AUDIENCE"),
        }
        missing = [name for name, value in oauth.items() if not value]
        if missing:
            raise SystemExit(f"--codec-token-cache requires: {', '.join(missing)}")
        login_url, client_id, audience = oauth.values()
        try:
            token_provider = CodecTokenProvider(token_cache, login_url=str(login_url), client_id=str(client_id), audience=str(audience))
        except ValueError as e:
            raise SystemExit(str(e))

    try:
        return CodecSettings(endpoint=endpoint, auth=auth, token_provider=token_provider)
    except ValueError as e:
        raise SystemExit(str(e))


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

    # API key authentication (for Temporal Cloud)
    api_key = args.api_key or os.environ.get("TEMPORAL_API_KEY")
    allowed_namespaces_raw = os.environ.get("TEMPORAL_ALLOWED_NAMESPACES")
    allowed_namespaces = allowed_namespaces_raw.split(",") if allowed_namespaces_raw is not None else None

    codec = _build_codec(args)

    transport = args.transport or os.environ.get("TEMPORAL_MCP_TRANSPORT", "stdio").lower()
    if transport not in ("stdio", "http"):
        raise SystemExit(f"TEMPORAL_MCP_TRANSPORT must be stdio or http (got {transport!r})")
    http_settings = _http_settings(args) if transport == "http" else None

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
        allowed_namespaces=allowed_namespaces,
        codec=codec,
    )
    if http_settings:
        host, port, bearer_token = http_settings
        print(f"Serving streamable HTTP on {host}:{port}/mcp (bearer token: {'required' if bearer_token else 'not required'})", file=sys.stderr)
        asyncio.run(server.run_http(host, port, bearer_token))
    else:
        asyncio.run(server.run())


if __name__ == "__main__":
    main()
