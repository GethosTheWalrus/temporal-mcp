"""Tests for workflow handler tools."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from temporal_mcp.handlers import workflow_handlers


class TestStartWorkflow:
    @pytest.mark.asyncio
    async def test_start_workflow_success(self, mock_client):
        mock_handle = AsyncMock()
        mock_handle.id = "test-workflow-123"
        mock_handle.result_run_id = "run-456"
        mock_client.start_workflow.return_value = mock_handle

        args = {
            "workflow_name": "TestWorkflow",
            "workflow_id": "test-workflow-123",
            "task_queue": "test-queue",
            "args": {"key": "value"},
        }

        result = await workflow_handlers.start_workflow(mock_client, args)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["workflow_id"] == "test-workflow-123"
        assert response["run_id"] == "run-456"
        assert response["status"] == "started"
        mock_client.start_workflow.assert_called_once()


class TestCancelWorkflow:
    @pytest.mark.asyncio
    async def test_cancel_workflow_success(self, mock_client):
        mock_handle = AsyncMock()
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)

        result = await workflow_handlers.cancel_workflow(mock_client, {"workflow_id": "test-workflow-123"})

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "cancelled"
        mock_handle.cancel.assert_called_once()


class TestTerminateWorkflow:
    @pytest.mark.asyncio
    async def test_terminate_workflow_success(self, mock_client):
        mock_handle = AsyncMock()
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)

        args = {"workflow_id": "test-workflow-123", "reason": "Test termination"}
        result = await workflow_handlers.terminate_workflow(mock_client, args)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "terminated"
        assert response["reason"] == "Test termination"
        mock_handle.terminate.assert_called_once_with("Test termination")


class TestGetWorkflowResult:
    @pytest.mark.asyncio
    async def test_get_workflow_result_success(self, mock_client):
        mock_handle = AsyncMock()
        mock_handle.result.return_value = {"output": "success", "value": 42}
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)

        result = await workflow_handlers.get_workflow_result(mock_client, {"workflow_id": "test-workflow-123"})

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["result"]["output"] == "success"
        assert response["result"]["value"] == 42


class TestDescribeWorkflow:
    @pytest.mark.asyncio
    async def test_describe_workflow_success(self, mock_client):
        mock_description = MagicMock()
        mock_description.id = "test-workflow-123"
        mock_description.run_id = "run-456"
        mock_description.workflow_type = "TestWorkflow"
        mock_description.status = 1  # RUNNING
        mock_description.start_time = datetime(2025, 10, 30, 12, 0, 0)
        mock_description.execution_time = None
        mock_description.close_time = None

        mock_handle = AsyncMock()
        mock_handle.describe.return_value = mock_description
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)

        result = await workflow_handlers.describe_workflow(mock_client, {"workflow_id": "test-workflow-123"})

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["workflow_id"] == "test-workflow-123"
        assert response["workflow_type"] == "TestWorkflow"
        assert response["status"] == "WORKFLOW_EXECUTION_STATUS_RUNNING"


class TestListWorkflows:
    @pytest.mark.asyncio
    async def test_list_workflows_success(self, mock_client):
        mock_wf1 = MagicMock()
        mock_wf1.id = "workflow-1"
        mock_wf1.run_id = "run-1"
        mock_wf1.workflow_type = "TestWorkflow"
        mock_wf1.status = 2  # COMPLETED
        mock_wf1.start_time = datetime(2025, 10, 30, 12, 0, 0)

        mock_wf2 = MagicMock()
        mock_wf2.id = "workflow-2"
        mock_wf2.run_id = "run-2"
        mock_wf2.workflow_type = "TestWorkflow"
        mock_wf2.status = 1  # RUNNING
        mock_wf2.start_time = datetime(2025, 10, 30, 13, 0, 0)

        async def mock_list_workflows(query):
            for wf in [mock_wf1, mock_wf2]:
                yield wf

        mock_client.list_workflows = mock_list_workflows

        result = await workflow_handlers.list_workflows(
            mock_client, {"query": "WorkflowType='TestWorkflow'", "limit": 10}
        )

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert len(response["workflows"]) == 2
        assert response["workflows"][0]["workflow_id"] == "workflow-1"
        assert response["workflows"][1]["workflow_id"] == "workflow-2"


class TestGetWorkflowHistory:
    @pytest.mark.asyncio
    async def test_get_workflow_history_success(self, mock_client):
        mock_event1 = MagicMock()
        mock_event1.event_id = 1
        mock_event1.event_type = "WorkflowExecutionStarted"
        mock_event1.event_time = datetime(2025, 10, 30, 12, 0, 0)

        mock_event2 = MagicMock()
        mock_event2.event_id = 2
        mock_event2.event_type = "ActivityTaskScheduled"
        mock_event2.event_time = datetime(2025, 10, 30, 12, 0, 1)

        async def mock_fetch_history_events():
            for event in [mock_event1, mock_event2]:
                yield event

        mock_handle = AsyncMock()
        mock_handle.fetch_history_events = mock_fetch_history_events
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)

        result = await workflow_handlers.get_workflow_history(
            mock_client, {"workflow_id": "test-workflow-123", "limit": 100}
        )

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["workflow_id"] == "test-workflow-123"
        assert len(response["events"]) == 2
        assert response["events"][0]["event_type"] == "WorkflowExecutionStarted"
