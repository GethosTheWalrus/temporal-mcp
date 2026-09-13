"""Tests for request-specific Temporal namespace routing."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from temporal_mcp.server import TemporalMCPServer
from temporal_mcp.tools.tool_definitions import get_all_tools


@pytest.mark.asyncio
async def test_explicit_namespace_overrides_default_and_is_removed_from_handler_args():
    server = TemporalMCPServer(namespace="production", allowed_namespaces=["production", "payments"])
    payments_client = object()
    server.client_manager.get_client = AsyncMock(return_value=payments_client)

    with patch("temporal_mcp.server.workflow_handlers.describe_workflow", new=AsyncMock(return_value=[])) as handler:
        result = await server._execute_tool("describe_workflow", {"workflow_id": "order-1", "namespace": "payments"})

    assert result == []
    server.client_manager.get_client.assert_awaited_once_with("payments")
    handler.assert_awaited_once_with(payments_client, {"workflow_id": "order-1"})


@pytest.mark.asyncio
async def test_omitted_namespace_uses_configured_default():
    server = TemporalMCPServer(namespace="production")
    production_client = object()
    server.client_manager.get_client = AsyncMock(return_value=production_client)

    with patch("temporal_mcp.server.workflow_handlers.describe_workflow", new=AsyncMock(return_value=[])) as handler:
        await server._execute_tool("describe_workflow", {"workflow_id": "order-1"})

    server.client_manager.get_client.assert_awaited_once_with("production")
    handler.assert_awaited_once_with(production_client, {"workflow_id": "order-1"})


@pytest.mark.asyncio
@pytest.mark.parametrize("namespace", ["", "unknown"])
async def test_invalid_namespace_is_rejected_before_connect(namespace):
    server = TemporalMCPServer(namespace="default", allowed_namespaces=["default", "payments"])
    server.client_manager.get_client = AsyncMock()

    result = await server._execute_tool("describe_workflow", {"workflow_id": "order-1", "namespace": namespace})
    payload = json.loads(result[0].text)

    assert payload["error_type"] == "ValueError"
    server.client_manager.get_client.assert_not_awaited()


def test_all_tool_schemas_include_optional_namespace():
    tools = get_all_tools(["default", "payments"])

    assert tools
    for tool in tools:
        input_schema = getattr(tool, "input_schema", None) or tool.inputSchema
        namespace_schema = input_schema["properties"]["namespace"]
        assert namespace_schema["enum"] == ["default", "payments"]
        assert "namespace" not in input_schema.get("required", [])


def test_wildcard_schema_does_not_restrict_namespace_values():
    server = TemporalMCPServer(allowed_namespaces=["*"])

    tools = get_all_tools(server.client_manager.allowed_namespaces)

    assert all("enum" not in (getattr(tool, "input_schema", None) or tool.inputSchema)["properties"]["namespace"] for tool in tools)
