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
    """Cancel multiple workflows with concurrent processing.
    
    Args:
        client: Connected Temporal client
        args: Arguments containing query and optional limit, concurrency
        
    Returns:
        Batch operation results with success and error counts
    """
    import asyncio
    
    query = args["query"]
    limit = args.get("limit", 100)
    concurrency = args.get("concurrency", 50)  # Process 50 workflows concurrently
    
    print(f"Starting batch cancel with limit={limit}, concurrency={concurrency}", file=sys.stderr)

    workflows_cancelled = []
    errors = []
    
    async def cancel_workflow(workflow_id: str) -> tuple[str, Exception | None]:
        """Cancel a single workflow and return result."""
        try:
            handle = client.get_workflow_handle(workflow_id)
            await handle.cancel()
            return workflow_id, None
        except Exception as e:
            return workflow_id, e
    
    # Collect workflows to cancel
    workflows_to_cancel = []
    async for workflow in client.list_workflows(query):
        workflows_to_cancel.append(workflow.id)
        if len(workflows_to_cancel) >= limit:
            break
    
    total = len(workflows_to_cancel)
    print(f"Found {total} workflows to cancel. Starting cancellation...", file=sys.stderr)
    
    # Process in batches for concurrency
    for i in range(0, len(workflows_to_cancel), concurrency):
        batch = workflows_to_cancel[i:i + concurrency]
        batch_num = i // concurrency + 1
        total_batches = (len(workflows_to_cancel) + concurrency - 1) // concurrency
        
        print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} workflows)...", file=sys.stderr)
        
        # Cancel workflows concurrently in this batch
        results = await asyncio.gather(
            *[cancel_workflow(wf_id) for wf_id in batch],
            return_exceptions=False
        )
        
        # Process results
        for workflow_id, error in results:
            if error is None:
                workflows_cancelled.append(workflow_id)
            else:
                error_detail = {
                    "workflow_id": workflow_id,
                    "error": str(error),
                    "error_type": type(error).__name__
                }
                errors.append(error_detail)
                print(f"Error cancelling workflow {workflow_id}: {error}", file=sys.stderr)
        
        print(f"Batch {batch_num}/{total_batches} complete. Total cancelled: {len(workflows_cancelled)}, errors: {len(errors)}", file=sys.stderr)
    
    print(f"Batch cancel complete! Cancelled: {len(workflows_cancelled)}, Errors: {len(errors)}", file=sys.stderr)
    
    # Return only summary to avoid context overflow - do NOT include full list of IDs
    result = {
        "success_count": len(workflows_cancelled),
        "error_count": len(errors),
        "total_processed": len(workflows_cancelled) + len(errors),
        "message": f"Successfully cancelled {len(workflows_cancelled)} workflows."
    }
    
    # Include first and last few IDs as samples only
    if len(workflows_cancelled) > 0:
        if len(workflows_cancelled) <= 10:
            result["cancelled_workflows"] = workflows_cancelled
        else:
            result["sample_first"] = workflows_cancelled[:5]
            result["sample_last"] = workflows_cancelled[-5:]
            result["note"] = f"Showing first 5 and last 5 of {len(workflows_cancelled)} cancelled workflows to avoid context overflow"
    
    if errors:
        result["sample_errors"] = errors[:5]  # Only show first 5 errors
        if len(errors) > 5:
            result["errors_note"] = f"Showing first 5 of {len(errors)} errors"
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def batch_terminate(client: Client, args: dict) -> list[TextContent]:
    """Terminate multiple workflows with concurrent processing.
    
    Args:
        client: Connected Temporal client
        args: Arguments containing query, optional reason, limit, and concurrency
        
    Returns:
        Batch operation results with success and error counts
    """
    import asyncio
    
    query = args["query"]
    reason = args.get("reason", "Batch termination via MCP")
    limit = args.get("limit", 100)
    concurrency = args.get("concurrency", 50)  # Process 50 workflows concurrently
    
    print(f"Starting batch terminate with limit={limit}, concurrency={concurrency}", file=sys.stderr)

    workflows_terminated = []
    errors = []
    
    async def terminate_workflow(workflow_id: str) -> tuple[str, Exception | None]:
        """Terminate a single workflow and return result."""
        try:
            handle = client.get_workflow_handle(workflow_id)
            await handle.terminate(reason)
            return workflow_id, None
        except Exception as e:
            return workflow_id, e
    
    # Collect workflows to terminate
    workflows_to_terminate = []
    async for workflow in client.list_workflows(query):
        workflows_to_terminate.append(workflow.id)
        if len(workflows_to_terminate) >= limit:
            break
    
    total = len(workflows_to_terminate)
    print(f"Found {total} workflows to terminate. Starting termination...", file=sys.stderr)
    
    # Process in batches for concurrency
    for i in range(0, len(workflows_to_terminate), concurrency):
        batch = workflows_to_terminate[i:i + concurrency]
        batch_num = i // concurrency + 1
        total_batches = (len(workflows_to_terminate) + concurrency - 1) // concurrency
        
        print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} workflows)...", file=sys.stderr)
        
        # Terminate workflows concurrently in this batch
        results = await asyncio.gather(
            *[terminate_workflow(wf_id) for wf_id in batch],
            return_exceptions=False
        )
        
        # Process results
        for workflow_id, error in results:
            if error is None:
                workflows_terminated.append(workflow_id)
            else:
                error_detail = {
                    "workflow_id": workflow_id,
                    "error": str(error),
                    "error_type": type(error).__name__
                }
                errors.append(error_detail)
                print(f"Error terminating workflow {workflow_id}: {error}", file=sys.stderr)
        
        print(f"Batch {batch_num}/{total_batches} complete. Total terminated: {len(workflows_terminated)}, errors: {len(errors)}", file=sys.stderr)
    
    print(f"Batch terminate complete! Terminated: {len(workflows_terminated)}, Errors: {len(errors)}", file=sys.stderr)
    
    # Return only summary to avoid context overflow - do NOT include full list of IDs
    result = {
        "reason": reason,
        "success_count": len(workflows_terminated),
        "error_count": len(errors),
        "total_processed": len(workflows_terminated) + len(errors),
        "message": f"Successfully terminated {len(workflows_terminated)} workflows."
    }
    
    # Include first and last few IDs as samples only
    if len(workflows_terminated) > 0:
        if len(workflows_terminated) <= 10:
            result["terminated_workflows"] = workflows_terminated
        else:
            result["sample_first"] = workflows_terminated[:5]
            result["sample_last"] = workflows_terminated[-5:]
            result["note"] = f"Showing first 5 and last 5 of {len(workflows_terminated)} terminated workflows to avoid context overflow"
    
    if errors:
        result["sample_errors"] = errors[:5]  # Only show first 5 errors
        if len(errors) > 5:
            result["errors_note"] = f"Showing first 5 of {len(errors)} errors"
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
