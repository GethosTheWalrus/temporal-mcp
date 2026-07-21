"""Handlers for schedule operations."""

import dataclasses
import json
import sys
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from mcp.types import TextContent
from temporalio.api.common.v1 import Payload
from temporalio.client import Client, Schedule, ScheduleActionExecutionStartWorkflow, ScheduleActionStartWorkflow, ScheduleSpec, ScheduleDescription


async def create_schedule(client: Client, args: dict) -> list[TextContent]:
    """Create a new workflow schedule.

    Args:
        client: Connected Temporal client
        args: Arguments containing schedule_id, workflow_name, task_queue, cron, and optional args

    Returns:
        Success response with schedule details
    """
    schedule_id = args["schedule_id"]
    workflow_name = args["workflow_name"]
    task_queue = args["task_queue"]
    cron = args["cron"]
    workflow_args = args.get("args", {})

    await client.create_schedule(
        schedule_id,
        Schedule(
            action=ScheduleActionStartWorkflow(
                workflow_name,
                workflow_args,
                id=f"{schedule_id}-workflow",
                task_queue=task_queue,
            ),
            spec=ScheduleSpec(cron_expressions=[cron]),
        ),
    )

    return [TextContent(type="text", text=json.dumps({"status": "created", "schedule_id": schedule_id, "workflow_name": workflow_name, "cron": cron}, indent=2))]


async def list_schedules(client: Client, args: dict) -> list[TextContent]:
    """List all schedules with skip-based pagination.

    Args:
        client: Connected Temporal client
        args: Arguments containing optional limit and skip

    Returns:
        List of schedules with pagination info
    """
    limit = args.get("limit", 100)
    skip = args.get("skip", 0)

    schedules = []
    count = 0
    total_fetched = 0

    async for schedule in await client.list_schedules():
        # Skip the first 'skip' results
        if count < skip:
            count += 1
            continue

        schedules.append(
            {
                "schedule_id": schedule.id,
                "paused": schedule.schedule.state.paused if schedule.schedule else False,
            }
        )
        count += 1
        total_fetched += 1

        if total_fetched >= limit:
            break

    # Check if there are more results
    has_more = False
    try:
        async for _ in await client.list_schedules():
            if count < skip + limit:
                count += 1
                continue
            has_more = True
            break
    except Exception as e:
        print(f"Warning: Error checking for more schedules: {e}", file=sys.stderr)

    result = {"schedules": schedules, "count": len(schedules), "skip": skip, "limit": limit}

    if has_more:
        result["has_more"] = True
        result["next_skip"] = skip + limit
        result["message"] = f"Showing {len(schedules)} schedules (skipped {skip}). More results available. Use skip={skip + limit} to get the next page."
    else:
        result["has_more"] = False
        result["message"] = f"Showing all {len(schedules)} schedules (skipped {skip}). No more results."

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def pause_schedule(client: Client, args: dict) -> list[TextContent]:
    """Pause a schedule.

    Args:
        client: Connected Temporal client
        args: Arguments containing schedule_id and optional note

    Returns:
        Success response
    """
    schedule_id = args["schedule_id"]
    note = args.get("note", "Paused via MCP")

    handle = client.get_schedule_handle(schedule_id)
    await handle.pause(note=note)

    return [TextContent(type="text", text=json.dumps({"status": "paused", "schedule_id": schedule_id, "note": note}, indent=2))]


async def unpause_schedule(client: Client, args: dict) -> list[TextContent]:
    """Resume a paused schedule.

    Args:
        client: Connected Temporal client
        args: Arguments containing schedule_id and optional note

    Returns:
        Success response
    """
    schedule_id = args["schedule_id"]
    note = args.get("note", "Resumed via MCP")

    handle = client.get_schedule_handle(schedule_id)
    await handle.unpause(note=note)

    return [TextContent(type="text", text=json.dumps({"status": "unpaused", "schedule_id": schedule_id, "note": note}, indent=2))]


async def delete_schedule(client: Client, args: dict) -> list[TextContent]:
    """Delete a schedule.

    Args:
        client: Connected Temporal client
        args: Arguments containing schedule_id

    Returns:
        Success response
    """
    schedule_id = args["schedule_id"]

    handle = client.get_schedule_handle(schedule_id)
    await handle.delete()

    return [TextContent(type="text", text=json.dumps({"status": "deleted", "schedule_id": schedule_id}, indent=2))]


async def trigger_schedule(client: Client, args: dict) -> list[TextContent]:
    """Manually trigger a schedule.

    Args:
        client: Connected Temporal client
        args: Arguments containing schedule_id

    Returns:
        Success response
    """
    schedule_id = args["schedule_id"]

    handle = client.get_schedule_handle(schedule_id)
    await handle.trigger()

    return [TextContent(type="text", text=json.dumps({"status": "triggered", "schedule_id": schedule_id}, indent=2))]


