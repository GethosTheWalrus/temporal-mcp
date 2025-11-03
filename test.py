"""Unit tests for the Temporal MCP Server tools."""
import asyncio
import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from temporal_mcp.server import TemporalMCPServer
from temporal_mcp.handlers import workflow_handlers, query_handlers, batch_handlers, schedule_handlers
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
    client = AsyncMock()
    return client


class TestStartWorkflow:
    """Tests for start_workflow tool."""
    
    @pytest.mark.asyncio
    async def test_start_workflow_success(self, mcp_server, mock_client):
        """Test successfully starting a workflow."""
        # Mock workflow handle
        mock_handle = AsyncMock()
        mock_handle.id = "test-workflow-123"
        mock_handle.result_run_id = "run-456"
        mock_client.start_workflow.return_value = mock_handle
        
        args = {
            "workflow_name": "TestWorkflow",
            "workflow_id": "test-workflow-123",
            "task_queue": "test-queue",
            "args": {"key": "value"}
        }
        
        result = await workflow_handlers.start_workflow(mock_client, args)
        
        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["workflow_id"] == "test-workflow-123"
        assert response["run_id"] == "run-456"
        assert response["status"] == "started"
        
        mock_client.start_workflow.assert_called_once()
class TestQueryWorkflow:
    """Tests for query_workflow tool."""
    
    @pytest.mark.asyncio
    async def test_query_workflow_success(self, mcp_server, mock_client):
        """Test successfully querying a workflow."""
        
        
        # Mock workflow handle (get_workflow_handle is NOT async in real client)
        mock_handle = AsyncMock()
        mock_handle.query.return_value = {"status": "running", "progress": 50}
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        
        args = {
            "workflow_id": "test-workflow-123",
            "query_name": "get_status",
            "args": {}
        }
        
        result = await query_handlers.query_workflow(mock_client, args)
        
        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["query_result"]["status"] == "running"
        assert response["query_result"]["progress"] == 50
class TestSignalWorkflow:
    """Tests for signal_workflow tool."""
    
    @pytest.mark.asyncio
    async def test_signal_workflow_success(self, mcp_server, mock_client):
        """Test successfully signaling a workflow."""
        
        
        # Mock workflow handle
        mock_handle = AsyncMock()
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        
        args = {
            "workflow_id": "test-workflow-123",
            "signal_name": "update_status",
            "args": {"new_status": "paused"}
        }
        
        result = await query_handlers.signal_workflow(mock_client, args)
        
        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "signal_sent"
        
        mock_handle.signal.assert_called_once_with("update_status", {"new_status": "paused"})
class TestCancelWorkflow:
    """Tests for cancel_workflow tool."""
    
    @pytest.mark.asyncio
    async def test_cancel_workflow_success(self, mcp_server, mock_client):
        """Test successfully canceling a workflow."""
        
        
        # Mock workflow handle
        mock_handle = AsyncMock()
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        
        args = {"workflow_id": "test-workflow-123"}
        
        result = await workflow_handlers.cancel_workflow(mock_client, args)
        
        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "cancelled"
        
        mock_handle.cancel.assert_called_once()
class TestGetWorkflowResult:
    """Tests for get_workflow_result tool."""
    
    @pytest.mark.asyncio
    async def test_get_workflow_result_success(self, mcp_server, mock_client):
        """Test successfully getting workflow result."""
        
        
        # Mock workflow handle
        mock_handle = AsyncMock()
        mock_handle.result.return_value = {"output": "success", "value": 42}
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        
        args = {"workflow_id": "test-workflow-123"}
        
        result = await workflow_handlers.get_workflow_result(mock_client, args)
        
        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["result"]["output"] == "success"
        assert response["result"]["value"] == 42
