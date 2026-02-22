"""Shared fixtures for the Temporal MCP test suite."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock

from temporal_mcp.server import TemporalMCPServer


@pytest_asyncio.fixture
async def mcp_server():
    """Create a test MCP server instance."""
    server = TemporalMCPServer(temporal_host="localhost:7233")
    # Don't actually connect - tests use mock_client directly
    yield server
    # No need to disconnect since we never connected


@pytest.fixture
def mock_client():
    """Create a mock Temporal client."""
    return AsyncMock()
