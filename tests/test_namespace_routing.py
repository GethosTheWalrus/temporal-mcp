"""Tests for request-specific Temporal namespace routing."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from mcp.types import CallToolRequestParams

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

    result = await server._call_tool(None, CallToolRequestParams(name="describe_workflow", arguments={"workflow_id": "order-1", "namespace": namespace}))
    payload = json.loads(result.content[0].text)

    assert payload["error_type"] == "ValueError"
    assert result.model_dump(by_alias=True)["isError"] is True
    server.client_manager.get_client.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("allowed_namespaces", [None, ["*"]])
@pytest.mark.parametrize("namespace", [None, "", "   ", 0, False, [], {}])
async def test_invalid_namespace_cannot_dispatch_destructive_tool(namespace, allowed_namespaces):
    server = TemporalMCPServer(namespace="production", allowed_namespaces=allowed_namespaces)
    server.client_manager.get_client = AsyncMock()
    params = CallToolRequestParams.model_validate_json(json.dumps({"name": "terminate_workflow", "arguments": {"workflow_id": "order-1", "namespace": namespace}}))

    with patch("temporal_mcp.server.workflow_handlers.terminate_workflow", new=AsyncMock()) as handler:
        result = await server._call_tool(None, params)

    assert result.model_dump(by_alias=True)["isError"] is True
    assert json.loads(result.content[0].text)["error_type"] == "ValueError"
    server.client_manager.get_client.assert_not_called()
    handler.assert_not_called()
    assert "namespace" in params.arguments
    assert params.arguments["namespace"] == namespace


@pytest.mark.asyncio
@pytest.mark.parametrize("arguments, expected_namespace", [({"workflow_id": "order-1"}, "production"), ({"workflow_id": "order-1", "namespace": " payments "}, "payments")])
async def test_mcp_dispatch_preserves_default_and_explicit_namespace(arguments, expected_namespace):
    server = TemporalMCPServer(namespace="production", allowed_namespaces=["production", "payments"])
    client = object()
    server.client_manager.get_client = AsyncMock(return_value=client)
    params = CallToolRequestParams.model_validate_json(json.dumps({"name": "terminate_workflow", "arguments": arguments}))

    with patch("temporal_mcp.server.workflow_handlers.terminate_workflow", new=AsyncMock(return_value=[])) as handler:
        result = await server._call_tool(None, params)

    assert result.model_dump(by_alias=True)["isError"] is False
    server.client_manager.get_client.assert_awaited_once_with(expected_namespace)
    handler.assert_awaited_once_with(client, {"workflow_id": "order-1"})
    assert params.arguments == arguments


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