class TestDescribeWorkflow:
    """Tests for describe_workflow tool."""
    
    @pytest.mark.asyncio
    async def test_describe_workflow_success(self, mcp_server, mock_client):
        """Test successfully describing a workflow."""
        
        
        # Mock workflow description
        mock_description = MagicMock()
        mock_description.id = "test-workflow-123"
        mock_description.run_id = "run-456"
        mock_description.workflow_type = "TestWorkflow"
        mock_description.status = 1  # Use integer enum value (1 = RUNNING)
        mock_description.start_time = datetime(2025, 10, 30, 12, 0, 0)
        mock_description.execution_time = None
        mock_description.close_time = None
        
        mock_handle = AsyncMock()
        mock_handle.describe.return_value = mock_description
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        
        args = {"workflow_id": "test-workflow-123"}
        
        result = await workflow_handlers.describe_workflow(mock_client, args)
        
        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["workflow_id"] == "test-workflow-123"
        assert response["workflow_type"] == "TestWorkflow"
        assert response["status"] == "WORKFLOW_EXECUTION_STATUS_RUNNING"


class TestListWorkflows:
    """Tests for list_workflows tool."""
    
    @pytest.mark.asyncio
    async def test_list_workflows_success(self, mcp_server, mock_client):
        """Test successfully listing workflows."""
        
        
        # Mock workflow list
        mock_workflow1 = MagicMock()
        mock_workflow1.id = "workflow-1"
        mock_workflow1.run_id = "run-1"
        mock_workflow1.workflow_type = "TestWorkflow"
        mock_workflow1.status = 2  # Use integer enum value (2 = COMPLETED)
        mock_workflow1.start_time = datetime(2025, 10, 30, 12, 0, 0)
        
        mock_workflow2 = MagicMock()
        mock_workflow2.id = "workflow-2"
        mock_workflow2.run_id = "run-2"
        mock_workflow2.workflow_type = "TestWorkflow"
        mock_workflow2.status = 1  # Use integer enum value (1 = RUNNING)
        mock_workflow2.start_time = datetime(2025, 10, 30, 13, 0, 0)
        
        async def mock_list_workflows(query):
            for wf in [mock_workflow1, mock_workflow2]:
                yield wf
        
        mock_client.list_workflows = mock_list_workflows
        
        args = {"query": "WorkflowType='TestWorkflow'", "limit": 10}
        
        result = await workflow_handlers.list_workflows(mock_client, args)
        
        assert len(result) == 1
        response = json.loads(result[0].text)
        assert len(response["workflows"]) == 2
        assert response["workflows"][0]["workflow_id"] == "workflow-1"
        assert response["workflows"][1]["workflow_id"] == "workflow-2"
class TestTerminateWorkflow:
    """Tests for terminate_workflow tool."""
    
    @pytest.mark.asyncio
    async def test_terminate_workflow_success(self, mcp_server, mock_client):
        """Test successfully terminating a workflow."""
        
        
        # Mock workflow handle
        mock_handle = AsyncMock()
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        
        args = {
            "workflow_id": "test-workflow-123",
            "reason": "Test termination"
        }
        
        result = await workflow_handlers.terminate_workflow(mock_client, args)
        
        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "terminated"
        assert response["reason"] == "Test termination"
        
        mock_handle.terminate.assert_called_once_with("Test termination")
class TestGetWorkflowHistory:
    """Tests for get_workflow_history tool."""
    
    @pytest.mark.asyncio
    async def test_get_workflow_history_success(self, mcp_server, mock_client):
        """Test successfully getting workflow history."""
        
        
        # Mock history events
        mock_event1 = MagicMock()
        mock_event1.event_id = 1
        mock_event1.event_type = "WorkflowExecutionStarted"
        mock_event1.event_time = datetime(2025, 10, 30, 12, 0, 0)
        
        mock_event2 = MagicMock()
        mock_event2.event_id = 2
        mock_event2.event_type = "ActivityTaskScheduled"
        mock_event2.event_time = datetime(2025, 10, 30, 12, 0, 1)
        
        async def mock_fetch_history():
            for event in [mock_event1, mock_event2]:
                yield event
        
        mock_handle = AsyncMock()
        mock_handle.fetch_history = mock_fetch_history
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        
        args = {"workflow_id": "test-workflow-123", "limit": 100}
        
        result = await workflow_handlers.get_workflow_history(mock_client, args)
        
        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["workflow_id"] == "test-workflow-123"
        assert len(response["events"]) == 2
        assert response["events"][0]["event_type"] == "WorkflowExecutionStarted"
