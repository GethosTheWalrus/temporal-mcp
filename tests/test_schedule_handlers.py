"""Tests for schedule handler tools."""

import json
import pytest
from datetime import datetime, timezone
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
        mock_handle = AsyncMock()
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
        mock_handle = AsyncMock()
        mock_client.get_schedule_handle = MagicMock(return_value=mock_handle)

        args = {"schedule_id": "test-schedule", "note": "Maintenance complete"}
        result = await schedule_handlers.unpause_schedule(mock_client, args)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "unpaused"
        mock_handle.unpause.assert_called_once_with(note="Maintenance complete")

    @pytest.mark.asyncio
    async def test_delete_schedule_success(self, mock_client):
        mock_handle = AsyncMock()
        mock_client.get_schedule_handle = MagicMock(return_value=mock_handle)

        result = await schedule_handlers.delete_schedule(mock_client, {"schedule_id": "test-schedule"})

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "deleted"
        mock_handle.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_schedule_success(self, mock_client):
        mock_handle = AsyncMock()
        mock_client.get_schedule_handle = MagicMock(return_value=mock_handle)

        result = await schedule_handlers.trigger_schedule(mock_client, {"schedule_id": "test-schedule"})

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "triggered"
        mock_handle.trigger.assert_called_once()

    @pytest.mark.asyncio
    async def test_describe_schedule_success(self, mock_client):
        from temporalio.client import ScheduleActionStartWorkflow

        now = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        next_time = datetime(2024, 1, 16, 9, 0, 0, tzinfo=timezone.utc)

        mock_action = MagicMock(spec=ScheduleActionStartWorkflow)
        mock_action.workflow = "TestWorkflow"
        mock_action.task_queue = "test-queue"
        mock_action.id = "test-schedule-workflow"

        mock_spec = MagicMock()
        mock_spec.cron_expressions = ["0 9 * * *"]

        mock_state = MagicMock()
        mock_state.paused = False
        mock_state.note = None
        mock_state.limited_actions = False
        mock_state.remaining_actions = 0

        mock_schedule = MagicMock()
        mock_schedule.action = mock_action
        mock_schedule.spec = mock_spec
        mock_schedule.state = mock_state

        mock_recent_action = MagicMock()
        mock_recent_action.scheduled_at = now
        mock_recent_action.started_at = now

        mock_info = MagicMock()
        mock_info.num_actions = 5
        mock_info.num_actions_missed_catchup_window = 0
        mock_info.num_actions_skipped_overlap = 1
        mock_info.recent_actions = [mock_recent_action]
        mock_info.next_action_times = [next_time]
        mock_info.created_at = now
        mock_info.last_updated_at = None

        mock_description = MagicMock()
        mock_description.id = "test-schedule"
        mock_description.schedule = mock_schedule
        mock_description.info = mock_info

        mock_handle = AsyncMock()
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
        assert len(response["info"]["recent_actions"]) == 1
        assert response["info"]["recent_actions"][0]["scheduled_at"] == now.isoformat()
        assert response["info"]["next_action_times"] == [next_time.isoformat()]
        assert response["info"]["created_at"] == now.isoformat()
        assert response["info"]["last_updated_at"] is None
        mock_handle.describe.assert_called_once()

    @pytest.mark.asyncio
    async def test_describe_schedule_with_last_updated_at(self, mock_client):
        from temporalio.client import ScheduleActionStartWorkflow

        now = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        updated = datetime(2024, 1, 20, 12, 0, 0, tzinfo=timezone.utc)

        mock_action = MagicMock(spec=ScheduleActionStartWorkflow)
        mock_action.workflow = "TestWorkflow"
        mock_action.task_queue = "test-queue"
        mock_action.id = "test-schedule-workflow"

        mock_spec = MagicMock()
        mock_spec.cron_expressions = ["0 12 * * *"]

        mock_state = MagicMock()
        mock_state.paused = True
        mock_state.note = "Paused for maintenance"
        mock_state.limited_actions = False
        mock_state.remaining_actions = 0

        mock_schedule = MagicMock()
        mock_schedule.action = mock_action
        mock_schedule.spec = mock_spec
        mock_schedule.state = mock_state

        mock_info = MagicMock()
        mock_info.num_actions = 10
        mock_info.num_actions_missed_catchup_window = 2
        mock_info.num_actions_skipped_overlap = 0
        mock_info.recent_actions = []
        mock_info.next_action_times = []
        mock_info.created_at = now
        mock_info.last_updated_at = updated

        mock_description = MagicMock()
        mock_description.id = "test-schedule"
        mock_description.schedule = mock_schedule
        mock_description.info = mock_info

        mock_handle = AsyncMock()
        mock_handle.describe = AsyncMock(return_value=mock_description)
        mock_client.get_schedule_handle = MagicMock(return_value=mock_handle)

        result = await schedule_handlers.describe_schedule(mock_client, {"schedule_id": "test-schedule"})

        assert len(result) == 1
        response = json.loads(result[0].text)

        assert response["state"]["paused"] is True
        assert response["state"]["note"] == "Paused for maintenance"
        assert response["info"]["num_actions_missed_catchup_window"] == 2
        assert response["info"]["last_updated_at"] == updated.isoformat()
