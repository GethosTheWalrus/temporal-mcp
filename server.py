"""Entry point for Temporal MCP Server (Docker / standalone use).

For pip-installed usage, prefer:
  temporal-mcp-server        (CLI)
  python -m temporal_mcp     (module)
"""

from temporal_mcp.__main__ import main

if __name__ == "__main__":
    main()