class TestBatchSignal:
    """Tests for batch_signal tool."""
    
    @pytest.mark.asyncio
    async def test_batch_signal_success(self, mcp_server, mock_client):
        """Test successfully batch signaling workflows."""
        
        
        # Mock workflow list
        mock_workflow1 = MagicMock()
        mock_workflow1.id = "workflow-1"
        
        mock_workflow2 = MagicMock()
        mock_workflow2.id = "workflow-2"
        
        async def mock_list_workflows(query):
            for wf in [mock_workflow1, mock_workflow2]:
                yield wf
        
        mock_client.list_workflows = mock_list_workflows
        
        # Mock workflow handles
        mock_handle = AsyncMock()
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        
        args = {
            "query": "WorkflowType='TestWorkflow'",
            "signal_name": "pause",
            "args": {},
            "limit": 10
        }
        
        result = await batch_handlers.batch_signal(mock_client, args)
        
        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["signal_name"] == "pause"
        assert len(response["workflows_signaled"]) == 2
        assert "workflow-1" in response["workflows_signaled"]
        assert "workflow-2" in response["workflows_signaled"]
class TestBatchCancel:
    """Tests for batch_cancel tool."""
    
    @pytest.mark.asyncio
    async def test_batch_cancel_success(self, mcp_server, mock_client):
        """Test successfully batch canceling workflows."""
        
        
        # Mock workflow list
        mock_workflow1 = MagicMock()
        mock_workflow1.id = "workflow-1"
        
        async def mock_list_workflows(query):
            yield mock_workflow1
        
        mock_client.list_workflows = mock_list_workflows
        
        # Mock workflow handle
        mock_handle = AsyncMock()
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        
        args = {
            "query": "WorkflowType='TestWorkflow'",
            "limit": 10
        }
        
        result = await batch_handlers.batch_cancel(mock_client, args)
        
        assert len(result) == 1
        response = json.loads(result[0].text)
        assert len(response["cancelled_workflows"]) == 1
        assert "workflow-1" in response["cancelled_workflows"]
class TestBatchTerminate:
    """Tests for batch_terminate tool."""
    
    @pytest.mark.asyncio
    async def test_batch_terminate_success(self, mcp_server, mock_client):
        """Test successfully batch terminating workflows."""
        
        
        # Mock workflow list
        mock_workflow1 = MagicMock()
        mock_workflow1.id = "workflow-1"
        
        async def mock_list_workflows(query):
            yield mock_workflow1
        
        mock_client.list_workflows = mock_list_workflows
        
        # Mock workflow handle
        mock_handle = AsyncMock()
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        
        args = {
            "query": "WorkflowType='TestWorkflow'",
            "reason": "Batch cleanup",
            "limit": 10
        }
        
        result = await batch_handlers.batch_terminate(mock_client, args)
        
        assert len(result) == 1
        response = json.loads(result[0].text)
        assert len(response["terminated_workflows"]) == 1
        assert response["reason"] == "Batch cleanup"
