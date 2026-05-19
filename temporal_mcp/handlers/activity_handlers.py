"""Handlers for standalone activity operations."""

import asyncio
import json
from datetime import timedelta
from typing import Any, cast

from mcp.types import TextContent
from temporalio.api.enums.v1 import ActivityExecutionStatus
from temporalio.client import Client


def _to_timedelta(seconds: float | int | None) -> timedelta | None:
    if seconds is None:
        return None
    return timedelta(seconds=float(seconds))


def _status_name(status: object) -> str:
    if status is None:
        return "UNKNOWN"

    if isinstance(status, int):
        return ActivityExecutionStatus.Name(cast(Any, status))

    try:
        return ActivityExecutionStatus.Name(cast(Any, int(str(status))))
    except Exception:
        return str(status)


async def start_activity(client: Client, args: dict) -> list[TextContent]:
    """Start a standalone activity and return its handle identifiers."""
    activity = args["activity"]
    activity_id = args["activity_id"]
    task_queue = args["task_queue"]
    activity_args = args.get("args", {})
    start_to_close_timeout = _to_timedelta(args.get("start_to_close_timeout_seconds"))

    handle = await client.start_activity(
        activity,
        args=[activity_args],
        id=activity_id,
        task_queue=task_queue,
        start_to_close_timeout=start_to_close_timeout,
    )

    result = {
        "activity_id": getattr(handle, "id", activity_id),
        "run_id": getattr(handle, "run_id", None),
        "status": "started",
    }
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def execute_activity(client: Client, args: dict) -> list[TextContent]:
    """Execute a standalone activity and wait for result."""
    activity = args["activity"]
    activity_id = args["activity_id"]
    task_queue = args["task_queue"]
    activity_args = args.get("args", {})
    start_to_close_timeout = _to_timedelta(args.get("start_to_close_timeout_seconds"))

    result = await client.execute_activity(
        activity,
        args=[activity_args],
        id=activity_id,
        task_queue=task_queue,
        start_to_close_timeout=start_to_close_timeout,
    )

    return [
        TextContent(
            type="text",
            text=json.dumps(
                {
                    "activity_id": activity_id,
                    "result": result,
                    "status": "completed",
                },
                indent=2,
                default=str,
            ),
        )
    ]


async def get_activity_result(client: Client, args: dict) -> list[TextContent]:
    """Fetch result for an existing standalone activity."""
    activity_id = args["activity_id"]
    run_id = args.get("run_id")
    timeout = args.get("timeout")

    handle = client.get_activity_handle(activity_id=activity_id, run_id=run_id)

    try:
        if timeout:
            result = await asyncio.wait_for(handle.result(), timeout=timeout)
        else:
            result = await handle.result()
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "activity_id": activity_id,
                        "run_id": run_id,
                        "result": result,
                    },
                    indent=2,
                    default=str,
                ),
            )
        ]
    except asyncio.TimeoutError:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Timeout waiting for activity result after {timeout} seconds",
                        "type": "timeout",
                        "activity_id": activity_id,
                    },
                    indent=2,
                ),
            )
        ]


async def describe_activity(client: Client, args: dict) -> list[TextContent]:
    """Describe an existing standalone activity."""
    activity_id = args["activity_id"]
    run_id = args.get("run_id")

    handle = client.get_activity_handle(activity_id=activity_id, run_id=run_id)
    description = await handle.describe()

    result = {
        "activity_id": getattr(description, "activity_id", activity_id),
        "run_id": getattr(description, "run_id", run_id),
        "activity_type": getattr(description, "activity_type", None),
        "task_queue": getattr(description, "task_queue", None),
        "status": _status_name(getattr(description, "status", None)),
        "status_code": getattr(description, "status", None),
        "attempt": getattr(description, "attempt", None),
        "start_time": str(getattr(description, "start_time", None)),
        "close_time": str(getattr(description, "close_time", None)) if getattr(description, "close_time", None) else None,
    }
    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


async def list_activities(client: Client, args: dict) -> list[TextContent]:
    """List standalone activity executions with skip-based pagination."""
    query = args.get("query", "")
    limit = args.get("limit", 100)
    skip = args.get("skip", 0)

    activities = []
    count = 0
    total_fetched = 0

    async for activity in client.list_activities(query=query):
        if count < skip:
            count += 1
            continue

        activities.append(
            {
                "activity_id": getattr(activity, "activity_id", None),
                "run_id": getattr(activity, "run_id", None),
                "activity_type": getattr(activity, "activity_type", None),
                "task_queue": getattr(activity, "task_queue", None),
                "status": _status_name(getattr(activity, "status", None)),
                "status_code": getattr(activity, "status", None),
                "start_time": str(getattr(activity, "start_time", None)),
            }
        )
        count += 1
        total_fetched += 1

        if total_fetched >= limit:
            break

    has_more = False
    async for _ in client.list_activities(query=query):
        if count < skip + limit:
            count += 1
            continue
        has_more = True
        break

    result = {
        "activities": activities,
        "count": len(activities),
        "skip": skip,
        "limit": limit,
        "has_more": has_more,
    }
    if has_more:
        result["next_skip"] = skip + limit
        result["message"] = f"Showing {len(activities)} activities (skipped {skip}). More results available. Use skip={skip + limit} to get the next page."
    else:
        result["message"] = f"Showing all {len(activities)} activities (skipped {skip}). No more results."

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def count_activities(client: Client, args: dict) -> list[TextContent]:
    """Count standalone activities matching a query."""
    query = args.get("query", "")
    response = await client.count_activities(query=query)

    groups = []
    for group in getattr(response, "groups", []):
        groups.append(
            {
                "group_values": list(getattr(group, "group_values", [])),
                "count": getattr(group, "count", 0),
            }
        )

    result = {
        "query": query,
        "count": getattr(response, "count", 0),
        "groups": groups,
    }
    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


async def cancel_activity(client: Client, args: dict) -> list[TextContent]:
    """Cancel a standalone activity execution."""
    activity_id = args["activity_id"]
    run_id = args.get("run_id")
    handle = client.get_activity_handle(activity_id=activity_id, run_id=run_id)
    await handle.cancel()
    return [
        TextContent(
            type="text",
            text=json.dumps(
                {"status": "cancelled", "activity_id": activity_id, "run_id": run_id},
                indent=2,
            ),
        )
    ]


async def terminate_activity(client: Client, args: dict) -> list[TextContent]:
    """Terminate a standalone activity execution."""
    activity_id = args["activity_id"]
    run_id = args.get("run_id")
    reason = args.get("reason", "Terminated via MCP")
    handle = client.get_activity_handle(activity_id=activity_id, run_id=run_id)
    await handle.terminate(reason=reason)
    return [
        TextContent(
            type="text",
            text=json.dumps(
                {
                    "status": "terminated",
                    "activity_id": activity_id,
                    "run_id": run_id,
                    "reason": reason,
                },
                indent=2,
            ),
        )
    ]
