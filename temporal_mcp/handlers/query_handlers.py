"""Handlers for workflow query and signal operations."""

import json
from typing import Any

from mcp.types import TextContent
from temporalio.client import Client


async def query_workflow(client: Client, args: dict) -> list[TextContent]:
    """Query a workflow execution.
    
    Args:
        client: Connected Temporal client
        args: Arguments containing workflow_id, query_name, and optional args
        
    Returns:
        Query result
    """
    workflow_id = args["workflow_id"]
    query_name = args["query_name"]
    query_args = args.get("args")

    handle = client.get_workflow_handle(workflow_id)
    result = await handle.query(query_name, query_args)
    
    return [TextContent(
        type="text",
        text=json.dumps({"query_result": result}, indent=2, default=str)
    )]


async def signal_workflow(client: Client, args: dict) -> list[TextContent]:
    """Send a signal to a workflow.
    
    Args:
        client: Connected Temporal client
        args: Arguments containing workflow_id, signal_name, and optional args
        
    Returns:
        Success response
    """
    workflow_id = args["workflow_id"]
    signal_name = args["signal_name"]
    signal_args = args.get("args")

    handle = client.get_workflow_handle(workflow_id)
    await handle.signal(signal_name, signal_args)
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "status": "signal_sent",
            "workflow_id": workflow_id,
            "signal_name": signal_name
        }, indent=2)
    )]


async def continue_as_new(client: Client, args: dict) -> list[TextContent]:
    """Signal a workflow to continue as new.
    
    Note: This sends a signal to the workflow. The workflow itself must be
    designed to call workflow.continue_as_new() when it receives this signal.
    
    Args:
        client: Connected Temporal client
        args: Arguments containing workflow_id, signal_name, and optional signal_args
        
    Returns:
        Success response
    """
    workflow_id = args["workflow_id"]
    signal_name = args["signal_name"]
    signal_args = args.get("signal_args", {})
    
    handle = client.get_workflow_handle(workflow_id)
    await handle.signal(signal_name, signal_args)
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "status": "signal_sent",
            "workflow_id": workflow_id,
            "signal_name": signal_name,
            "note": "Workflow must implement continue-as-new logic in signal handler"
        }, indent=2)
    )]
