"""Handlers for schedule operations."""

import json
import sys
from typing import Any

from mcp.types import TextContent
from temporalio.client import Client, Schedule, ScheduleActionStartWorkflow, ScheduleSpec


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
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "status": "created",
            "schedule_id": schedule_id,
            "workflow_name": workflow_name,
            "cron": cron
        }, indent=2)
    )]


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
    
    async for schedule in client.list_schedules():
        # Skip the first 'skip' results
        if count < skip:
            count += 1
            continue
            
        schedules.append({
            "schedule_id": schedule.id,
            "state": str(schedule.info.paused) if schedule.info else "unknown",
        })
        count += 1
        total_fetched += 1
        
        if total_fetched >= limit:
            break
    
    # Check if there are more results
    has_more = False
    try:
        async for _ in client.list_schedules():
            if count < skip + limit:
                count += 1
                continue
            has_more = True
            break
    except Exception as e:
        print(f"Warning: Error checking for more schedules: {e}", file=sys.stderr)
    
    result = {
        "schedules": schedules,
        "count": len(schedules),
        "skip": skip,
        "limit": limit
    }
    
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
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "status": "paused",
            "schedule_id": schedule_id,
            "note": note
        }, indent=2)
    )]


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
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "status": "unpaused",
            "schedule_id": schedule_id,
            "note": note
        }, indent=2)
    )]


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
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "status": "deleted",
            "schedule_id": schedule_id
        }, indent=2)
    )]


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
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "status": "triggered",
            "schedule_id": schedule_id
        }, indent=2)
    )]
