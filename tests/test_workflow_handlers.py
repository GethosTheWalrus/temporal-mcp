"""Tests for workflow handler tools."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
from google.protobuf.timestamp_pb2 import Timestamp
from temporalio.api.common.v1 import ActivityType, Payloads, WorkflowExecution, WorkflowType
from temporalio.api.enums.v1 import EventType, RetryState
from temporalio.api.failure.v1 import ApplicationFailureInfo, Failure
from temporalio.api.history.v1 import (
    ActivityTaskCompletedEventAttributes,
    ActivityTaskFailedEventAttributes,
    ActivityTaskScheduledEventAttributes,
    ChildWorkflowExecutionFailedEventAttributes,
    HistoryEvent,
    StartChildWorkflowExecutionInitiatedEventAttributes,
    WorkflowExecutionStartedEventAttributes,
)
from temporalio.converter import default

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

        result = await workflow_handlers.list_workflows(mock_client, {"query": "WorkflowType='TestWorkflow'", "limit": 10})

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

        result = await workflow_handlers.get_workflow_history(mock_client, {"workflow_id": "test-workflow-123", "limit": 100})

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["workflow_id"] == "test-workflow-123"
        assert len(response["events"]) == 2
        assert response["events"][0]["event_type"] == "WorkflowExecutionStarted"

    @pytest.mark.asyncio
    async def test_get_workflow_history_includes_activity_failure_metadata(self, mock_client):
        scheduled_event = _history_event(
            event_id=8,
            event_type=EventType.EVENT_TYPE_ACTIVITY_TASK_SCHEDULED,
            activity_task_scheduled_event_attributes=ActivityTaskScheduledEventAttributes(
                activity_id="delete-volume-claim-abc123",
                activity_type=ActivityType(name="volume-claim-delete"),
            ),
        )
        failed_event = _history_event(
            event_id=12,
            event_type=EventType.EVENT_TYPE_ACTIVITY_TASK_FAILED,
            activity_task_failed_event_attributes=ActivityTaskFailedEventAttributes(
                scheduled_event_id=8,
                started_event_id=10,
                retry_state=RetryState.RETRY_STATE_MAXIMUM_ATTEMPTS_REACHED,
                failure=Failure(
                    message="activity failed",
                    source="PythonSDK",
                    stack_trace="stack trace",
                    application_failure_info=ApplicationFailureInfo(type="NullPointerException", non_retryable=False),
                    cause=Failure(message="root cause", application_failure_info=ApplicationFailureInfo(type="ValueError")),
                ),
            ),
        )

        async def mock_fetch_history_events():
            for event in [scheduled_event, failed_event]:
                yield event

        mock_handle = AsyncMock()
        mock_handle.fetch_history_events = mock_fetch_history_events
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)

        result = await workflow_handlers.get_workflow_history(mock_client, {"workflow_id": "test-workflow-123"})

        response = json.loads(result[0].text)
        failed_attrs = response["events"][1]["attributes"]

        assert response["events"][1]["event_type_name"] == "EVENT_TYPE_ACTIVITY_TASK_FAILED"
        assert failed_attrs["scheduled_event_id"] == 8
        assert failed_attrs["started_event_id"] == 10
        assert failed_attrs["activity"] == {"activity_id": "delete-volume-claim-abc123", "activity_type": "volume-claim-delete"}
        assert failed_attrs["retry_state"] == RetryState.RETRY_STATE_MAXIMUM_ATTEMPTS_REACHED
        assert failed_attrs["retry_state_name"] == "RETRY_STATE_MAXIMUM_ATTEMPTS_REACHED"
        assert failed_attrs["failure"]["message"] == "activity failed"
        assert failed_attrs["failure"]["source"] == "PythonSDK"
        assert failed_attrs["failure"]["stack_trace"] == "stack trace"
        assert failed_attrs["failure"]["type"] == "application_failure"
        assert failed_attrs["failure"]["application_failure"] == {"type": "NullPointerException", "non_retryable": False}
        assert failed_attrs["failure"]["cause"]["message"] == "root cause"
        assert "__raw__" not in failed_attrs
        assert "input" not in failed_attrs

    @pytest.mark.asyncio
    async def test_get_workflow_history_includes_child_workflow_metadata(self, mock_client):
        initiated_event = _history_event(
            event_id=5,
            event_type=EventType.EVENT_TYPE_START_CHILD_WORKFLOW_EXECUTION_INITIATED,
            start_child_workflow_execution_initiated_event_attributes=StartChildWorkflowExecutionInitiatedEventAttributes(
                workflow_id="child-workflow-id",
                workflow_type=WorkflowType(name="ChildWorkflow"),
                workflow_task_completed_event_id=4,
            ),
        )
        failed_event = _history_event(
            event_id=9,
            event_type=EventType.EVENT_TYPE_CHILD_WORKFLOW_EXECUTION_FAILED,
            child_workflow_execution_failed_event_attributes=ChildWorkflowExecutionFailedEventAttributes(
                initiated_event_id=5,
                started_event_id=6,
                workflow_execution=WorkflowExecution(workflow_id="child-workflow-id", run_id="child-run-id"),
                workflow_type=WorkflowType(name="ChildWorkflow"),
                retry_state=RetryState.RETRY_STATE_MAXIMUM_ATTEMPTS_REACHED,
                failure=Failure(message="child failed", application_failure_info=ApplicationFailureInfo(type="ChildError")),
            ),
        )

        async def mock_fetch_history_events():
            for event in [initiated_event, failed_event]:
                yield event

        mock_handle = AsyncMock()
        mock_handle.fetch_history_events = mock_fetch_history_events
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)

        result = await workflow_handlers.get_workflow_history(mock_client, {"workflow_id": "parent-workflow-id"})

        response = json.loads(result[0].text)
        initiated_attrs = response["events"][0]["attributes"]
        failed_attrs = response["events"][1]["attributes"]

        assert initiated_attrs["workflow_task_completed_event_id"] == 4
        assert initiated_attrs["workflow"] == {"workflow_id": "child-workflow-id", "workflow_type": "ChildWorkflow"}
        assert response["events"][1]["event_type_name"] == "EVENT_TYPE_CHILD_WORKFLOW_EXECUTION_FAILED"
        assert failed_attrs["initiated_event_id"] == 5
        assert failed_attrs["started_event_id"] == 6
        assert failed_attrs["workflow"] == {"workflow_id": "child-workflow-id", "workflow_type": "ChildWorkflow", "run_id": "child-run-id"}
        assert failed_attrs["retry_state_name"] == "RETRY_STATE_MAXIMUM_ATTEMPTS_REACHED"
        assert failed_attrs["failure"]["application_failure"] == {"type": "ChildError", "non_retryable": False}
        assert "__raw__" not in failed_attrs
        assert "result" not in failed_attrs


class TestGetWorkflowEvent:
    @pytest.mark.asyncio
    async def test_get_workflow_event_decodes_activity_result(self, mock_client):
        data_converter = default()

        scheduled_event = _history_event(
            event_id=8,
            event_type=EventType.EVENT_TYPE_ACTIVITY_TASK_SCHEDULED,
            activity_task_scheduled_event_attributes=ActivityTaskScheduledEventAttributes(
                activity_id="activity-123",
                activity_type=ActivityType(name="FetchCustomer"),
                input=Payloads(payloads=await data_converter.encode([{"customer_id": "123"}])),
            ),
        )
        completed_event = _history_event(
            event_id=12,
            event_type=EventType.EVENT_TYPE_ACTIVITY_TASK_COMPLETED,
            activity_task_completed_event_attributes=ActivityTaskCompletedEventAttributes(
                scheduled_event_id=8,
                started_event_id=10,
                result=Payloads(payloads=await data_converter.encode([{"status": "active"}])),
            ),
        )

        async def mock_fetch_history_events():
            for event in [scheduled_event, completed_event]:
                yield event

        mock_handle = AsyncMock()
        mock_handle.fetch_history_events = mock_fetch_history_events
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        mock_client.data_converter = data_converter

        result = await workflow_handlers.get_workflow_event(mock_client, {"workflow_id": "test-workflow-123", "event_id": 12})

        response = json.loads(result[0].text)
        event = response["event"]
        attrs = event["attributes"]

        assert response["workflow_id"] == "test-workflow-123"
        assert event["event_id"] == 12
        assert event["event_type_name"] == "EVENT_TYPE_ACTIVITY_TASK_COMPLETED"
        assert attrs["scheduled_event_id"] == 8
        assert attrs["started_event_id"] == 10
        assert attrs["activity"] == {"activity_id": "activity-123", "activity_type": "FetchCustomer"}
        assert attrs["result"] == {"decoded": True, "value": {"status": "active"}, "payload_count": 1}
        mock_client.get_workflow_handle.assert_called_once_with("test-workflow-123", run_id=None)

    @pytest.mark.asyncio
    async def test_get_workflow_event_reports_payload_decode_failure(self, mock_client):
        data_converter = _FailingDataConverter()

        event = _history_event(
            event_id=1,
            event_type=EventType.EVENT_TYPE_WORKFLOW_EXECUTION_STARTED,
            workflow_execution_started_event_attributes=WorkflowExecutionStartedEventAttributes(
                workflow_type=WorkflowType(name="TestWorkflow"),
                input=Payloads(payloads=await default().encode([{"customer_id": "123"}])),
            ),
        )

        async def mock_fetch_history_events():
            yield event

        mock_handle = AsyncMock()
        mock_handle.fetch_history_events = mock_fetch_history_events
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        mock_client.data_converter = data_converter

        result = await workflow_handlers.get_workflow_event(mock_client, {"workflow_id": "test-workflow-123", "event_id": 1, "run_id": "run-456"})

        response = json.loads(result[0].text)
        decoded_input = response["event"]["attributes"]["input"]

        assert response["run_id"] == "run-456"
        assert decoded_input["decoded"] is False
        assert decoded_input["error"] == "bad payload"
        assert decoded_input["error_type"] == "ValueError"
        assert decoded_input["payload_count"] == 1
        mock_client.get_workflow_handle.assert_called_once_with("test-workflow-123", run_id="run-456")

    @pytest.mark.asyncio
    async def test_get_workflow_event_not_found(self, mock_client):
        async def mock_fetch_history_events():
            if False:
                yield None

        mock_handle = AsyncMock()
        mock_handle.fetch_history_events = mock_fetch_history_events
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)

        result = await workflow_handlers.get_workflow_event(mock_client, {"workflow_id": "test-workflow-123", "event_id": 99})

        response = json.loads(result[0].text)
        assert response["type"] == "not_found"
        assert response["event_id"] == 99


def _history_event(event_id, event_type, **attributes):
    event_time = Timestamp()
    event_time.FromDatetime(datetime(2025, 10, 30, 12, 0, event_id % 60, tzinfo=timezone.utc))
    return HistoryEvent(event_id=event_id, event_type=event_type, event_time=event_time, **attributes)


class _FailingDataConverter:
    async def decode(self, payloads):
        raise ValueError("bad payload")