async def describe_schedule(client: Client, args: dict) -> list[TextContent]:
    """Retrieve configuration and runtime information about a schedule.

    Args:
        client: Connected Temporal client
        args: Arguments containing schedule_id

    Returns:
        Schedule description including spec, state, and recent execution info
    """
    schedule_id = args["schedule_id"]

    handle = client.get_schedule_handle(schedule_id)
    desc: ScheduleDescription = await handle.describe()

    sched = desc.schedule
    info = desc.info

    action_info = _schedule_action_to_dict(sched.action)

    recent_actions = [
        {
            "scheduled_at": r.scheduled_at.isoformat(),
            "started_at": r.started_at.isoformat(),
            "action": _schedule_action_execution_to_dict(r.action),
        }
        for r in info.recent_actions
    ]

    next_action_times = [t.isoformat() for t in info.next_action_times]

    result = {
        "schedule_id": desc.id,
        "spec": _schedule_spec_to_dict(sched.spec),
        "action": action_info,
        "state": {
            "paused": sched.state.paused,
            "note": sched.state.note,
            "limited_actions": sched.state.limited_actions,
            "remaining_actions": sched.state.remaining_actions,
        },
        "info": {
            "num_actions": info.num_actions,
            "num_actions_missed_catchup_window": info.num_actions_missed_catchup_window,
            "num_actions_skipped_overlap": info.num_actions_skipped_overlap,
            "running_actions": [_schedule_action_execution_to_dict(action) for action in info.running_actions],
            "recent_actions": recent_actions,
            "next_action_times": next_action_times,
            "created_at": info.created_at.isoformat(),
            "last_updated_at": info.last_updated_at.isoformat() if info.last_updated_at else None,
        },
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def _schedule_spec_to_dict(spec: ScheduleSpec) -> dict[str, Any]:
    return {
        "calendars": [_calendar_spec_to_dict(calendar) for calendar in spec.calendars],
        "intervals": [_interval_spec_to_dict(interval) for interval in spec.intervals],
        "cron_expressions": list(spec.cron_expressions),
        "skip": [_calendar_spec_to_dict(calendar) for calendar in spec.skip],
        "start_at": spec.start_at.isoformat() if spec.start_at else None,
        "end_at": spec.end_at.isoformat() if spec.end_at else None,
        "jitter": _timedelta_to_seconds(spec.jitter),
        "time_zone_name": spec.time_zone_name,
    }


def _calendar_spec_to_dict(calendar: Any) -> dict[str, Any]:
    return {
        "second": [_range_to_dict(r) for r in calendar.second],
        "minute": [_range_to_dict(r) for r in calendar.minute],
        "hour": [_range_to_dict(r) for r in calendar.hour],
        "day_of_month": [_range_to_dict(r) for r in calendar.day_of_month],
        "month": [_range_to_dict(r) for r in calendar.month],
        "year": [_range_to_dict(r) for r in calendar.year],
        "day_of_week": [_range_to_dict(r) for r in calendar.day_of_week],
        "comment": calendar.comment,
    }


def _range_to_dict(schedule_range: Any) -> dict[str, int]:
    return {
        "start": schedule_range.start,
        "end": schedule_range.end,
        "step": schedule_range.step,
    }


def _interval_spec_to_dict(interval: Any) -> dict[str, float | None]:
    return {
        "every": _timedelta_to_seconds(interval.every),
        "offset": _timedelta_to_seconds(interval.offset),
    }


def _schedule_action_to_dict(action: Any) -> dict[str, Any]:
    if isinstance(action, ScheduleActionStartWorkflow):
        result = {
            "workflow": action.workflow,
            "task_queue": action.task_queue,
            "workflow_execution_id": action.id,
            "args": _json_safe(action.args),
            "execution_timeout": _timedelta_to_seconds(action.execution_timeout),
            "run_timeout": _timedelta_to_seconds(action.run_timeout),
            "task_timeout": _timedelta_to_seconds(action.task_timeout),
            "retry_policy": _json_safe(action.retry_policy),
            "memo": _json_safe(action.memo),
            "search_attributes": _search_attributes_to_dict(action.typed_search_attributes, action.untyped_search_attributes),
            "static_summary": _json_safe(action.static_summary),
            "static_details": _json_safe(action.static_details),
            "priority": _json_safe(action.priority),
        }
        if action.headers:
            result["headers"] = _json_safe(action.headers)
        return result
    return {}


def _schedule_action_execution_to_dict(action: Any) -> dict[str, Any]:
    if isinstance(action, ScheduleActionExecutionStartWorkflow):
        return {
            "workflow_id": action.workflow_id,
            "first_execution_run_id": action.first_execution_run_id,
        }
    return {}


def _search_attributes_to_dict(typed_search_attributes: Any, untyped_search_attributes: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if typed_search_attributes and getattr(typed_search_attributes, "search_attributes", None):
        result["typed"] = _json_safe(typed_search_attributes)
    if untyped_search_attributes:
        result["untyped"] = _json_safe(untyped_search_attributes)
    return result


def _timedelta_to_seconds(value: timedelta | None) -> float | None:
    return value.total_seconds() if value else None


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, Enum):
        return value.name
    if isinstance(value, Payload):
        return {
            "metadata": {key: metadata_value.decode("utf-8", errors="replace") for key, metadata_value in value.metadata.items()},
            "data_size": len(value.data),
        }
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "_asdict"):
        return _json_safe(value._asdict())
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {field.name: _json_safe(getattr(value, field.name)) for field in dataclasses.fields(value)}
    return str(value)