class TestScheduleOperations:
    """Tests for schedule management tools."""
    
    @pytest.mark.asyncio
    async def test_create_schedule_success(self, mcp_server, mock_client):
        """Test successfully creating a schedule."""
        
        mock_client.create_schedule = AsyncMock()
        
        args = {
            "schedule_id": "test-schedule",
            "workflow_name": "TestWorkflow",
            "task_queue": "test-queue",
            "cron": "0 9 * * *",
            "args": {}
        }
        
        result = await schedule_handlers.create_schedule(mock_client, args)
        
        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "created"
        assert response["schedule_id"] == "test-schedule"
        assert response["cron"] == "0 9 * * *"
    
    @pytest.mark.asyncio
    async def test_list_schedules_success(self, mcp_server, mock_client):
        """Test successfully listing schedules."""
        
        
        # Mock schedule list
        mock_schedule = MagicMock()
        mock_schedule.id = "test-schedule"
        mock_schedule.info.paused = False
        
        async def mock_list_schedules():
            yield mock_schedule
        
        mock_client.list_schedules = mock_list_schedules
        
        args = {"limit": 20}
        
        result = await schedule_handlers.list_schedules(mock_client, args)
        
        assert len(result) == 1
        response = json.loads(result[0].text)
        assert len(response["schedules"]) == 1
        assert response["schedules"][0]["schedule_id"] == "test-schedule"
    
    @pytest.mark.asyncio
    async def test_pause_schedule_success(self, mcp_server, mock_client):
        """Test successfully pausing a schedule."""
        
        
        mock_handle = AsyncMock()
        mock_client.get_schedule_handle = MagicMock(return_value=mock_handle)
        
        args = {
            "schedule_id": "test-schedule",
            "note": "Paused for maintenance"
        }
        
        result = await schedule_handlers.pause_schedule(mock_client, args)
        
        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "paused"
        assert response["schedule_id"] == "test-schedule"
        
        mock_handle.pause.assert_called_once_with(note="Paused for maintenance")
    
    @pytest.mark.asyncio
    async def test_unpause_schedule_success(self, mcp_server, mock_client):
        """Test successfully unpausing a schedule."""
        
        
        mock_handle = AsyncMock()
        mock_client.get_schedule_handle = MagicMock(return_value=mock_handle)
        
        args = {
            "schedule_id": "test-schedule",
            "note": "Maintenance complete"
        }
        
        result = await schedule_handlers.unpause_schedule(mock_client, args)
        
        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "unpaused"
        
        mock_handle.unpause.assert_called_once_with(note="Maintenance complete")
    
    @pytest.mark.asyncio
    async def test_delete_schedule_success(self, mcp_server, mock_client):
        """Test successfully deleting a schedule."""
        
        
        mock_handle = AsyncMock()
        mock_client.get_schedule_handle = MagicMock(return_value=mock_handle)
        
        args = {"schedule_id": "test-schedule"}
        
        result = await schedule_handlers.delete_schedule(mock_client, args)
        
        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "deleted"
        
        mock_handle.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_trigger_schedule_success(self, mcp_server, mock_client):
        """Test successfully triggering a schedule."""
        
        
        mock_handle = AsyncMock()
        mock_client.get_schedule_handle = MagicMock(return_value=mock_handle)
        
        args = {"schedule_id": "test-schedule"}
        
        result = await schedule_handlers.trigger_schedule(mock_client, args)
        
        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "triggered"
        
        mock_handle.trigger.assert_called_once()
class TestContinueAsNew:
    """Tests for continue_as_new tool."""
    
    @pytest.mark.asyncio
    async def test_continue_as_new_success(self, mcp_server, mock_client):
        """Test successfully sending continue-as-new signal."""
        
        
        mock_handle = AsyncMock()
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        
        args = {
            "workflow_id": "test-workflow-123",
            "signal_name": "continue_with_new_data",
            "signal_args": {"new_param": "value"}
        }
        
        result = await query_handlers.continue_as_new(mock_client, args)
        
        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "signal_sent"
        assert response["workflow_id"] == "test-workflow-123"
        assert "continue-as-new" in response["note"]
        
        mock_handle.signal.assert_called_once_with(
            "continue_with_new_data",
            {"new_param": "value"}
        )
class TestErrorHandling:
    """Tests for error handling in tools."""
    
    @pytest.mark.asyncio
    async def test_start_workflow_error(self, mcp_server, mock_client):
        """Test error handling when starting a workflow fails."""
        
        mock_client.start_workflow.side_effect = Exception("Connection error")
        
        args = {
            "workflow_name": "TestWorkflow",
            "workflow_id": "test-workflow-123",
            "task_queue": "test-queue"
        }
        
        with pytest.raises(Exception) as exc_info:
            await workflow_handlers.start_workflow(mock_client, args)
        
        assert "Connection error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_query_workflow_not_found(self, mcp_server, mock_client):
        """Test querying a non-existent workflow."""
        
        
        mock_handle = AsyncMock()
        mock_handle.query.side_effect = Exception("Workflow not found")
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        
        args = {
            "workflow_id": "non-existent",
            "query_name": "get_status"
        }
        
        with pytest.raises(Exception) as exc_info:
            await query_handlers.query_workflow(mock_client, args)
        
        assert "Workflow not found" in str(exc_info.value)
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
