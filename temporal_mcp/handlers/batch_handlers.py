"""Handlers for batch workflow operations."""

import json
import sys
from typing import Any

from mcp.types import TextContent
from temporalio.client import Client


async def batch_signal(client: Client, args: dict) -> list[TextContent]:
    """Send signal to multiple workflows.
    
    Args:
        client: Connected Temporal client
        args: Arguments containing query, signal_name, optional args, and optional limit
        
    Returns:
        Batch operation results with success and error counts
    """
    query = args["query"]
    signal_name = args["signal_name"]
    signal_args = args.get("args")
    limit = args.get("limit", 100)

    workflows_signaled = []
    errors = []
    
    async for workflow in client.list_workflows(query):
        if len(workflows_signaled) + len(errors) >= limit:
            break
        
        try:
            handle = client.get_workflow_handle(workflow.id)
            await handle.signal(signal_name, signal_args)
            workflows_signaled.append(workflow.id)
        except Exception as e:
            error_detail = {
                "workflow_id": workflow.id,
                "error": str(e),
                "error_type": type(e).__name__
            }
            errors.append(error_detail)
            print(f"Error signaling workflow {workflow.id}: {e}", file=sys.stderr)
    
    result = {
        "signal_name": signal_name,
        "workflows_signaled": workflows_signaled,
        "success_count": len(workflows_signaled),
        "error_count": len(errors)
    }
    
    if errors:
        result["errors"] = errors
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def batch_cancel(client: Client, args: dict) -> list[TextContent]:
    """Cancel multiple workflows.
    
    Args:
        client: Connected Temporal client
        args: Arguments containing query and optional limit
        
    Returns:
        Batch operation results with success and error counts
    """
    query = args["query"]
    limit = args.get("limit", 100)

    workflows_cancelled = []
    errors = []
    
    async for workflow in client.list_workflows(query):
        if len(workflows_cancelled) + len(errors) >= limit:
            break
        
        try:
            handle = client.get_workflow_handle(workflow.id)
            await handle.cancel()
            workflows_cancelled.append(workflow.id)
        except Exception as e:
            error_detail = {
                "workflow_id": workflow.id,
                "error": str(e),
                "error_type": type(e).__name__
            }
            errors.append(error_detail)
            print(f"Error cancelling workflow {workflow.id}: {e}", file=sys.stderr)
    
    result = {
        "workflows_cancelled": workflows_cancelled,
        "success_count": len(workflows_cancelled),
        "error_count": len(errors)
    }
    
    if errors:
        result["errors"] = errors
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def batch_terminate(client: Client, args: dict) -> list[TextContent]:
    """Terminate multiple workflows.
    
    Args:
        client: Connected Temporal client
        args: Arguments containing query, optional reason, and optional limit
        
    Returns:
        Batch operation results with success and error counts
    """
    query = args["query"]
    reason = args.get("reason", "Batch termination via MCP")
    limit = args.get("limit", 100)

    workflows_terminated = []
    errors = []
    
    async for workflow in client.list_workflows(query):
        if len(workflows_terminated) + len(errors) >= limit:
            break
        
        try:
            handle = client.get_workflow_handle(workflow.id)
            await handle.terminate(reason)
            workflows_terminated.append(workflow.id)
        except Exception as e:
            error_detail = {
                "workflow_id": workflow.id,
                "error": str(e),
                "error_type": type(e).__name__
            }
            errors.append(error_detail)
            print(f"Error terminating workflow {workflow.id}: {e}", file=sys.stderr)
    
    result = {
        "reason": reason,
        "workflows_terminated": workflows_terminated,
        "success_count": len(workflows_terminated),
        "error_count": len(errors)
    }
    
    if errors:
        result["errors"] = errors
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
