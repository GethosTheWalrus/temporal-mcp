"""Tests for error handling in handler tools."""

import asyncio
import json

import pytest
from unittest.mock import AsyncMock, MagicMock

from mcp.types import CallToolRequestParams, TextContent

from temporal_mcp.server import TemporalMCPServer
from temporal_mcp.handlers import workflow_handlers, query_handlers


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_start_workflow_error(self, mock_client):
        mock_client.start_workflow.side_effect = Exception("Connection error")

        args = {
            "workflow_name": "TestWorkflow",
            "workflow_id": "test-workflow-123",
            "task_queue": "test-queue",
        }

        with pytest.raises(Exception, match="Connection error"):
            await workflow_handlers.start_workflow(mock_client, args)

    @pytest.mark.asyncio
    async def test_query_workflow_not_found(self, mock_client):
        mock_handle = AsyncMock()
        mock_handle.query.side_effect = Exception("Workflow not found")
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)

        args = {"workflow_id": "non-existent", "query_name": "get_status"}

        with pytest.raises(Exception, match="Workflow not found"):
            await query_handlers.query_workflow(mock_client, args)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "params, client_side_effect, expected_type",
        [
            (CallToolRequestParams(name="describe_workflow", arguments={"workflow_id": "wf", "namespace": ""}), None, "ValueError"),
            (CallToolRequestParams(name="describe_workflow", arguments={"workflow_id": "wf"}), RuntimeError("dial failed"), "connection_error"),
            (CallToolRequestParams(name="no_such_tool", arguments={}), None, "unknown_tool"),
        ],
    )
    async def test_mcp_call_tool_marks_application_failures_as_errors(self, params, client_side_effect, expected_type):
        server = TemporalMCPServer(namespace="default", allowed_namespaces=["default"])
        if client_side_effect is not None:
            server.client_manager.get_client = AsyncMock(side_effect=client_side_effect)
        else:
            server.client_manager.get_client = AsyncMock(return_value=object())

        result = await server._call_tool(None, params)
        payload = json.loads(result.content[0].text)

        assert result.model_dump(by_alias=True)["isError"] is True
        assert payload.get("type") == expected_type or payload.get("error_type") == expected_type

    @pytest.mark.asyncio
    async def test_mcp_call_tool_marks_handler_exceptions_as_errors(self):
        server = TemporalMCPServer(namespace="default")
        server.client_manager.get_client = AsyncMock(return_value=object())

        result = await server._call_tool(None, CallToolRequestParams(name="describe_workflow", arguments={"workflow_id": "wf"}))
        payload = json.loads(result.content[0].text)

        assert result.model_dump(by_alias=True)["isError"] is True
        assert payload["tool"] == "describe_workflow"

    @pytest.mark.asyncio
    async def test_mcp_call_tool_keeps_successful_results_non_errors(self):
        server = TemporalMCPServer(namespace="default")
        server.client_manager.get_client = AsyncMock(return_value=object())
        server._execute_tool = AsyncMock(return_value=[TextContent(type="text", text=json.dumps({"status": "ok"}))])

        result = await server._call_tool(None, CallToolRequestParams(name="describe_workflow", arguments={"workflow_id": "wf"}))

        assert result.model_dump(by_alias=True)["isError"] is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "tool, arguments, error_type",
        [
            ("get_workflow_result", {"workflow_id": "wf", "timeout": 1}, "timeout"),
            ("get_activity_result", {"activity_id": "act", "timeout": 1}, "timeout"),
            ("get_workflow_event", {"workflow_id": "wf", "event_id": 99}, "not_found"),
        ],
    )
    async def test_mcp_call_tool_marks_soft_handler_failures_as_errors(self, tool, arguments, error_type):
        server = TemporalMCPServer(namespace="default")
        client = MagicMock()
        workflow_handle = MagicMock()
        workflow_handle.result = AsyncMock(side_effect=asyncio.TimeoutError)

        async def empty_history():
            if False:
                yield None

        workflow_handle.fetch_history_events = empty_history
        activity_handle = MagicMock()
        activity_handle.result = AsyncMock(side_effect=asyncio.TimeoutError)
        client.get_workflow_handle.return_value = workflow_handle
        client.get_activity_handle.return_value = activity_handle
        server.client_manager.get_client = AsyncMock(return_value=client)

        result = await server._call_tool(None, CallToolRequestParams(name=tool, arguments=arguments))

        assert result.model_dump(by_alias=True)["isError"] is True
        assert json.loads(result.content[0].text)["type"] == error_type
