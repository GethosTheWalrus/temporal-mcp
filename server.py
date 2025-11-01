"""Entry point for Temporal MCP Server."""

import asyncio
import os
import sys

from temporal_mcp.server import TemporalMCPServer


async def main():
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
    
    print(f"Starting MCP server with TEMPORAL_HOST={temporal_host}, TLS={tls_enabled}", file=sys.stderr)
    
    server = TemporalMCPServer(
        temporal_host=temporal_host,
        namespace=namespace,
        tls_enabled=tls_enabled
    )
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
