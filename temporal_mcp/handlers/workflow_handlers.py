"""Handlers for workflow operations."""

import asyncio
import json
import sys
from typing import Any

from mcp.types import TextContent
from temporalio.client import Client
from temporalio.api.enums.v1 import WorkflowExecutionStatus


async def start_workflow(client: Client, args: dict) -> list[TextContent]:
    """Start a new workflow execution.
    
    Args:
        client: Connected Temporal client
        args: Arguments containing workflow_name, workflow_id, task_queue, and optional args
        
    Returns:
        Success response with workflow details
    """
    workflow_name = args["workflow_name"]
    workflow_id = args["workflow_id"]
    task_queue = args["task_queue"]
    workflow_args = args.get("args", {})

    handle = await client.start_workflow(
        workflow_name,
        workflow_args,
        id=workflow_id,
        task_queue=task_queue,
    )

    result = {
        "workflow_id": handle.id,
        "run_id": handle.result_run_id,
        "status": "started"
    }
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def cancel_workflow(client: Client, args: dict) -> list[TextContent]:
    """Cancel a workflow execution.
    
    Args:
        client: Connected Temporal client
        args: Arguments containing workflow_id
        
    Returns:
        Success response
    """
    workflow_id = args["workflow_id"]

    handle = client.get_workflow_handle(workflow_id)
    await handle.cancel()
    
    return [TextContent(
        type="text",
        text=json.dumps({"status": "cancelled", "workflow_id": workflow_id}, indent=2)
    )]


async def terminate_workflow(client: Client, args: dict) -> list[TextContent]:
    """Terminate a workflow execution.
    
    Args:
        client: Connected Temporal client
        args: Arguments containing workflow_id and optional reason
        
    Returns:
        Success response
    """
    workflow_id = args["workflow_id"]
    reason = args.get("reason", "Terminated via MCP")

    handle = client.get_workflow_handle(workflow_id)
    await handle.terminate(reason)
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "status": "terminated",
            "workflow_id": workflow_id,
            "reason": reason
        }, indent=2)
    )]


async def get_workflow_result(client: Client, args: dict) -> list[TextContent]:
    """Get the result of a workflow execution.
    
    Args:
        client: Connected Temporal client
        args: Arguments containing workflow_id and optional timeout
        
    Returns:
        Workflow result or timeout error
    """
    workflow_id = args["workflow_id"]
    timeout = args.get("timeout")

    handle = client.get_workflow_handle(workflow_id)
    
    try:
        if timeout:
            result = await asyncio.wait_for(handle.result(), timeout=timeout)
        else:
            result = await handle.result()
        
        return [TextContent(
            type="text",
            text=json.dumps({
                "result": result,
                "workflow_id": workflow_id
            }, indent=2, default=str)
        )]
    except asyncio.TimeoutError:
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": f"Timeout waiting for workflow result after {timeout} seconds",
                "type": "timeout",
                "workflow_id": workflow_id,
                "note": "Workflow may still be running. Use describe_workflow to check status."
            }, indent=2)
        )]


async def describe_workflow(client: Client, args: dict) -> list[TextContent]:
    """Get detailed information about a workflow.
    
    Args:
        client: Connected Temporal client
        args: Arguments containing workflow_id
        
    Returns:
        Workflow description
    """
    workflow_id = args["workflow_id"]

    handle = client.get_workflow_handle(workflow_id)
    description = await handle.describe()
    
    status_name = WorkflowExecutionStatus.Name(description.status)
    
    info = {
        "workflow_id": description.id,
        "run_id": description.run_id,
        "workflow_type": description.workflow_type,
        "status": status_name,
        "status_code": description.status,
        "start_time": str(description.start_time),
        "execution_time": str(description.execution_time) if description.execution_time else None,
        "close_time": str(description.close_time) if description.close_time else None,
    }
    
    return [TextContent(type="text", text=json.dumps(info, indent=2))]


async def list_workflows(client: Client, args: dict) -> list[TextContent]:
    """List workflow executions with skip-based pagination support.
    
    Args:
        client: Connected Temporal client
        args: Arguments containing optional query, limit, and skip
        
    Returns:
        List of workflows with pagination info
    """
    query = args.get("query", "")
    limit = args.get("limit", 100)
    skip = args.get("skip", 0)

    workflows = []
    count = 0
    total_fetched = 0
    
    async for workflow in client.list_workflows(query):
        # Skip the first 'skip' results
        if count < skip:
            count += 1
            continue
        
        workflows.append({
            "workflow_id": workflow.id,
            "run_id": workflow.run_id,
            "workflow_type": workflow.workflow_type,
            "status": WorkflowExecutionStatus.Name(workflow.status),
            "status_code": workflow.status,
            "start_time": str(workflow.start_time),
        })
        count += 1
        total_fetched += 1
        
        if total_fetched >= limit:
            break
    
    # Check if there are more results
    has_more = False
    try:
        async for _ in client.list_workflows(query):
            if count < skip + limit:
                count += 1
                continue
            has_more = True
            break
    except Exception as e:
        print(f"Warning: Error checking for more workflows: {e}", file=sys.stderr)
    
    result = {
        "workflows": workflows,
        "count": len(workflows),
        "skip": skip,
        "limit": limit
    }
    
    if has_more:
        result["has_more"] = True
        result["next_skip"] = skip + limit
        result["message"] = f"Showing {len(workflows)} workflows (skipped {skip}). More results available. Use skip={skip + limit} to get the next page."
    else:
        result["has_more"] = False
        result["message"] = f"Showing all {len(workflows)} workflows (skipped {skip}). No more results."
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def get_workflow_history(client: Client, args: dict) -> list[TextContent]:
    """Get workflow execution history.
    
    Args:
        client: Connected Temporal client
        args: Arguments containing workflow_id and optional limit
        
    Returns:
        Workflow history events
    """
    workflow_id = args["workflow_id"]
    limit = args.get("limit", 1000)

    handle = client.get_workflow_handle(workflow_id)
    
    events = []
    async for event in handle.fetch_history():
        events.append({
            "event_id": event.event_id,
            "event_type": event.event_type,
            "event_time": str(event.event_time),
        })
        if len(events) >= limit:
            break
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "workflow_id": workflow_id,
            "events": events,
            "count": len(events)
        }, indent=2)
    )]
