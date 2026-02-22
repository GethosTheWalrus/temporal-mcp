"""Tests for error handling in handler tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock

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
