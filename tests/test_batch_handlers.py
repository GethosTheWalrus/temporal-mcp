"""Tests for batch handler tools."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from temporal_mcp.handlers import batch_handlers


class TestBatchSignal:
    @pytest.mark.asyncio
    async def test_batch_signal_success(self, mock_client):
        mock_wf1 = MagicMock()
        mock_wf1.id = "workflow-1"
        mock_wf2 = MagicMock()
        mock_wf2.id = "workflow-2"

        async def mock_list_workflows(query):
            for wf in [mock_wf1, mock_wf2]:
                yield wf

        mock_client.list_workflows = mock_list_workflows
        mock_handle = AsyncMock()
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)

        args = {
            "query": "WorkflowType='TestWorkflow'",
            "signal_name": "pause",
            "args": {},
            "limit": 10,
        }

        result = await batch_handlers.batch_signal(mock_client, args)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["signal_name"] == "pause"
        assert len(response["workflows_signaled"]) == 2
        assert "workflow-1" in response["workflows_signaled"]
        assert "workflow-2" in response["workflows_signaled"]


class TestBatchCancel:
    @pytest.mark.asyncio
    async def test_batch_cancel_success(self, mock_client):
        mock_wf1 = MagicMock()
        mock_wf1.id = "workflow-1"

        async def mock_list_workflows(query):
            yield mock_wf1

        mock_client.list_workflows = mock_list_workflows
        mock_handle = AsyncMock()
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)

        args = {"query": "WorkflowType='TestWorkflow'", "limit": 10}

        result = await batch_handlers.batch_cancel(mock_client, args)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert len(response["cancelled_workflows"]) == 1
        assert "workflow-1" in response["cancelled_workflows"]


class TestBatchTerminate:
    @pytest.mark.asyncio
    async def test_batch_terminate_success(self, mock_client):
        mock_wf1 = MagicMock()
        mock_wf1.id = "workflow-1"

        async def mock_list_workflows(query):
            yield mock_wf1

        mock_client.list_workflows = mock_list_workflows
        mock_handle = AsyncMock()
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)

        args = {
            "query": "WorkflowType='TestWorkflow'",
            "reason": "Batch cleanup",
            "limit": 10,
        }

        result = await batch_handlers.batch_terminate(mock_client, args)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert len(response["terminated_workflows"]) == 1
        assert response["reason"] == "Batch cleanup"
