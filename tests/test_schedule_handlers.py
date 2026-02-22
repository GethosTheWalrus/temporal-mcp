"""Tests for schedule handler tools."""

import json
import pytest
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
