"""Tests for schedule handler tools."""

import json
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from temporal_mcp.handlers import schedule_handlers


class TestScheduleHandlers:
    @pytest.mark.asyncio
    async def test_create_schedule_success(self, mock_client):
        mock_client.create_schedule = AsyncMock()

        args = {
            "schedule_id": "test-schedule",
            "workflow_name": "TestWorkflow",
            "task_queue": "test-queue",
            "cron": "0 9 * * *",
            "args": {},
        }

        result = await schedule_handlers.create_schedule(mock_client, args)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "created"
        assert response["schedule_id"] == "test-schedule"
        assert response["cron"] == "0 9 * * *"

    @pytest.mark.asyncio
    async def test_list_schedules_success(self, mock_client):
        mock_schedule = MagicMock()
        mock_schedule.id = "test-schedule"
        mock_schedule.schedule.state.paused = False

        async def mock_list_schedules_inner():
            yield mock_schedule

        async def mock_list_schedules():
            return mock_list_schedules_inner()

        mock_client.list_schedules = mock_list_schedules

        result = await schedule_handlers.list_schedules(mock_client, {"limit": 20})

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert len(response["schedules"]) == 1
        assert response["schedules"][0]["schedule_id"] == "test-schedule"
        assert response["schedules"][0]["paused"] is False

    @pytest.mark.asyncio
    async def test_pause_schedule_success(self, mock_client):
        mock_handle = MagicMock()
        mock_handle.pause = AsyncMock()
        mock_client.get_schedule_handle = MagicMock(return_value=mock_handle)

        args = {"schedule_id": "test-schedule", "note": "Paused for maintenance"}
        result = await schedule_handlers.pause_schedule(mock_client, args)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "paused"
        assert response["schedule_id"] == "test-schedule"
        mock_handle.pause.assert_called_once_with(note="Paused for maintenance")

    @pytest.mark.asyncio
    async def test_unpause_schedule_success(self, mock_client):
        mock_handle = MagicMock()
        mock_handle.unpause = AsyncMock()
        mock_client.get_schedule_handle = MagicMock(return_value=mock_handle)

        args = {"schedule_id": "test-schedule", "note": "Maintenance complete"}
        result = await schedule_handlers.unpause_schedule(mock_client, args)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "unpaused"
        mock_handle.unpause.assert_called_once_with(note="Maintenance complete")

    @pytest.mark.asyncio
    async def test_delete_schedule_success(self, mock_client):
        mock_handle = MagicMock()
        mock_handle.delete = AsyncMock()
        mock_client.get_schedule_handle = MagicMock(return_value=mock_handle)

        result = await schedule_handlers.delete_schedule(mock_client, {"schedule_id": "test-schedule"})

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "deleted"
        mock_handle.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_schedule_success(self, mock_client):
        mock_handle = MagicMock()
        mock_handle.trigger = AsyncMock()
        mock_client.get_schedule_handle = MagicMock(return_value=mock_handle)

        result = await schedule_handlers.trigger_schedule(mock_client, {"schedule_id": "test-schedule"})

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "triggered"
        mock_handle.trigger.assert_called_once()

    @pytest.mark.asyncio
    async def test_describe_schedule_success(self, mock_client):
        from temporalio.client import ScheduleActionStartWorkflow, ScheduleSpec

        now = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        next_time = datetime(2024, 1, 16, 9, 0, 0, tzinfo=timezone.utc)

        mock_action = ScheduleActionStartWorkflow(
            "TestWorkflow",
            args=[],
            id="test-schedule-workflow",
            task_queue="test-queue",
        )

        mock_state = MagicMock()
        mock_state.paused = False
        mock_state.note = None
        mock_state.limited_actions = False
        mock_state.remaining_actions = 0

        mock_schedule = MagicMock()
        mock_schedule.action = mock_action
        mock_schedule.spec = ScheduleSpec(cron_expressions=["0 9 * * *"])
        mock_schedule.state = mock_state

        mock_recent_action = MagicMock()
        mock_recent_action.scheduled_at = now
        mock_recent_action.started_at = now

        mock_info = MagicMock()
        mock_info.num_actions = 5
        mock_info.num_actions_missed_catchup_window = 0
        mock_info.num_actions_skipped_overlap = 1
        mock_info.running_actions = []
        mock_info.recent_actions = [mock_recent_action]
        mock_info.next_action_times = [next_time]
        mock_info.created_at = now
        mock_info.last_updated_at = None

        mock_description = MagicMock()
        mock_description.id = "test-schedule"
        mock_description.schedule = mock_schedule
        mock_description.info = mock_info

        mock_handle = MagicMock()
        mock_handle.describe = AsyncMock(return_value=mock_description)
        mock_client.get_schedule_handle = MagicMock(return_value=mock_handle)

        result = await schedule_handlers.describe_schedule(mock_client, {"schedule_id": "test-schedule"})

        assert len(result) == 1
        response = json.loads(result[0].text)

        assert response["schedule_id"] == "test-schedule"
        assert response["spec"]["cron_expressions"] == ["0 9 * * *"]
        assert response["action"]["workflow"] == "TestWorkflow"
        assert response["action"]["task_queue"] == "test-queue"
        assert response["state"]["paused"] is False
        assert response["state"]["note"] is None
        assert response["info"]["num_actions"] == 5
        assert response["info"]["num_actions_skipped_overlap"] == 1
        assert response["info"]["running_actions"] == []
        assert len(response["info"]["recent_actions"]) == 1
        assert response["info"]["recent_actions"][0]["scheduled_at"] == now.isoformat()
        assert response["info"]["next_action_times"] == [next_time.isoformat()]
        assert response["info"]["created_at"] == now.isoformat()
        assert response["info"]["last_updated_at"] is None
        mock_handle.describe.assert_called_once()

    @pytest.mark.asyncio
    async def test_describe_schedule_with_last_updated_at(self, mock_client):
        from temporalio.client import ScheduleActionStartWorkflow, ScheduleSpec

        now = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        updated = datetime(2024, 1, 20, 12, 0, 0, tzinfo=timezone.utc)

        mock_action = ScheduleActionStartWorkflow(
            "TestWorkflow",
            args=[],
            id="test-schedule-workflow",
            task_queue="test-queue",
        )

        mock_state = MagicMock()
        mock_state.paused = True
        mock_state.note = "Paused for maintenance"
        mock_state.limited_actions = False
        mock_state.remaining_actions = 0

        mock_schedule = MagicMock()
        mock_schedule.action = mock_action
        mock_schedule.spec = ScheduleSpec(cron_expressions=["0 12 * * *"])
        mock_schedule.state = mock_state

        mock_info = MagicMock()
        mock_info.num_actions = 10
        mock_info.num_actions_missed_catchup_window = 2
        mock_info.num_actions_skipped_overlap = 0
        mock_info.running_actions = []
        mock_info.recent_actions = []
        mock_info.next_action_times = []
        mock_info.created_at = now
        mock_info.last_updated_at = updated

        mock_description = MagicMock()
        mock_description.id = "test-schedule"
        mock_description.schedule = mock_schedule
        mock_description.info = mock_info

        mock_handle = MagicMock()
        mock_handle.describe = AsyncMock(return_value=mock_description)
        mock_client.get_schedule_handle = MagicMock(return_value=mock_handle)

        result = await schedule_handlers.describe_schedule(mock_client, {"schedule_id": "test-schedule"})

        assert len(result) == 1
        response = json.loads(result[0].text)

        assert response["state"]["paused"] is True
        assert response["state"]["note"] == "Paused for maintenance"
        assert response["info"]["num_actions_missed_catchup_window"] == 2
        assert response["info"]["last_updated_at"] == updated.isoformat()

    @pytest.mark.asyncio
    async def test_describe_schedule_includes_extended_fields(self, mock_client):
        from temporalio.client import ScheduleActionExecutionStartWorkflow, ScheduleActionResult, ScheduleActionStartWorkflow, ScheduleCalendarSpec, ScheduleIntervalSpec, ScheduleRange, ScheduleSpec
        from temporalio.common import RetryPolicy

        now = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        start_at = datetime(2024, 1, 16, 9, 0, 0, tzinfo=timezone.utc)
        end_at = datetime(2024, 2, 16, 9, 0, 0, tzinfo=timezone.utc)
        action_execution = ScheduleActionExecutionStartWorkflow(
            workflow_id="child-workflow-id",
            first_execution_run_id="run-123",
        )

        mock_state = MagicMock()
        mock_state.paused = False
        mock_state.note = None
        mock_state.limited_actions = False
        mock_state.remaining_actions = 0

        mock_schedule = MagicMock()
        mock_schedule.action = ScheduleActionStartWorkflow(
            "TestWorkflow",
            args=[{"customer_id": "123"}],
            id="test-schedule-workflow",
            task_queue="test-queue",
            execution_timeout=timedelta(minutes=30),
            run_timeout=timedelta(minutes=20),
            task_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3, non_retryable_error_types=["BadRequest"]),
            memo={"owner": "platform"},
            untyped_search_attributes={"CustomKeywordField": ["nightly"]},
            static_summary="Nightly schedule",
            static_details="Runs every night",
        )
        mock_schedule.spec = ScheduleSpec(
            calendars=[
                ScheduleCalendarSpec(
                    minute=[ScheduleRange(15)],
                    hour=[ScheduleRange(2)],
                    comment="2:15 AM",
                )
            ],
            intervals=[ScheduleIntervalSpec(every=timedelta(hours=6), offset=timedelta(minutes=30))],
            cron_expressions=["15 2 * * *"],
            skip=[ScheduleCalendarSpec(day_of_week=[ScheduleRange(0)], comment="skip sunday")],
            start_at=start_at,
            end_at=end_at,
            jitter=timedelta(minutes=5),
            time_zone_name="America/New_York",
        )
        mock_schedule.state = mock_state

        mock_info = MagicMock()
        mock_info.num_actions = 5
        mock_info.num_actions_missed_catchup_window = 0
        mock_info.num_actions_skipped_overlap = 0
        mock_info.running_actions = [action_execution]
        mock_info.recent_actions = [
            ScheduleActionResult(
                scheduled_at=now,
                started_at=now,
                action=action_execution,
            )
        ]
        mock_info.next_action_times = []
        mock_info.created_at = now
        mock_info.last_updated_at = now

        mock_description = MagicMock()
        mock_description.id = "test-schedule"
        mock_description.schedule = mock_schedule
        mock_description.info = mock_info

        mock_handle = MagicMock()
        mock_handle.describe = AsyncMock(return_value=mock_description)
        mock_client.get_schedule_handle = MagicMock(return_value=mock_handle)

        result = await schedule_handlers.describe_schedule(mock_client, {"schedule_id": "test-schedule"})

        response = json.loads(result[0].text)

        assert response["spec"]["calendars"][0]["minute"] == [{"start": 15, "end": 15, "step": 1}]
        assert response["spec"]["calendars"][0]["hour"] == [{"start": 2, "end": 2, "step": 1}]
        assert response["spec"]["calendars"][0]["comment"] == "2:15 AM"
        assert response["spec"]["intervals"] == [{"every": 21600.0, "offset": 1800.0}]
        assert response["spec"]["skip"][0]["comment"] == "skip sunday"
        assert response["spec"]["start_at"] == start_at.isoformat()
        assert response["spec"]["end_at"] == end_at.isoformat()
        assert response["spec"]["jitter"] == 300.0
        assert response["spec"]["time_zone_name"] == "America/New_York"
        assert response["action"]["args"] == [{"customer_id": "123"}]
        assert response["action"]["memo"] == {"owner": "platform"}
        assert response["action"]["retry_policy"]["maximum_attempts"] == 3
        assert response["action"]["retry_policy"]["non_retryable_error_types"] == ["BadRequest"]
        assert response["action"]["search_attributes"]["untyped"] == {"CustomKeywordField": ["nightly"]}
        assert response["action"]["execution_timeout"] == 1800.0
        assert response["action"]["run_timeout"] == 1200.0
        assert response["action"]["task_timeout"] == 30.0
        assert response["action"]["static_summary"] == "Nightly schedule"
        assert response["action"]["static_details"] == "Runs every night"
        assert response["info"]["running_actions"] == [{"workflow_id": "child-workflow-id", "first_execution_run_id": "run-123"}]
        assert response["info"]["recent_actions"][0]["action"] == {"workflow_id": "child-workflow-id", "first_execution_run_id": "run-123"}
